#!/usr/bin/env python3
"""域层反馈自动提交器（/tw:feedback 的落地工具，零第三方依赖）。

从宿主项目本地队列 .claude/tw_feedback.md 读取「待提交」条目，脱敏后
通过 gh issue create 提交到框架仓库。默认只预览（--dry-run），提交时
使用预览输出的校验值，确认目标仓库与内容没有发生变化。

用法：
  python3 tw/tools/submit_feedback.py --project-root <宿主项目根> --dry-run
  python3 tw/tools/submit_feedback.py --project-root <宿主项目根> --yes --approval <预览校验值>
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO = "penghang1223/tapwitness-ui-automation"
DEFAULT_LABEL = "tw-feedback"
QUEUE_NAME = ".claude/tw_feedback.md"
LEDGER_NAME = ".claude/tw_feedback_submitted.json"
PROFILE_NAME = ".claude/project_profile.md"

COLS = ["日期", "阶段", "现象", "根因", "对策", "适用平台", "来源 feature", "状态"]

# 脱敏规则：绝对路径 / URL / 邮箱 / 常见凭据形态
REDACTIONS = [
    (re.compile(r"(?:/Users/|/home/|/root/|/var/folders/|[A-Za-z]:\\|\\\\)[^\s,|)]*"), "[PATH]"),
    (re.compile(r"https?://[^\s,|)]+"), "[URL]"),
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9_-]{16,}|[A-Fa-f0-9]{32,})\b"), "[REDACTED]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP]"),
    (re.compile(r"(?i)\b(password|passwd|pwd|token|api[_-]?key|secret|authorization)\s*[:=]\s*[^\s,;]+"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)\bBearer\s+[^\s,;]+"), "Bearer [REDACTED]"),
]


def sanitize(text: str, limit: int = 500) -> str:
    """白名单之外的信息一律不进入公开 issue；同时避免破坏表格结构。"""
    s = str(text).strip().replace("|", "/").replace("\r", " ").replace("\n", " ")
    for pattern, repl in REDACTIONS:
        s = pattern.sub(repl, s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s[:limit]


def parse_frontmatter_channel(project_root: Path) -> dict:
    """极简读取 project_profile.md 的 feedback_channel 段，不依赖 PyYAML。"""
    cfg = {}
    path = project_root / PROFILE_NAME
    if not path.exists():
        return cfg
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return cfg
    if not lines or lines[0].strip() != "---":
        return cfg
    in_section = False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_section = line.strip().startswith("feedback_channel:")
            continue
        if not in_section or indent > 4:
            continue
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        val = re.sub(r"\s+#.*$", "", val).strip().strip('"').strip("'")
        if val:
            cfg[key] = val
    return cfg


def load_queue(project_root: Path):
    path = project_root / QUEUE_NAME
    if not path.exists():
        return path, [], []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = []
    for idx, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        if cells and cells[0] in ("日期", "date"):
            continue
        while len(cells) < len(COLS):
            cells.append("")
        rows.append((idx, cells[: len(COLS)], line))
    pending = [(i, c) for i, c, _ in rows if "待提交" in c[7]]
    return path, pending, rows


def load_ledger(project_root: Path) -> dict:
    path = project_root / LEDGER_NAME
    if not path.exists():
        return {"version": 1, "submitted": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("无法读取反馈台账 %s（%s）" % (path, exc))
    if not isinstance(data, dict) or not isinstance(data.get("submitted"), list) or not all(
            isinstance(item, dict) and isinstance(item.get("key"), str)
            and item.get("status", "submitted") in ("pending", "submitted")
            and (item.get("status") != "pending" or isinstance(item.get("repo"), str))
            for item in data["submitted"]):
        raise ValueError("反馈台账格式错误：%s" % path)
    return data


def atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent),
                                         delete=False) as fh:
            name = fh.name
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(name, path)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()


def save_ledger(project_root: Path, ledger: dict):
    atomic_write(project_root / LEDGER_NAME,
                 json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


def item_key(source_project: str, feature: str, phenomenon: str) -> str:
    # 保持既有台账的去重键算法，新增脱敏规则不影响历史记录匹配。
    def legacy_value(value):
        text = str(value).strip().replace("|", "/").replace("\r", " ").replace("\n", " ")
        for pattern, replacement in REDACTIONS[:4]:
            text = pattern.sub(replacement, text)
        return re.sub(r"\s{2,}", " ", text).strip()[:80]
    raw = "%s|%s|%s" % (legacy_value(source_project), legacy_value(feature), legacy_value(phenomenon))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_issue(cfg: dict, cells: list, source_project: str):
    date, stage, phenomenon, root_cause, countermeasure, platform, feature, _ = cells
    title = "[tw-feedback] %s" % (sanitize(phenomenon, 90) or "域层坑点反馈")
    body = "\n".join([
        "## 来源",
        "- 来源项目：%s" % sanitize(source_project, 80),
        "- 来源 feature：%s" % sanitize(feature, 80),
        "- 日期：%s" % sanitize(date, 40),
        "- 阶段：%s" % sanitize(stage, 40),
        "- 适用平台：%s" % sanitize(platform, 40),
        "",
        "## 现象",
        sanitize(phenomenon),
        "",
        "## 根因",
        sanitize(root_cause) or "（未提供）",
        "",
        "## 对策（判据 + 动作）",
        sanitize(countermeasure),
        "",
        "---",
        "> 由 `/tw:feedback` 提交。请勿直接改 plugin 缓存内的域包文件（升级会丢失）。",
        "",
    ])
    return title, body


def preview_digest(repo, pending, project_name):
    items = []
    for _, cells in pending:
        title, body = build_issue({}, cells, project_name)
        items.append({"title": title, "body": body,
                      "key": item_key(project_name, cells[6], cells[2])})
    payload = json.dumps({"repo": repo, "items": items}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def prefilled_url(repo: str, title: str, body: str) -> str:
    short = body[:1500]
    return "https://github.com/%s/issues/new?%s" % (
        repo, urllib.parse.urlencode({"title": title, "body": short}))


def gh_ready():
    if shutil.which("gh") is None:
        return False, "未安装 gh CLI（https://cli.github.com）"
    r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if r.returncode != 0:
        return False, "gh 未登录，请先执行 gh auth login"
    return True, ""


def create_issue(repo: str, title: str, body: str, label: str):
    """返回 (ok, url, message)。失败时远端状态可能未知，交由调用方核对。"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as fh:
        fh.write(body)
        body_file = fh.name
    try:
        base = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body-file", body_file]
        r = subprocess.run(base + ["--label", label], capture_output=True, text=True)
        if r.returncode != 0:
            return False, "", (r.stderr or r.stdout).strip()[:300]
        m = re.search(r"https://github\.com/[^\s]+/issues/\d+", r.stdout)
        return True, (m.group(0) if m else ""), ""
    finally:
        Path(body_file).unlink(missing_ok=True)


def rewrite_queue(path: Path, lines: list, idx: int, status: str, original: list):
    if idx >= len(lines):
        raise ValueError("反馈队列已变化，请重新检查后恢复")
    cells = [c.strip() for c in lines[idx].strip().strip("|").split("|")]
    if cells[:7] != original[:7]:
        raise ValueError("反馈队列已变化，请重新检查后恢复")
    while len(cells) < len(COLS):
        cells.append("")
    cells[7] = status
    lines[idx] = "| " + " | ".join(cells[: len(COLS)]) + " |"
    atomic_write(path, "\n".join(lines) + "\n")


def submitted_status(entry):
    match = re.search(r"/issues/(\d+)$", entry.get("url", ""))
    label = "Issue #%s" % match.group(1) if match else "Issue"
    return "已提交(%s,%s)" % (label, entry.get("date", ""))


def submit_pending(project_root, queue_path, pending, ledger, repo, label):
    ok, why = gh_ready()
    if not ok:
        print("ERROR：%s。反馈仍保留在本地队列，未丢失。" % why)
        title, body = build_issue({}, pending[0][1], project_root.name)
        print("人工提交：%s" % prefilled_url(repo, title, body))
        return 2

    seen = {entry["key"]: entry for entry in ledger["submitted"]}
    today = datetime.date.today().isoformat()
    done = 0
    for idx, cells in pending:
        title, body = build_issue({}, cells, project_root.name)
        key = item_key(project_root.name, cells[6], cells[2])
        entry = seen.get(key)
        if entry:
            if entry.get("status", "submitted") == "pending":
                print("ERROR：反馈 %s 的远端提交结果待核对，已停止重试。" % key)
                print("请在 %s 核对标识 tw-feedback:%s，再用 --resolve 记录结果。" % (repo, key))
                return 1
            lines = queue_path.read_text(encoding="utf-8").splitlines()
            rewrite_queue(queue_path, lines, idx, submitted_status(entry), cells)
            print("  [SKIP] 已提交过并修复队列状态：%s" % title)
            continue
        entry = {"key": key, "title": title, "url": "", "date": today,
                 "status": "pending", "repo": repo}
        ledger["submitted"].append(entry)
        save_ledger(project_root, ledger)
        body += "\n<!-- tw-feedback:%s -->\n" % key
        success, url, err = create_issue(repo, title, body, label)
        if not success or not url:
            print("ERROR：提交结果待核对：%s" % (err or "未获取 Issue URL"))
            print("请在 %s 核对标识 tw-feedback:%s，再用 --resolve 记录结果。" % (repo, key))
            return 1
        entry.update(status="submitted", url=url)
        save_ledger(project_root, ledger)
        seen[key] = entry
        lines = queue_path.read_text(encoding="utf-8").splitlines()
        rewrite_queue(queue_path, lines, idx, submitted_status(entry), cells)
        done += 1
        print("✓ 已提交：%s" % url)
    remain = len(load_queue(project_root)[1])
    print("✓ 本次提交 %d 条，队列剩余 %d 条待提交。" % (done, remain))
    return 0


def resolve_pending(project_root, ledger, key, issue_url, confirm_absent):
    entries = [entry for entry in ledger["submitted"]
               if entry.get("key") == key and entry.get("status") == "pending"]
    if len(entries) != 1:
        raise ValueError("待核对反馈不存在或不唯一：%s" % key)
    entry = entries[0]
    if issue_url:
        expected = "https://github.com/%s/issues/" % entry["repo"]
        if not issue_url.startswith(expected) or not issue_url[len(expected):].isdigit():
            raise ValueError("Issue URL 必须指向原目标仓库")
        entry.update(status="submitted", url=issue_url)
    elif confirm_absent:
        ledger["submitted"].remove(entry)
    else:
        raise ValueError("--resolve 需要 --issue-url 或 --confirm-absent")
    save_ledger(project_root, ledger)
    print("✓ 反馈 %s 的核对结果已记录" % key)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", default=str(Path.cwd()), help="宿主项目根目录（默认 CWD）")
    ap.add_argument("--repo", default=None, help="覆盖目标仓库 owner/repo")
    ap.add_argument("--label", default=DEFAULT_LABEL)
    ap.add_argument("--dry-run", action="store_true", help="只预览，不调用 gh（默认）")
    ap.add_argument("--yes", action="store_true", help="真正提交 issue")
    ap.add_argument("--approval", help="预览输出的校验值，提交时必须提供")
    ap.add_argument("--all", action="store_true", help="提交队列全部待提交条目（默认只提交第一条）")
    ap.add_argument("--resolve", metavar="KEY", help="记录待核对反馈的远端结果")
    result = ap.add_mutually_exclusive_group()
    result.add_argument("--issue-url", help="待核对反馈已创建的 Issue URL")
    result.add_argument("--confirm-absent", action="store_true", help="已核实远端未创建，允许重新提交")
    args = ap.parse_args()

    project_root = Path(args.project_root).resolve()
    cfg = parse_frontmatter_channel(project_root)
    repo = args.repo or cfg.get("issue_repo") or DEFAULT_REPO
    issue_url = cfg.get("issue_url") or "https://github.com/%s/issues/new?template=tw-feedback.yml" % repo
    auto_submit = str(cfg.get("auto_submit", "true")).strip().lower() not in ("false", "off", "no", "0")
    submit = args.yes and not args.dry_run and auto_submit

    if (args.issue_url or args.confirm_absent) and not args.resolve:
        ap.error("--issue-url 和 --confirm-absent 需要 --resolve")
    if args.resolve and (args.yes or args.dry_run or args.approval):
        ap.error("--resolve 不能与 --yes、--dry-run 或 --approval 同时使用")
    queue_path, pending, _ = load_queue(project_root)
    if args.resolve:
        return locked_action(project_root, lambda ledger: resolve_pending(
            project_root, ledger, args.resolve, args.issue_url, args.confirm_absent))
    if not pending:
        print("✓ 无待提交反馈（%s）" % queue_path)
        return 0
    if not args.all:
        pending = pending[:1]

    if not submit:
        reason = "profile 关闭了 auto_submit" if (args.yes and not auto_submit) else "未带 --yes"
        print("[DRY RUN] %s；只预览，不创建任何 issue。共 %d 条待提交。" % (reason, len(pending)))
        ledger = load_ledger(project_root)
        seen = {entry["key"]: entry for entry in ledger["submitted"]}
        for idx, cells in pending:
            title, body = build_issue(cfg, cells, project_root.name)
            key = item_key(project_root.name, cells[6], cells[2])
            entry = seen.get(key)
            if entry:
                status = "提交结果待核对" if entry.get("status") == "pending" else "已提交过"
                print("  [SKIP] %s：%s（%s）" % (status, title, key))
                continue
            body += "\n<!-- tw-feedback:%s -->\n" % key
            print("--- 目标仓库 ---\n%s" % repo)
            print("--- 标题 ---\n%s\n--- 正文 ---\n%s" % (title, body))
            print("--- 人工降级链接 ---\n%s" % prefilled_url(repo, title, body))
        print("预览校验值：%s" % preview_digest(repo, pending, project_root.name))
        print("反馈入口：%s" % issue_url)
        return 0

    def submit_locked(ledger):
        path, current, _ = load_queue(project_root)
        current = current if args.all else current[:1]
        if not current:
            return 0
        if args.approval != preview_digest(repo, current, project_root.name):
            print("ERROR：预览校验值缺失或内容已变化，请重新预览。")
            return 1
        return submit_pending(project_root, path, current, ledger, repo, args.label)
    return locked_action(project_root, submit_locked)


def locked_action(project_root, action):
    lock = project_root / ".claude" / "tw_feedback_submit.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        print("ERROR：反馈提交锁已存在：%s。确认没有提交进程后可删除该目录。" % lock)
        return 1
    try:
        return action(load_ledger(project_root))
    finally:
        lock.rmdir()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print("ERROR：%s" % exc, file=sys.stderr)
        sys.exit(1)
