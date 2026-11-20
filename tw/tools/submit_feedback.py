#!/usr/bin/env python3
"""域层反馈自动提交器（/tw:feedback 的落地工具，零第三方依赖）。

从宿主项目本地队列 .claude/tw_feedback.md 读取「待提交」条目，脱敏后
通过 gh issue create 提交到框架仓库。默认只预览（--dry-run），带 --yes
才真正提交；失败时保留队列并打印预填 Issue 链接作为人工降级。

用法：
  python3 tw/tools/submit_feedback.py --project-root <宿主项目根> --dry-run
  python3 tw/tools/submit_feedback.py --project-root <宿主项目根> --yes
  python3 tw/tools/submit_feedback.py --yes --all
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
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
        if isinstance(data, dict) and isinstance(data.get("submitted"), list):
            return data
    except (OSError, ValueError):
        pass
    return {"version": 1, "submitted": []}


def item_key(source_project: str, feature: str, phenomenon: str) -> str:
    raw = "%s|%s|%s" % (sanitize(source_project, 80), sanitize(feature, 80), sanitize(phenomenon, 80))
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
        "> 由 `/tw:feedback` 自动提交，内容已脱敏。请勿直接改 plugin 缓存内的域包文件（升级会丢失）。",
        "",
    ])
    return title, body


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
    """返回 (ok, url, message)。label 不存在时自动降级为不带 label 重试。"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as fh:
        fh.write(body)
        body_file = fh.name
    try:
        base = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body-file", body_file]
        r = subprocess.run(base + ["--label", label], capture_output=True, text=True)
        if r.returncode != 0 and re.search(r"label|could not add", r.stderr, re.I):
            r = subprocess.run(base, capture_output=True, text=True)
        if r.returncode != 0:
            return False, "", (r.stderr or r.stdout).strip()[:300]
        m = re.search(r"https://github\.com/[^\s]+/issues/\d+", r.stdout)
        return True, (m.group(0) if m else ""), ""
    finally:
        Path(body_file).unlink(missing_ok=True)


def rewrite_queue(path: Path, lines: list, idx: int, status: str):
    cells = [c.strip() for c in lines[idx].strip().strip("|").split("|")]
    while len(cells) < len(COLS):
        cells.append("")
    cells[7] = status
    lines[idx] = "| " + " | ".join(cells[: len(COLS)]) + " |"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", default=str(Path.cwd()), help="宿主项目根目录（默认 CWD）")
    ap.add_argument("--repo", default=None, help="覆盖目标仓库 owner/repo")
    ap.add_argument("--label", default=DEFAULT_LABEL)
    ap.add_argument("--dry-run", action="store_true", help="只预览，不调用 gh（默认）")
    ap.add_argument("--yes", action="store_true", help="真正提交 issue")
    ap.add_argument("--all", action="store_true", help="提交队列全部待提交条目（默认只提交第一条）")
    args = ap.parse_args()

    project_root = Path(args.project_root).resolve()
    cfg = parse_frontmatter_channel(project_root)
    repo = args.repo or cfg.get("issue_repo") or DEFAULT_REPO
    issue_url = cfg.get("issue_url") or "https://github.com/%s/issues/new?template=tw-feedback.yml" % repo
    auto_submit = str(cfg.get("auto_submit", "true")).strip().lower() not in ("false", "off", "no", "0")
    submit = args.yes and not args.dry_run and auto_submit

    queue_path, pending, _ = load_queue(project_root)
    if not pending:
        print("✓ 无待提交反馈（%s）" % queue_path)
        return 0
    if not args.all:
        pending = pending[:1]

    if not submit:
        reason = "profile 关闭了 auto_submit" if (args.yes and not auto_submit) else "未带 --yes"
        print("[DRY RUN] %s；只预览，不创建任何 issue。共 %d 条待提交。" % (reason, len(pending)))
        ledger = load_ledger(project_root)
        for idx, cells in pending:
            title, body = build_issue(cfg, cells, project_root.name)
            if item_key(project_root.name, cells[6], cells[2]) in {x.get("key") for x in ledger["submitted"]}:
                print("  [SKIP] 已提交过：%s" % title)
                continue
            print("--- 标题 ---\n%s\n--- 正文 ---\n%s" % (title, body))
            print("--- 人工降级链接 ---\n%s" % prefilled_url(repo, title, body))
        print("反馈入口：%s" % issue_url)
        return 0

    ok, why = gh_ready()
    if not ok:
        print("ERROR：%s。反馈仍保留在本地队列，未丢失。" % why)
        title, body = build_issue(cfg, pending[0][1], project_root.name)
        print("人工提交：%s" % prefilled_url(repo, title, body))
        return 2

    ledger = load_ledger(project_root)
    seen = {x.get("key") for x in ledger["submitted"]}
    today = datetime.date.today().isoformat()
    done = 0
    for idx, cells in pending:
        title, body = build_issue(cfg, cells, project_root.name)
        key = item_key(project_root.name, cells[6], cells[2])
        if key in seen:
            print("  [SKIP] 已提交过：%s" % title)
            continue
        success, url, err = create_issue(repo, title, body, args.label)
        if not success:
            print("ERROR：提交失败：%s" % err)
            print("反馈仍保留在本地队列，未丢失。")
            print("人工提交：%s" % prefilled_url(repo, title, body))
            return 1
        num = re.search(r"/issues/(\d+)", url)
        label = ("Issue #%s" % num.group(1)) if num else "Issue"
        lines = queue_path.read_text(encoding="utf-8").splitlines()
        rewrite_queue(queue_path, lines, idx, "已提交(%s,%s)" % (label, today))
        ledger["submitted"].append({"key": key, "title": title, "url": url, "date": today})
        (project_root / LEDGER_NAME).write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        seen.add(key)
        done += 1
        print("✓ 已提交 %s：%s" % (label, url or "(URL 未解析)"))

    remain = len(load_queue(project_root)[1])
    print("✓ 本次提交 %d 条，队列剩余 %d 条待提交。反馈入口：%s" % (done, remain, issue_url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
