"""反馈预览、提交和恢复验收。"""

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from .common import (
    PACKS, ROOT, SKILLS, TOOLS, VAL8, has_issue, py, read,
)


FEEDBACK_REPO = "penghang1223/tapwitness-ui-automation"
FEEDBACK_URL = "https://github.com/%s/issues/new?template=tw-feedback.yml" % FEEDBACK_REPO


def c_fb_profile_points_to_repo():
    bad = []
    for name in ("project_profile.template.md", "subsystem_profile.template.md"):
        t = read(ROOT / "tw" / "templates" / name)
        for token in ("issue_repo:", "issue_url:", "auto_submit:", FEEDBACK_REPO):
            if token not in t:
                bad.append("%s 缺 %s" % (name, token))
        if "<Issue 新建 URL>" in t:
            bad.append("%s 仍是占位 URL" % name)
    rc, out = py(VAL8, "--check-profile-contract")
    if rc != 0 or has_issue(out):
        bad.append("profile 契约未通过：%s" % out.replace("\n", " / ")[:100])
    return (not bad), ("PASS / 两份 profile 指向 %s，契约 0 ERROR" % FEEDBACK_REPO) if not bad \
        else "FAIL / " + "; ".join(bad[:4])


def c_fb_issue_form():
    yml = ROOT / ".github" / "ISSUE_TEMPLATE" / "tw-feedback.yml"
    cfg = ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"
    bad = []
    if not yml.exists() or not cfg.exists():
        return False, "FAIL / .github/ISSUE_TEMPLATE 缺失"
    try:
        import yaml
        d = yaml.safe_load(read(yml))
        if not isinstance(d, dict):
            bad.append("issue form 不是 mapping")
        else:
            ids = {x.get("id") for x in d.get("body", []) if isinstance(x, dict)}
            need = {"source_project", "source_feature", "date", "stage", "platform",
                    "phenomenon", "root_cause", "countermeasure", "suggested_location", "sanity"}
            if not need <= ids:
                bad.append("字段缺失 %s" % sorted(need - ids))
            if "tw-feedback" not in (d.get("labels") or []):
                bad.append("未打 tw-feedback 标签")
            if "[tw-feedback]" not in str(d.get("title", "")):
                bad.append("标题缺 [tw-feedback] 前缀")
    except Exception as exc:
        bad.append("YAML 解析失败 %s" % exc)
    return (not bad), "PASS / GitHub Issue Form 字段齐全 + 标签 + 标题前缀" if not bad \
        else "FAIL / " + "; ".join(bad[:4])


def c_fb_skill_calls_submitter():
    t = read(SKILLS / "feedback" / "SKILL.md")
    need = ["submit_feedback.py", "--yes", "--dry-run", FEEDBACK_REPO,
            "tw_feedback_submitted.json", "gh issue create", "脱敏", "保留在本地队列"]
    bad = [x for x in need if x not in t]
    if "<Issue 新建 URL>" in t:
        bad.append("仍含占位 URL")
    return (not bad), "PASS / /tw:feedback 调用提交脚本 + 降级 + 脱敏说明" if not bad \
        else "FAIL / 缺 " + ", ".join(bad[:4])


def c_fb_script_static():
    t = read(TOOLS / "submit_feedback.py")
    need = ["--dry-run", "--yes", "gh issue create", "REDACTIONS", "prefilled_url",
            "auto_submit", "tw_feedback_submitted.json", "sys.stdout.reconfigure",
            "Path(__file__)", "--project-root", "--label"]
    bad = [x for x in need if x not in t]
    if re.search(r"^\s*import yaml\b", t, re.M):
        bad.append("引入了第三方依赖 yaml")
    return (not bad), "PASS / 提交脚本：零第三方依赖 + 脱敏 + 预览 + 降级" if not bad \
        else "FAIL / 缺 " + ", ".join(bad[:4])


def _fb_fixture(root):
    claude = root / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "tw" / "templates" / "project_profile.template.md",
                    claude / "project_profile.md")
    (claude / "tw_feedback.md").write_text(
        "| 日期 | 阶段 | 现象 | 根因 | 对策 | 适用平台 | 来源 feature | 状态 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 2026-11-20 | 4 用例开发 | 登录页 /Users/narain/secret/proj 点击超时，联系 a@b.com | "
        "元素遮挡 | 等可见再点，凭据 gho_abcdefghijklmnopqrstuvwxyz1234 password=short123 内网 192.168.1.100 | web | login | 待提交 |\n",
        encoding="utf-8")
    return claude


def c_fb_dry_run_sanitizes():
    with tempfile.TemporaryDirectory(prefix="twfbtest-") as td:
        claude = _fb_fixture(Path(td))
        before = (claude / "tw_feedback.md").read_bytes()
        rc, out = py(TOOLS / "submit_feedback.py", "--project-root", td, "--dry-run")
        bad = []
        if rc != 0:
            bad.append("rc=%d %s" % (rc, out[:120]))
        for token in ("[DRY RUN]", "[PATH]", "[EMAIL]", "[REDACTED]", "[IP]", "issues/new?"):
            if token not in out:
                bad.append("输出缺 %s" % token)
        for secret in ("/Users/narain/secret/proj", "a@b.com",
                       "gho_abcdefghijklmnopqrstuvwxyz1234", "short123", "192.168.1.100"):
            if secret in out:
                bad.append("敏感信息泄漏 %s" % secret)
        if (claude / "tw_feedback.md").read_bytes() != before:
            bad.append("dry-run 改写了队列")
        if (claude / "tw_feedback_submitted.json").exists():
            bad.append("dry-run 写了去重台账")
        if FEEDBACK_URL not in out:
            bad.append("反馈入口未指向真实仓库")
    return (not bad), "PASS / dry-run 脱敏且零外部写" if not bad \
        else "FAIL / " + "; ".join(bad[:4])


def c_fb_no_submit_when_disabled():
    with tempfile.TemporaryDirectory(prefix="twfbtest-") as td:
        claude = _fb_fixture(Path(td))
        p = claude / "project_profile.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "auto_submit: true", "auto_submit: false"), encoding="utf-8")
        rc, out = py(TOOLS / "submit_feedback.py", "--project-root", td, "--yes")
        ok = rc == 0 and "[DRY RUN]" in out and "关闭了 auto_submit" in out \
             and not (claude / "tw_feedback_submitted.json").exists()
    return ok, "PASS / auto_submit=false 强制只预览，不触发提交" if ok \
        else "FAIL / rc=%d %s" % (rc, out.replace("\n", " / ")[:150])


def c_fb_submit_recovery():
    with tempfile.TemporaryDirectory(prefix="twfb-recovery-") as td:
        root = Path(td)
        claude = _fb_fixture(root)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text(
            "#!%s\n" % sys.executable +
            "import os, pathlib, sys\n"
            "if sys.argv[1:3] == ['auth', 'status']:\n"
            "    sys.exit(0)\n"
            "p = pathlib.Path(os.environ['TW_FAKE_GH_COUNT'])\n"
            "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1')\n"
            "if os.environ.get('TW_FAKE_GH_FAIL') == '1':\n"
            "    print('网络中断', file=sys.stderr)\n"
            "    sys.exit(1)\n"
            "print('https://github.com/%s/issues/42')\n" % FEEDBACK_REPO,
            encoding="utf-8")
        gh.chmod(0o755)
        env = os.environ.copy()
        env.update(PATH=str(bin_dir) + os.pathsep + env.get("PATH", ""),
                   TW_FAKE_GH_COUNT=str(root / "count"), TW_FAKE_GH_FAIL="1")
        script = TOOLS / "submit_feedback.py"
        command = [script, "--project-root", root]
        rc, out = py(*command, "--dry-run", env=env)
        match = re.search(r"预览校验值：([0-9a-f]{64})", out)
        if rc != 0 or not match:
            return False, "预览缺校验值：%s" % out
        approval = match.group(1)
        rc, out = py(*command, "--yes", "--approval", "incorrect", env=env)
        if rc != 1 or (root / "count").exists():
            return False, "错误预览校验值未拦截：%s" % out
        queue = claude / "tw_feedback.md"
        original = read(queue)
        queue.write_text(original.replace("元素遮挡", "元素被遮挡"), encoding="utf-8")
        rc, out = py(*command, "--yes", "--approval", approval, env=env)
        if rc != 1 or (root / "count").exists():
            return False, "预览后修改内容未拦截：%s" % out
        queue.write_text(original, encoding="utf-8")
        rc, out = py(*command, "--yes", "--approval", approval, env=env)
        ledger_path = claude / "tw_feedback_submitted.json"
        ledger = json.loads(read(ledger_path))
        entry = ledger["submitted"][0]
        if rc != 1 or entry.get("status") != "pending" or read(root / "count") != "1":
            return False, "首次失败未记录待核对：%s" % out
        env["TW_FAKE_GH_FAIL"] = "0"
        rc, out = py(*command, "--yes", "--approval", approval, env=env)
        if rc != 1 or "待核对" not in out or read(root / "count") != "1":
            return False, "待核对条目被重复提交：%s" % out
        url = "https://github.com/%s/issues/42" % FEEDBACK_REPO
        rc, out = py(*command, "--resolve", entry["key"], "--issue-url", url, env=env)
        if rc != 0:
            return False, "记录远端结果失败：%s" % out
        rc, out = py(*command, "--yes", "--approval", approval, env=env)
        if rc != 0 or "Issue #42" not in read(claude / "tw_feedback.md") or read(root / "count") != "1":
            return False, "恢复队列状态失败：%s" % out
        ledger_path.write_text("{", encoding="utf-8")
        rc, out = py(*command, "--dry-run", env=env)
        # 空队列无需读取台账，重新加入待提交条目再验证损坏台账。
        _fb_fixture(root)
        rc, out = py(*command, "--yes", "--approval", approval, env=env)
        if rc != 1 or "无法读取反馈台账" not in out or read(root / "count") != "1":
            return False, "损坏台账未阻止重复提交：%s" % out
        ledger_path.unlink()
        rc, out = py(*command, "--dry-run", env=env)
        approval = re.search(r"预览校验值：([0-9a-f]{64})", out).group(1)
        rc, out = py(*command, "--yes", "--approval", approval, env=env)
        ledger = json.loads(read(ledger_path))
        if (rc != 0 or ledger["submitted"][0].get("url") != url
                or "Issue #42" not in read(queue) or read(root / "count") != "2"):
            return False, "成功提交或本地回写失败：%s" % out
    return True, "PASS / 网络结果不明、人工核对、队列恢复和损坏台账"


def c_fb_pack_stage8_refs():
    bad = []
    for p in sorted(PACKS.glob("*/stages/stage8_kb_feedback.md")):
        t = read(p)
        if "submit_feedback.py" not in t:
            bad.append(p.relative_to(ROOT).as_posix() + " 未引用提交脚本")
        if ".issue_templates/feedback.md" in t:
            bad.append(p.relative_to(ROOT).as_posix() + " 仍引用旧模板")
    return (not bad), "PASS / 4 份 stage8 均指向自动提交通道" if not bad \
        else "FAIL / " + "; ".join(bad[:4])
