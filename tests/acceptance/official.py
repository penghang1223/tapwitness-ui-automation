"""Claude Code 官方 CLI 冒烟验收。"""

import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from .common import (
    ROOT, VAL8, cli, has_issue, py, read, skill_names,
)


def c_official_validate():
    if not shutil.which("claude"):
        return None, "SKIP / 未安装 claude CLI"
    rc, out = cli("claude", "plugin", "validate", ".", cwd=str(ROOT))
    n = len(re.findall(r"skills: tw:", out))
    ok = rc == 0 and n == 31
    return ok, ("PASS / 官方 validate 识别 31 个 tw:* skills") if ok else \
        "FAIL / rc=%d skills=%d | %s" % (rc, n, out[-180:].replace("\n", " / "))


def c_official_directory_profile():
    if not shutil.which("claude"):
        return None, "SKIP / 未安装 claude CLI"
    rc, out = cli("claude", "plugin", "validate", ".", "--profile", "directory",
                  cwd=str(ROOT))
    bad = "Found 1 problem the plugin directory refuses" in out
    ok = rc == 0 and not bad
    return ok, ("PASS / 目录级校验（LICENSE 等）通过") if ok else \
        "FAIL / rc=%d | %s" % (rc, out[-200:].replace("\n", " / "))


def c_official_isolated_install():
    if not shutil.which("claude"):
        return None, "SKIP / 未安装 claude CLI"
    with tempfile.TemporaryDirectory(prefix="twcfg-") as cfg:
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = cfg
        steps = []
        rc, out = cli("claude", "plugin", "marketplace", "add", str(ROOT),
                      "--json", env=env, cwd=str(ROOT))
        steps.append(("add", rc, out))
        rc2, out2 = cli("claude", "plugin", "install", "tw@tw-marketplace",
                        "-y", "--json", env=env, cwd=str(ROOT))
        steps.append(("install", rc2, out2))
        rc3, out3 = cli("claude", "plugin", "list", "--json", env=env, cwd=str(ROOT))
        steps.append(("list", rc3, out3))
        try:
            listed = json.loads(out3)
            enabled = any(p.get("id") == "tw@tw-marketplace" and p.get("enabled")
                          for p in listed)
        except Exception:
            enabled = False
        rc4, out4 = cli("claude", "plugin", "details", "tw@tw-marketplace",
                        env=env, cwd=str(ROOT))
        steps.append(("details", rc4, out4))
        has31 = "Skills (31)" in out4
        ok = all(s[1] == 0 for s in steps) and enabled and has31
        return ok, ("PASS / 隔离 marketplace add→install→list→details，enabled 且 Skills(31)") \
            if ok else "FAIL / %s enabled=%s has31=%s" % (
                [(s[0], s[1]) for s in steps], enabled, has31)


def c_official_session_visibility():
    """真实 -p 会话：临时 --plugin-dir 加载，列出 /tw: 命令并与仓库比对。"""
    if not shutil.which("claude"):
        return None, "SKIP / 未安装 claude CLI"
    prompt = ("List the exact bare names of every available skill from the tw plugin "
              "(the /tw: commands). Output ONLY a single comma-separated list of bare "
              "names, no prefix, no explanation, no numbering.")
    rc, out = cli("claude", "-p", prompt, "--plugin-dir", str(ROOT),
                  cwd=str(ROOT), timeout=110)
    if "Not logged in" in out or "Please run /login" in out:
        return None, "SKIP / Claude Code 未登录，无法起真实会话"
    if rc != 0 or "TIMEOUT" in out:
        return False, "FAIL / 会话 rc=%d %s" % (rc, out[:150])
    # 只接受裸命令名（小写 + 连字符）。Claude Code 可能把环境提示混进 -p 输出，
    # 例如工作区未信任时的 "Ignoring 2 permissions.allow entries ..." 两行；
    # 这些含空格/大写/路径的噪声不应被当作命令名，也不应改用户全局信任设置。
    got = {x.strip() for x in re.split(r"[,\n]", out)
           if re.fullmatch(r"[a-z][a-z0-9-]*", x.strip())}
    expected = set(skill_names())
    ok = got == expected
    return ok, ("PASS / 真实会话可见 31 个命令，与仓库完全一致") if ok else \
        "FAIL / 会话多出 %s，缺少 %s" % (sorted(got - expected)[:5], sorted(expected - got)[:5])


def c_official_session_new_feature():
    """Phase 9 第 3 步：真实会话执行 /tw:new-feature，落盘状态机并通过校验器。

    在临时宿主项目中预置 profile，用 --permission-mode bypassPermissions 绕过
    Claude Code 对 .claude/ 的敏感路径保护（仅限本临时目录，不触碰用户项目）。
    """
    if not shutil.which("claude"):
        return None, "SKIP / 未安装 claude CLI"
    with tempfile.TemporaryDirectory(prefix="twsession-") as hostdir:
        host = Path(hostdir)
        (host / ".claude").mkdir()
        shutil.copyfile(ROOT / "tw" / "templates" / "project_profile.template.md",
                        host / ".claude" / "project_profile.md")
        prompt = (
            'Invoke the /tw:new-feature skill for feature name "demo_smoke" and follow it '
            'literally. The plugin root is %s (its tw/ directory is there). ACTUALLY create '
            'the files on disk: .claude/workflows/demo_smoke/state.json, '
            '.claude/workflows/.current, .claude/workflows/dashboard.md. Then run step 6: '
            'python3 %s/tw/tools/validate_workflow.py --workflows-dir .claude/workflows '
            'and report its result. Reply concisely.' % (ROOT, ROOT))
        rc, out = cli("claude", "-p", prompt, "--plugin-dir", str(ROOT),
                      "--permission-mode", "bypassPermissions",
                      cwd=str(host), timeout=175)
        if "Not logged in" in out or "Please run /login" in out:
            return None, "SKIP / Claude Code 未登录，无法起真实会话"
        wf = host / ".claude" / "workflows"
        sf = wf / "demo_smoke" / "state.json"
        if not sf.exists():
            return False, "FAIL / 会话未落盘 state.json | %s" % out.replace("\n", " / ")[:150]
        try:
            state = json.loads(read(sf))
        except Exception as exc:
            return False, "FAIL / state.json 无法解析 %s" % exc
        rc2, out2 = py(VAL8, "--workflows-dir", str(wf), "--strict")
        cur_file = wf / ".current"
        current = cur_file.read_text(encoding="utf-8").strip() if cur_file.exists() else None
        checks = [
            ("校验器 strict 通过", rc2 == 0 and not has_issue(out2)),
            (".current 指向 demo_smoke", current == "demo_smoke"),
            ("feature 与目录名一致", state.get("feature") == "demo_smoke"),
            ("8 个阶段键", len(state.get("stages", {})) == 8),
            ("阶段 1 in_progress", state.get("stages", {}).get("1_business", {}).get("status") == "in_progress"),
            ("current_stage=1", state.get("current_stage") == 1),
        ]
        bad = [name for name, ok in checks if not ok]
        return (not bad), ("PASS / 真实会话执行 /tw:new-feature，落盘状态机 strict 通过") if not bad \
            else "FAIL / %s | %s" % (bad, out2.replace("\n", " / ")[:120])
