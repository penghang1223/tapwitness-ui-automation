#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TW 工作流框架 · 可复现验收套件。

把架构规格 §12 Phase 0–8 的验收命令、§13 不变式中可静态验证的条目、
反向破坏测试与端到端状态流转模拟固化为一条命令：

    python3 tests/run_acceptance.py               # 全套
    python3 tests/run_acceptance.py --quick       # 只跑静态契约
    python3 tests/run_acceptance.py --official    # 追加 Claude Code 官方 CLI 冒烟

退出码：全部 PASS（SKIP 不算失败）→ 0；任一 FAIL → 1。

设计原则：只读 + 临时目录。所有需要改仓库文件的反向测试都在 try/finally
中恢复；隔离安装用临时 CLAUDE_CONFIG_DIR，不碰用户真实 Claude 配置。
"""
import sys
import os
import re
import json
import copy
import shutil
import argparse
import tempfile
import datetime
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
PACKS = ROOT / "tw" / "packs"
TOOLS = ROOT / "tw" / "tools"
REC_TOOLS = ROOT / "tw" / "workflows" / "record-driven" / "tools"
VAL8 = str(TOOLS / "validate_workflow.py")
VALR = str(REC_TOOLS / "validate_record_workflow.py")
GEN8 = str(TOOLS / "gen_dispatchers.py")
GENR = str(REC_TOOLS / "gen_record_dispatchers.py")
HANDOFF = str(TOOLS / "gen_handoff.py")

KEYS8 = ["1_business", "2_data", "3_assertion", "4_case",
         "5_verify", "6_e2e", "7_report", "8_kb_feedback"]
KEYSR = ["1_capture", "2_casegen", "3_case", "4_run", "5_review"]
ART8 = {
    "1_business": ["stage1_business.md", "stage1_cases.md", "stage1_cases.json"],
    "2_data": ["stage2_data.md"],
    "3_assertion": ["stage3_assertions.md", "stage3_assertions.json"],
    "4_case": ["stage4_plan.md", "stage4_files.md"],
    "5_verify": ["stage5_verify.log"],
    "6_e2e": ["stage6_e2e.md"],
    "7_report": ["stage7_report.md"],
    "8_kb_feedback": ["stage8_kb_feedback.md"],
}
ARTR = {
    "1_capture": ["stage1_record.md"],
    "2_casegen": ["stage2_cases.md", "stage2_cases.json"],
    "3_case": ["stage3_plan.md", "stage3_files.md"],
    "4_run": ["stage4_run.log"],
    "5_review": ["stage5_review.md"],
}
NOW = datetime.datetime.now().isoformat()


# --------------------------------------------------------------------------
# 基础设施
# --------------------------------------------------------------------------
def py(*args, cwd=None, env=None, timeout=60):
    """运行 python 脚本，返回 (rc, 合并输出)。"""
    try:
        r = subprocess.run([sys.executable, *map(str, args)], cwd=cwd,
                           env=env, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def cli(*args, cwd=None, env=None, timeout=120):
    """运行外部命令，返回 (rc, 合并输出)。"""
    try:
        r = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, "command not found: %s" % args[0]
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def clean(out):
    """从校验器输出里提取 ERROR / WARNING 数量。

    注意：校验器成功时也会打印 'PASS：0 ERROR / 0 WARNING'，因此不能用
    子串计数，只认行首的 ERROR / WARNING 行（真实诊断行的格式）。
    """
    return (len(re.findall(r"(?m)^\s*ERROR\b", out)),
            len(re.findall(r"(?m)^\s*WARNING\b", out)))


def has_issue(out):
    e, w = clean(out)
    return bool(e or w)


def expect_ok(rc, out, strict=False):
    if rc != 0:
        return False, "rc=%d | %s" % (rc, out.replace("\n", " / ")[:170])
    e, w = clean(out)
    if e or (strict and w):
        return False, "ERROR=%d WARNING=%d | %s" % (e, w, out.replace("\n", " / ")[:150])
    return True, "PASS / 0 ERROR / %d WARNING" % w


def expect_fail(rc, out, keyword=None):
    if rc == 0:
        return False, "期望失败但 rc=0 | %s" % out.replace("\n", " / ")[:150]
    if keyword and keyword not in out:
        return False, "rc=%d 但缺关键字 %r | %s" % (rc, keyword, out.replace("\n", " / ")[:150])
    return True, "按预期拦截 rc=%d%s" % (rc, (" / " + keyword) if keyword else "")


def skill_dirs():
    return sorted([p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").exists()])


def skill_names():
    return [p.name for p in skill_dirs()]


def read(path):
    return Path(path).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# fixture 构造器（严格贴合两个校验器的字段规则）
# --------------------------------------------------------------------------
def write_8(feat, statuses, cur, mode="manual", bypasses=None, stage_extra=None,
            dashboard=True, artifacts=True):
    """写一个 8 阶段 state.json + dashboard + 产出文件；返回 wf_dir。"""
    wf = feat.parent
    wf.mkdir(parents=True, exist_ok=True)
    feat.mkdir(parents=True, exist_ok=True)
    stages = {}
    for i, (key, status) in enumerate(zip(KEYS8, statuses), start=1):
        hi = False if status in {"done", "skipped"} else None
        entry = {"status": status, "human_intervention": hi,
                 "intervention_note": None}
        if status == "in_progress":
            entry["started_at"] = NOW
        if status == "done":
            entry["done_at"] = NOW
        if stage_extra and key in stage_extra:
            entry.update(stage_extra[key])
        stages[key] = entry
        if artifacts and status == "done":
            for art in ART8[key]:
                (feat / art).write_text("# fixture 产出\n", encoding="utf-8")
    state = {"feature": feat.name, "created": NOW, "mode": mode,
             "current_stage": cur, "stages": stages,
             "bypasses": bypasses or []}
    (feat / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    (wf / ".current").write_text(feat.name + "\n", encoding="utf-8")
    if dashboard:
        done = all(s in {"done", "skipped"} for s in statuses)
        header = "**1 / 1 完成** | **0 进行中** | **0 未启动**" if done else \
                 "**0 / 1 完成** | **1 进行中** | **0 未启动**"
        (wf / "dashboard.md").write_text(
            "# %s 看板\n\n%s\n\n## 进行中\n| feature |\n|---|\n| %s |\n"
            % (feat.name, header, feat.name), encoding="utf-8")
    return wf


def write_rec(feat, statuses, cur, mode="manual", bypasses=None, stage_extra=None,
              dashboard=True, artifacts=True):
    """写一个录制 record_state.json + dashboard + 产出文件；返回 rwf_dir。"""
    wf = feat.parent
    wf.mkdir(parents=True, exist_ok=True)
    feat.mkdir(parents=True, exist_ok=True)
    stages = {}
    for key, status in zip(KEYSR, statuses):
        hi = False if status in {"done", "skipped"} else None
        entry = {"status": status, "human_intervention": hi,
                 "intervention_note": None}
        if status == "in_progress":
            entry["started_at"] = NOW
        if stage_extra and key in stage_extra:
            entry.update(stage_extra[key])
        stages[key] = entry
        if artifacts and status == "done":
            for art in ARTR[key]:
                (feat / art).write_text("# fixture 产出\n", encoding="utf-8")
    state = {"feature": feat.name, "workflow": "record-driven", "created": NOW,
             "mode": mode, "current_stage": cur, "stages": stages,
             "bypasses": bypasses or []}
    (feat / "record_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    (wf / ".current").write_text(feat.name + "\n", encoding="utf-8")
    if dashboard:
        done = all(s in {"done", "skipped"} for s in statuses)
        header = "**1 / 1 完成** | **0 进行中** | **0 未启动**" if done else \
                 "**0 / 1 完成** | **1 进行中** | **0 未启动**"
        (wf / "dashboard.md").write_text(
            "# %s 录制看板\n\n%s\n\n## 进行中\n| feature |\n|---|\n| %s |\n"
            % (feat.name, header, feat.name), encoding="utf-8")
    return wf


def fresh_8(tmp, feature="demo"):
    feat = Path(tmp) / ".claude" / "workflows" / feature
    return feat


def fresh_rec(tmp, feature="demo"):
    feat = Path(tmp) / ".claude" / "record-workflows" / feature
    return feat


def base8_statuses(cur):
    """阶段 1..cur-1 done，cur in_progress，其余 pending。"""
    out = []
    for i in range(1, 9):
        out.append("done" if i < cur else ("in_progress" if i == cur else "pending"))
    return out


def baseR_statuses(cur):
    out = []
    for i in range(1, 6):
        out.append("done" if i < cur else ("in_progress" if i == cur else "pending"))
    return out


def v8(wf, strict=True):
    args = [VAL8, "--workflows-dir", str(wf)]
    if strict:
        args.append("--strict")
    return py(*args)


def vr(wf, strict=True):
    args = [VALR, "--workflows-dir", str(wf)]
    if strict:
        args.append("--strict")
    return py(*args)


# --------------------------------------------------------------------------
# 静态契约用例（§12 Phase 0/1/3/4/5/6/7/8 + §13）
# --------------------------------------------------------------------------
def c_manifests():
    p = json.loads(read(ROOT / ".claude-plugin" / "plugin.json"))
    m = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))
    errs = []
    if p.get("name") != "tw":
        errs.append("plugin.name")
    if not p.get("version"):
        errs.append("plugin.version")
    if not p.get("license"):
        errs.append("plugin.license")
    if m.get("plugins", [{}])[0].get("name") != "tw":
        errs.append("marketplace.plugins[0].name")
    return (not errs), ("PASS / plugin %s v%s" % (p.get("name"), p.get("version"))) if not errs \
        else "FAIL / 缺字段 %s" % errs


def c_skill_frontmatter():
    dirs = skill_dirs()
    errs = []
    names = []
    for d in dirs:
        text = read(d / "SKILL.md")
        if not text.startswith("---"):
            errs.append(d.name + ": 缺 frontmatter")
            continue
        fm = text.split("---", 2)[1]
        m = re.search(r"^name:\s*(\S+)\s*$", fm, re.M)
        if not m:
            errs.append(d.name + ": 缺 name")
        elif m.group(1) != d.name:
            errs.append("%s: name=%s 与目录不符" % (d.name, m.group(1)))
        else:
            names.append(m.group(1))
        if not re.search(r"^description:", fm, re.M):
            errs.append(d.name + ": 缺 description")
    if len(dirs) != 31:
        errs.append("命令数 %d ≠ 31" % len(dirs))
    if len(set(names)) != len(names):
        errs.append("命令名重复")
    return (not errs), ("PASS / 31 个 SKILL.md frontmatter 一致") if not errs \
        else "FAIL / " + "; ".join(errs[:5])


def c_readme_consistency():
    text = read(ROOT / "README.md")
    missing = [n for n in skill_names() if n not in text]
    packs = [p.name for p in PACKS.iterdir() if p.is_dir() and (p / "pack.yaml").exists()]
    missing_packs = [p for p in packs if p not in text]
    ok = not missing and not missing_packs and "31" in text
    return ok, ("PASS / README 覆盖 31 命令 + 4 域包") if ok else \
        "FAIL / 缺命令 %s 缺域包 %s" % (missing[:4], missing_packs)


def c_required_files():
    required = [
        ".claude/settings.local.json", ".gitignore", "README.md",
        "docs/install.md", "docs/使用教程.md", "docs/架构设计方案.md",
        ".issue_templates/feedback.md",
        "tw/protocols/state-protocol.md", "tw/protocols/gate-protocol.md",
        "tw/protocols/stage-registry.md", "tw/protocols/assertion-protocol.md",
        "tw/protocols/case-expansion-protocol.md", "tw/protocols/dump-artifact-protocol.md",
        "tw/protocols/feedback_absorbed.json",
        "tw/templates/_template/state.json", "tw/templates/pack.template.yaml",
        "tw/templates/project_profile.template.md", "tw/templates/subsystem_profile.template.md",
        "tw/workflows/record-driven/workflow.yaml",
        "tw/workflows/record-driven/protocols/state-protocol.md",
        "tw/workflows/record-driven/protocols/gate-protocol.md",
        "tw/workflows/record-driven/templates/record_state.json",
        "tw/workflows/record-driven/templates/dashboard.md",
        "baselines/ios-validate-normal-baseline.txt",
        "baselines/ios-validate-strict-baseline.txt",
        VAL8, GEN8, HANDOFF, VALR, GENR,
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    return (not missing), ("PASS / §15.1 关键文件 %d 项齐全" % len(required)) if not missing \
        else "FAIL / 缺失 %s" % missing[:6]


def c_json_assets():
    paths = [
        ROOT / "tw/protocols/feedback_absorbed.json",
        ROOT / "tw/templates/_template/state.json",
        ROOT / "tw/workflows/record-driven/templates/record_state.json",
    ]
    try:
        for p in paths:
            json.loads(read(p))
    except Exception as exc:
        return False, "FAIL / %s" % exc
    return True, "PASS / 3 份 JSON 模板与注册表可解析"


def c_gen8_check():
    rc, out = py(GEN8, "--check")
    return expect_ok(rc, out, strict=True)


def c_genr_check():
    rc, out = py(GENR, "--check")
    return expect_ok(rc, out, strict=True)


def c_check_pack_strict():
    rc, out = py(VAL8, "--check-pack", "--strict")
    return expect_ok(rc, out, strict=True)


def c_check_pack_single():
    rc, out = py(VAL8, "--check-pack", str(PACKS / "playwright-python"))
    return expect_ok(rc, out, strict=True)


def c_profile_contract():
    rc, out = py(VAL8, "--check-profile-contract")
    return expect_ok(rc, out, strict=True)


def c_dump_contract():
    rc, out = py(VAL8, "--check-dump-contract")
    return expect_ok(rc, out, strict=True)


def c_record_workflow_def():
    rc, out = py(VALR, "--check-workflow")
    return expect_ok(rc, out, strict=True)


def c_zero_coupling():
    s8, sr = [], []
    for d in skill_dirs():
        text = read(d / "SKILL.md")
        if "[TW 阶段" in text:
            s8.append(d)
        elif "[TW 录制阶段" in text:
            sr.append(d)
    bad = []
    for d in s8:
        t = read(d / "SKILL.md")
        if "record-workflows" in t or "record_state" in t:
            bad.append(d.name + " 含录制标识")
    for d in sr:
        if ".claude/workflows" in read(d / "SKILL.md"):
            bad.append(d.name + " 含 8 阶段状态目录")
    ok = not bad and len(s8) == 8 and len(sr) == 5
    return ok, ("PASS / 8+5 分发器零耦合") if ok else "FAIL / " + "; ".join(bad[:4])


def c_capability_gating():
    hits = []
    for base in (SKILLS, PACKS):
        for p in base.rglob("*.md"):
            if re.search(r'pack\s*==\s*["\']', read(p)):
                hits.append(str(p.relative_to(ROOT)))
    return (not hits), ("PASS / 无硬编码域包白名单") if not hits else "FAIL / %s" % hits[:3]


def c_no_cross_import():
    a, b = read(VAL8), read(VALR)
    bad = re.search(r"(?:import|from)\s+.*validate_(?:record_)?workflow", a) or \
          re.search(r"(?:import|from)\s+.*validate_(?:record_)?workflow", b)
    return (bad is None), ("PASS / 两个校验器互不 import") if bad is None else "FAIL / 存在跨引用"


def c_tool_hygiene():
    # 需要推导仓库根目录的 4 个脚本；gen_handoff 只写用户显式指定的项目目录，
    # 不依赖 __file__ 相对路径，因此只检查它的 UTF-8 重配置。
    need_root = [TOOLS / "gen_dispatchers.py", TOOLS / "validate_workflow.py",
                 REC_TOOLS / "gen_record_dispatchers.py",
                 REC_TOOLS / "validate_record_workflow.py"]
    scripts = need_root + [TOOLS / "gen_handoff.py"]
    bad = []
    for p in scripts:
        t = read(p)
        if "sys.stdout.reconfigure" not in t:
            bad.append(p.name + ": 缺 UTF-8 重配置")
        if p in need_root and "Path(__file__)" not in t:
            bad.append(p.name + ": 路径未由 __file__ 推导")
    return (not bad), ("PASS / 5 个脚本 UTF-8 + 4 个 __file__ 路径") if not bad \
        else "FAIL / " + "; ".join(bad[:4])


def c_yaml_guard():
    ok = all("isinstance(data, dict)" in read(p) for p in (VAL8, VALR))
    return ok, ("PASS / yaml.safe_load 有 dict 守卫") if ok else "FAIL / 缺 isinstance 守卫"


def c_gitignore():
    t = read(ROOT / ".gitignore")
    miss = [x for x in ("page_cache/", "storage_state.json", ".current") if x not in t]
    return (not miss), ("PASS / 运行时产物已 ignore") if not miss else "FAIL / 缺 %s" % miss


def c_six_sections():
    needed = ["## 目标", "## 前置输入", "## 步骤", "## 产出要求",
              "## 审查门判据", "## Exit Gate 输入"]
    s8_files = sorted(PACKS.glob("*/stages/*.md"))
    r_files = sorted(PACKS.glob("*/workflows/record-driven/stages/*.md"))
    files = s8_files + r_files
    bad = []
    for p in files:
        t = read(p)
        miss = [h for h in needed if h not in t]
        if miss:
            bad.append("%s 缺 %s" % (p.relative_to(ROOT), miss[0]))
    ok = not bad and len(s8_files) == 33 and len(r_files) == 5
    return ok, ("PASS / %d 份阶段指令六段结构 + Exit Gate 收束（33+5）" % len(files)) if ok \
        else "FAIL / s8=%d rec=%d %s" % (len(s8_files), len(r_files), bad[:4])


def c_packs_and_subtree():
    packs = sorted(p.name for p in PACKS.iterdir()
                   if p.is_dir() and (p / "pack.yaml").exists())
    with_rec = [p for p in packs if (PACKS / p / "workflows" / "record-driven").exists()]
    bad = [p for p in packs if not (PACKS / p / "pitfalls.md").exists()]
    ok = packs == ["android-airtest", "android-appium", "ios-appium", "playwright-python"] \
         and with_rec == ["playwright-python"] and not bad
    return ok, ("PASS / 4 域包 + 坑点库；录制子树仅 playwright-python") if ok else \
        "FAIL / packs=%s with_rec=%s 缺坑点=%s" % (packs, with_rec, bad)


def c_handoff():
    with tempfile.TemporaryDirectory(prefix="twhandoff-") as tmp:
        host = Path(tmp)
        (host / "HANDOFF.md").write_text("# 宿主项目\n\n手写内容保留\n", encoding="utf-8")
        rc, out = py(HANDOFF, str(host))
        if rc != 0:
            return False, "写入失败 " + out[:120]
        text = read(host / "HANDOFF.md")
        checks = [
            "手写内容保留" in text,
            text.count("<!-- tw:start -->") == 1,
            text.count("<!-- tw:end -->") == 1,
            "/tw:record-review" in text,
        ]
        rc2, out2 = py(HANDOFF, str(host), "--check")
        if rc2 != 0:
            return False, "--check 失败 " + out2[:120]
        before = text
        py(HANDOFF, str(host))
        if read(host / "HANDOFF.md") != before:
            return False, "重复写入不幂等"
        ok = all(checks)
        return ok, ("PASS / 保留手写 + 双标记 + 幂等 + --check") if ok else \
            "FAIL / checks=%s" % checks


# --------------------------------------------------------------------------
# fixture 与隔离用例
# --------------------------------------------------------------------------
def c_fixture8():
    with tempfile.TemporaryDirectory(prefix="twf8-") as tmp:
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1)
        rc, out = v8(wf, strict=True)
        return expect_ok(rc, out, strict=True)


def c_fixtureR():
    with tempfile.TemporaryDirectory(prefix="twfr-") as tmp:
        feat = fresh_rec(tmp)
        wf = write_rec(feat, baseR_statuses(1), 1)
        rc, out = vr(wf, strict=True)
        return expect_ok(rc, out, strict=True)


def c_default_path():
    with tempfile.TemporaryDirectory(prefix="twdef-") as tmp:
        root = Path(tmp)
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1)
        # 显式
        rc1, out1 = py(VAL8, "--workflows-dir", str(wf), "--strict")
        # 默认（CWD = 宿主项目根）
        rc2, out2 = py(VAL8, "--strict", cwd=str(root))
        # 相对路径
        rc3, out3 = py(VAL8, "--workflows-dir", ".claude/workflows", "--strict", cwd=str(root))
        ok = rc1 == rc2 == rc3 == 0 and all(not has_issue(o) for o in (out1, out2, out3))
        return ok, ("PASS / 默认 CWD 路径 == 显式路径 == 相对路径") if ok else \
            "FAIL / rc=%s,%s,%s | %s" % (rc1, rc2, rc3, (out1 + out2 + out3)[:150])


def c_missing_dir_error():
    with tempfile.TemporaryDirectory(prefix="twempty-") as tmp:
        rc, out = py(VAL8, cwd=tmp)
        return expect_fail(rc, out, "工作流目录不存在")


def c_isolation():
    with tempfile.TemporaryDirectory(prefix="twiso-") as tmp:
        root = Path(tmp)
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1)
        # 旁挂一份故意损坏的录制状态树，8 阶段校验器必须完全忽略
        rwf = root / ".claude" / "record-workflows"
        bad = rwf / "broken"
        bad.mkdir(parents=True)
        (rwf / ".current").write_text("broken\n", encoding="utf-8")
        (bad / "record_state.json").write_text('{"broken": true}', encoding="utf-8")
        rc, out = py(VAL8, "--strict", cwd=str(root))
        return expect_ok(rc, out, strict=True)


def c_dashboard_missing():
    with tempfile.TemporaryDirectory(prefix="twdash-") as tmp:
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1, dashboard=False)
        rc, out = v8(wf, strict=False)
        return expect_fail(rc, out, "dashboard.md 不存在")


# --------------------------------------------------------------------------
# 反向破坏用例（验证校验器/生成器「真的会拦」）
# --------------------------------------------------------------------------
def negative8(mutator, keyword=None, strict=True):
    with tempfile.TemporaryDirectory(prefix="twneg8-") as tmp:
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1)
        state = json.loads(read(feat / "state.json"))
        mutator(state, feat)
        (feat / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
        rc, out = v8(wf, strict=strict)
        return expect_fail(rc, out, keyword)


def c_neg_stage_drift():
    def m(s, f):
        s["current_stage"] = 3
    return negative8(m, "不自洽")


def c_neg_string_hi():
    def m(s, f):
        s["stages"]["1_business"]["human_intervention"] = "true"
    return negative8(m, "字符串")


def c_neg_skipped_no_bypass():
    def m(s, f):
        e = s["stages"]["2_data"]
        e["status"] = "skipped"
        e["human_intervention"] = False
    return negative8(m, "bypasses")


def c_neg_short_reason():
    def m(s, f):
        e = s["stages"]["2_data"]
        e["status"] = "skipped"
        e["human_intervention"] = False
        s["bypasses"] = [{"stage": 2, "reason": "no", "timestamp": NOW}]
    return negative8(m, "5 字符")


def c_neg_verify_failed():
    with tempfile.TemporaryDirectory(prefix="twfail-") as tmp:
        feat = fresh_8(tmp)
        st = ["done"] * 4 + ["failed"] + ["pending"] * 3
        wf = write_8(feat, st, 4)
        rc_ok, out_ok = v8(wf, strict=True)
        good = (rc_ok == 0), "current_stage=4 应 PASS | %s" % out_ok.replace("\n", " / ")[:120]
        state = json.loads(read(feat / "state.json"))
        state["current_stage"] = 5
        (feat / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
        rc_bad, out_bad = v8(wf, strict=True)
        bad = expect_fail(rc_bad, out_bad, "不自洽")
        ok = good[0] and bad[0]
        return ok, ("PASS / failed→停在 4 合法，停在 5 被拦") if ok else \
            "FAIL / good=%s bad=%s" % (good[1], bad[1])


def c_neg_record_drift_and_rework():
    results = []
    with tempfile.TemporaryDirectory(prefix="twnegr-") as tmp:
        feat = fresh_rec(tmp)
        wf = write_rec(feat, baseR_statuses(1), 1)
        state = json.loads(read(feat / "record_state.json"))
        # 1) 自洽漂移 → ERROR
        state["current_stage"] = 3
        (feat / "record_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
        rc, out = vr(wf, strict=False)
        results.append(expect_fail(rc, out, "不自洽"))
        # 2) rework_round=3 → WARNING（非 strict 放行，strict 拦下）
        state["current_stage"] = 1
        state["stages"]["3_case"]["rework_round"] = 3
        (feat / "record_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
        rc2, out2 = vr(wf, strict=False)
        rc3, out3 = vr(wf, strict=True)
        ok2 = rc2 == 0 and clean(out2)[1] > 0 and rc3 == 1
        results.append((ok2, "PASS / rework_round=3 非 strict 放行、strict 升级失败") if ok2
                       else "FAIL / rc=%d,%d %s" % (rc2, rc3, (out2 + out3)[:120]))
    ok = all(r[0] for r in results)
    return ok, ("PASS / 录制漂移 ERROR + rework WARNING 分级") if ok else \
        "FAIL / " + " ; ".join(r[1] for r in results)


def c_neg_dispatcher_drift():
    target = SKILLS / "business-context" / "SKILL.md"
    original = read(target)
    try:
        target.write_text(original + "\nDRIFT\n", encoding="utf-8")
        rc, out = py(GEN8, "--check")
        return expect_fail(rc, out, "漂移")
    finally:
        target.write_text(original, encoding="utf-8")


def c_neg_undeclared_pack_file():
    stray = PACKS / "playwright-python" / "references" / "__undeclared_acceptance.md"
    try:
        stray.write_text("# stray\n", encoding="utf-8")
        rc, out = py(VAL8, "--check-pack", "--strict")
        return expect_fail(rc, out, "未声明")
    finally:
        if stray.exists():
            stray.unlink()


def c_neg_rogue_record_dispatcher():
    rogue = SKILLS / "__rogue_acceptance"
    try:
        rogue.mkdir(exist_ok=True)
        (rogue / "SKILL.md").write_text(
            "---\nname: __rogue_acceptance\ndescription: x\n---\n\n[TW 录制阶段9] 逃逸\n",
            encoding="utf-8")
        rc, out = py(GENR, "--check")
        return expect_fail(rc, out, "覆盖护栏")
    finally:
        shutil.rmtree(rogue, ignore_errors=True)


# --------------------------------------------------------------------------
# 端到端状态流转模拟（代码层能覆盖的 Phase 9 部分）
# --------------------------------------------------------------------------
def c_e2e_8_stages():
    failures = []
    with tempfile.TemporaryDirectory(prefix="twe2e8-") as tmp:
        feat = fresh_8(tmp)
        for cur in range(1, 10):
            statuses = base8_statuses(9) if cur == 9 else base8_statuses(cur)
            wf = write_8(feat, statuses, cur)
            rc, out = v8(wf, strict=True)
            if rc != 0 or has_issue(out):
                failures.append("cur=%d rc=%d %s" % (cur, rc, out.replace("\n", " / ")[:100]))
    return (not failures), ("PASS / 8 阶段 1→9 逐步推进 9/9 快照全绿（含产出物与看板对账）") \
        if not failures else "FAIL / " + "; ".join(failures[:3])


def c_e2e_bypass():
    with tempfile.TemporaryDirectory(prefix="twbyp-") as tmp:
        feat = fresh_8(tmp)
        st = ["done", "skipped", "in_progress"] + ["pending"] * 5
        bypass = [{"stage": 2, "reason": "冒烟跳过阶段2", "timestamp": NOW}]
        wf = write_8(feat, st, 3, bypasses=bypass)
        rc, out = v8(wf, strict=True)
        state = json.loads(read(feat / "state.json"))
        ok = rc == 0 and state["stages"]["2_data"]["status"] == "skipped" \
             and state["current_stage"] == 3 and len(state["bypasses"]) == 1
        return ok, ("PASS / bypass 3 只跳过阶段 2（target_stage-1）并留 reason") if ok else \
            "FAIL / rc=%d %s" % (rc, out.replace("\n", " / ")[:150])


def c_e2e_tristate():
    """§4.3 审查门三值模型：批准 / edit / exit / full-auto 四种回写均合法。"""
    combos = [
        ("批准", False, False, False),
        ("edit/skip/accept", True, False, False),
        ("exit", None, True, False),
        ("full-auto", False, True, True),
    ]
    bad = []
    with tempfile.TemporaryDirectory(prefix="twtri-") as tmp:
        feat = fresh_8(tmp)
        for label, hi, review, is_full in combos:
            entry = {"status": "in_progress", "human_intervention": hi,
                     "intervention_note": ("人工编辑用例" if hi is True else None),
                     "review_needed": review}
            wf = write_8(feat, base8_statuses(1), 1,
                         mode="full-auto" if is_full else "manual",
                         stage_extra={"1_business": entry})
            rc, out = v8(wf, strict=True)
            if rc != 0 or has_issue(out):
                bad.append("%s: %s" % (label, out.replace("\n", " / ")[:100]))
    return (not bad), ("PASS / 三值模型 4 种回写全部合法") if not bad else "FAIL / " + "; ".join(bad[:2])


def c_e2e_record_stages():
    failures = []
    with tempfile.TemporaryDirectory(prefix="twe2er-") as tmp:
        feat = fresh_rec(tmp)
        for cur in range(1, 7):
            statuses = baseR_statuses(6) if cur == 6 else baseR_statuses(cur)
            wf = write_rec(feat, statuses, cur)
            rc, out = vr(wf, strict=True)
            if rc != 0 or has_issue(out):
                failures.append("cur=%d rc=%d %s" % (cur, rc, out.replace("\n", " / ")[:100]))
    return (not failures), ("PASS / 录制 1→6 逐步推进 6/6 快照全绿") if not failures \
        else "FAIL / " + "; ".join(failures[:3])


def c_e2e_record_rollback():
    with tempfile.TemporaryDirectory(prefix="twroll-") as tmp:
        feat = fresh_rec(tmp)
        st = ["done", "done", "done", "failed", "pending"]
        wf = write_rec(feat, st, 4,
                       stage_extra={"3_case": {"rework_round": 1}})
        rc, out = vr(wf, strict=True)
        ok = rc == 0 and not has_issue(out)
        return ok, ("PASS / 4_run failed 停在 4、rework_round=1 合法") if ok else \
            "FAIL / rc=%d %s" % (rc, out.replace("\n", " / ")[:150])


# --------------------------------------------------------------------------
# §13 条款守护：把原先「需人工评审」的纪律变成可执行断言
# --------------------------------------------------------------------------
def _stage_files():
    return sorted(PACKS.glob("*/stages/*.md"))


def _rec_stage_files():
    return sorted(PACKS.glob("*/workflows/record-driven/stages/*.md"))


def c_clause_gate_modes():
    """§4.3 四套 mode 失败分支：表里 6 行、录制 4/5 与不回拨语义齐全。"""
    t = read(ROOT / "tw/protocols/gate-protocol.md")
    needed = ["manual / semi-auto", "full-auto", "录制 4，7 轮用尽",
              "录制 5，结论「需修」", "录制 5，审核链路本身失败",
              "不回拨", "rework_round", "停止推进并报告"]
    miss = [x for x in needed if x not in t]
    rows = sum(1 for line in t.splitlines() if line.startswith("| 录制 ") or
               line.startswith("| 8 阶段 5"))
    ok = not miss and rows >= 6
    return ok, ("PASS / §4.3 四套 mode 6 行分支齐全") if ok else \
        "FAIL / 缺 %s，表行 %d" % (miss, rows)


def c_clause_pause_types():
    """§4.4 两类暂停门不可混用、semi-auto 在 1e/3a 会停、[skip] 不写 bypasses。"""
    t = read(ROOT / "tw/protocols/gate-protocol.md")
    needed = ["两类暂停门不可混用", "semi-auto 会停", "不写 `bypasses`",
              "`[skip]` 跳的是审查门", "统一展示", "full-auto"]
    miss = [x for x in needed if x not in t]
    return (not miss), ("PASS / §4.4 两类暂停门与 [skip] 语义齐全") if not miss \
        else "FAIL / 缺 %s" % miss


def c_clause_three_gates_order():
    """§6.2 三道门顺序，且 4 个域包 stage1 都按同顺序出现（§13 门禁项）。"""
    names = ["前置确认门", "实质缺口门", "用例审核门"]
    reg = read(ROOT / "tw/protocols/stage-registry.md")
    idx = [reg.find(n) for n in names]
    reg_ok = all(i >= 0 for i in idx) and idx[0] < idx[1] < idx[2]
    bad = []
    files = sorted(PACKS.glob("*/stages/stage1_*.md"))
    for p in files:
        t = read(p)
        j = [t.find(n) for n in names]
        if not (all(k >= 0 for k in j) and j[0] < j[1] < j[2]):
            bad.append(p.parent.parent.name)
    ok = reg_ok and len(files) == 4 and not bad
    return ok, ("PASS / 三道门顺序：协议 + 4 个域包 stage1 一致") if ok else \
        "FAIL / reg=%s files=%d bad=%s" % (reg_ok, len(files), bad)


def c_clause_stage4_discipline():
    """§6.3 4-pre 分级采集 / 4a-0 DOM 冲突对照 / 定位符来源。"""
    reg = read(ROOT / "tw/protocols/stage-registry.md")
    needed = ["4-pre DOM 分级采集", "4a-0 DOM 冲突对照", "DOM 冲突修订表",
              "每个定位符标来源", "不做笛卡尔积"]
    miss = [x for x in needed if x not in reg]
    files = sorted(PACKS.glob("*/stages/stage4_*.md"))
    bad = [p.parent.parent.name for p in files if "§6.3" not in read(p)]
    ok = not miss and len(files) == 4 and not bad
    return ok, ("PASS / 阶段 4 采集与冲突对照纪律 + 4 域包引用 §6.3") if ok else \
        "FAIL / 协议缺 %s 域包缺引用 %s" % (miss, bad)


def c_clause_stage5_6_discipline():
    """§6.4 探查-修复 ≤7 轮、§6.5 flaky quarantine 四步，域包按章节引用。"""
    reg = read(ROOT / "tw/protocols/stage-registry.md")
    needed = ["探查-修复循环（≤7 轮）", "禁止放宽断言迁就实现",
              "flaky quarantine 四步", "禁止长期挂着"]
    miss = [x for x in needed if x not in reg]
    bad5 = [p.parent.parent.name for p in sorted(PACKS.glob("*/stages/stage5_*.md"))
            if "§6.4" not in read(p)]
    bad6 = [p.parent.parent.name for p in sorted(PACKS.glob("*/stages/stage6_*.md"))
            if "§6.5" not in read(p)]
    ok = not miss and not bad5 and not bad6
    return ok, ("PASS / 阶段 5/6 纪律 + 域包引用 §6.4/§6.5") if ok else \
        "FAIL / 协议缺 %s 阶段5 %s 阶段6 %s" % (miss, bad5, bad6)


def c_clause_evidence_refs():
    """§13 证据纪律：协议被对应阶段引用、磁盘重读、独立子代理与逐条对账。"""
    def all_have(pattern, token):
        fs = sorted(PACKS.glob(pattern))
        return len(fs) > 0 and all(token in read(p) for p in fs), len(fs)

    checks = []
    ok1, n1 = all_have("*/stages/stage1_*.md", "case-expansion-protocol.md")
    checks.append(("阶段1→case-expansion", ok1))
    ok2, n2 = all_have("*/stages/stage3_*.md", "assertion-protocol.md")
    checks.append(("阶段3→assertion", ok2))
    ok3, n3 = all_have("*/stages/stage4_*.md", "dump-artifact-protocol.md")
    checks.append(("阶段4→dump-artifact", ok3))
    ok4, n4 = all_have("*/stages/stage5_*.md", "从磁盘重读 stage3/stage4")
    checks.append(("阶段5磁盘重读", ok4))
    rec2 = list(_rec_stage_files())
    r2 = next((p for p in rec2 if p.name == "stage2_casegen.md"), None)
    checks.append(("录制2→case-expansion", bool(r2) and "case-expansion-protocol.md" in read(r2)))
    r5 = next((p for p in rec2 if p.name == "stage5_review.md"), None)
    checks.append(("录制5独立子代理+逐条对账",
                   bool(r5) and "独立审核子代理" in read(r5) and "逐条对账" in read(r5)))
    bad = [name for name, ok in checks if not ok]
    return (not bad), ("PASS / 7 条证据纪律引用关系成立（%d 份阶段文件抽检）" % (n1 + n2 + n3 + n4)) \
        if not bad else "FAIL / %s" % bad


def c_clause_full_safety():
    """§7.3 --full 3 类必须停 + 2 类确定性处理 + 停止格式，协议与 skill 双份。"""
    g = read(ROOT / "tw/workflows/record-driven/protocols/gate-protocol.md")
    s = read(ROOT / "skills/record-auto/SKILL.md")
    need_g = ["3 类必须停", "evidence.degraded", "环境问题 / 真实 bug",
              "校验器报 ERROR", "确定性处理", "停止格式", "非 strict"]
    need_s = ["3 类必须停", "停止格式", "终止推进并报告", "rework_round > 2"]
    miss_g = [x for x in need_g if x not in g]
    miss_s = [x for x in need_s if x not in s]
    rows = all("| %d |" % i in g for i in range(1, 6))
    ok = not miss_g and not miss_s and rows
    return ok, ("PASS / --full 安全阀 5 行表 + 停止格式，协议与 skill 一致") if ok else \
        "FAIL / 协议缺 %s skill 缺 %s 表=%s" % (miss_g, miss_s, rows)


def c_clause_pack_no_state_write():
    """§14 风险：域包阶段指令不写状态文件（校验器不检查正文，此用例兜底）。

    域包只引用协议章节号，正文里连状态文件名都不该出现；出现即视为潜在双写者。
    """
    # 词边界：storage_state.json（浏览器认证态）不是工作流状态文件，
    # 其 "state.json" 前是 '_'，会被 (?<![\w]) 排除。
    pattern = re.compile(r"(?<![\w])(?:record_state\.json|state\.json|dashboard\.md|\.current)\b")
    bad = []
    for p in _stage_files() + _rec_stage_files():
        hits = sorted(set(pattern.findall(read(p))))
        if hits:
            bad.append("%s: %s" % (p.relative_to(ROOT), hits))
    return (not bad), ("PASS / %d 份阶段指令均未直接写状态文件" %
                       (len(_stage_files()) + len(_rec_stage_files()))) if not bad \
        else "FAIL / %s" % bad[:4]


def c_clause_section_refs():
    """§14 协议唯一真相源：所有阶段指令都指向具体章节号，不整段复述。"""
    files = _stage_files() + _rec_stage_files()
    bad = [p.relative_to(ROOT) for p in files if "§" not in read(p)]
    return (not bad), ("PASS / %d 份阶段指令全部引用具体章节号" % len(files)) if not bad \
        else "FAIL / %s" % [str(x) for x in bad[:4]]


def c_release_version_contract():
    """§13 发布一致性（git tag 的静态代理）：版本合法、marketplace 名字一致、
    域包 min_core_version 不高于内核版本。真正的 git tag 需在发布时人工执行。"""
    def tup(s):
        parts = (s.strip().split(".") + ["0", "0", "0"])[:3]
        try:
            return tuple(int(x) for x in parts)
        except ValueError:
            return (-1, -1, -1)
    p = json.loads(read(ROOT / ".claude-plugin/plugin.json"))
    m = json.loads(read(ROOT / ".claude-plugin/marketplace.json"))
    v = p.get("version", "")
    checks = [
        ("semver", re.fullmatch(r"\d+\.\d+\.\d+", v) is not None),
        ("marketplace 名字一致", m.get("plugins", [{}])[0].get("name") == p.get("name")),
        ("license 存在", bool(p.get("license"))),
    ]
    too_new = []
    for pack in sorted(PACKS.glob("*/pack.yaml")):
        mm = re.search(r"^min_core_version:\s*([0-9.]+)", read(pack), re.M)
        if mm and tup(mm.group(1)) > tup(v):
            too_new.append(pack.parent.name)
    checks.append(("域包 min_core_version 兼容", not too_new))
    bad = [name for name, ok in checks if not ok]
    return (not bad), ("PASS / plugin v%s 发布契约（git tag 需发布时人工执行）" % v) if not bad \
        else "FAIL / %s 域包超版本 %s" % (bad, too_new)


# --------------------------------------------------------------------------
# 官方 CLI 冒烟（--official）
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# 用例注册
# --------------------------------------------------------------------------
STATIC = [
    ("Phase 0", "manifest JSON 与 license", c_manifests),
    ("Phase 2", "31 个 SKILL.md frontmatter 与目录名一致", c_skill_frontmatter),
    ("Phase 8", "README 命令数/域包表与实际一致", c_readme_consistency),
    ("Phase 1", "§15.1 关键文件清单齐全", c_required_files),
    ("Phase 1", "JSON 模板与反馈注册表可解析", c_json_assets),
    ("Phase 2", "8 阶段分发器生成器 --check", c_gen8_check),
    ("Phase 5", "录制分发器生成器 --check", c_genr_check),
    ("Phase 7", "--check-pack --strict（4 域包 C1/C2/C5/C2R）", c_check_pack_strict),
    ("Phase 6", "--check-pack 单包 playwright-python", c_check_pack_single),
    ("Phase 4", "--check-profile-contract", c_profile_contract),
    ("Phase 4", "--check-dump-contract", c_dump_contract),
    ("Phase 5", "--check-workflow（录制定义 W3R/W8）", c_record_workflow_def),
    ("§13", "8+5 分发器零耦合静态扫描", c_zero_coupling),
    ("§13", "能力键门控（无硬编码 pack 白名单）", c_capability_gating),
    ("§13", "两个校验器互不 import", c_no_cross_import),
    ("§13", "5 个脚本 UTF-8 重配置 + __file__ 路径", c_tool_hygiene),
    ("§13", "yaml.safe_load 有 dict 守卫", c_yaml_guard),
    ("§13", ".gitignore 覆盖运行时产物", c_gitignore),
    ("§13", "阶段指令六段结构 + Exit Gate 收束", c_six_sections),
    ("§13", "4 域包/坑点库；录制子树仅 playwright-python", c_packs_and_subtree),
    ("Phase 3", "gen_handoff 保留手写/双标记/幂等/--check", c_handoff),
]

FIXTURE = [
    ("Phase 4", "8 阶段 fixture 0 ERROR / 0 WARNING", c_fixture8),
    ("Phase 5", "录制 fixture 0 ERROR", c_fixtureR),
    ("Phase 5", "默认 CWD 路径 == 显式 == 相对路径", c_default_path),
    ("§10.3", "无 CWD 工作流目录 → ERROR（禁止回落）", c_missing_dir_error),
    ("§13", "两套工作流隔离（忽略损坏的录制状态树）", c_isolation),
    ("Phase 4", "dashboard 缺失 → ERROR", c_dashboard_missing),
]

NEGATIVE = [
    ("反向", "current_stage 自洽漂移 → 拦截", c_neg_stage_drift),
    ("反向", "human_intervention 字符串 → 拦截", c_neg_string_hi),
    ("反向", "skipped 无 bypass → 拦截", c_neg_skipped_no_bypass),
    ("反向", "bypass.reason < 5 字符 → 拦截", c_neg_short_reason),
    ("反向", "5_verify=failed 停 4 合法 / 停 5 拦截", c_neg_verify_failed),
    ("反向", "录制漂移 ERROR + rework WARNING 分级", c_neg_record_drift_and_rework),
    ("反向", "分发器被篡改 → 生成器 --check 拦截", c_neg_dispatcher_drift),
    ("反向", "域包未声明 md → --check-pack --strict 拦截", c_neg_undeclared_pack_file),
    ("反向", "手写录制分发器逃逸 → 覆盖护栏拦截", c_neg_rogue_record_dispatcher),
]

E2E = [
    ("Phase 9*", "8 阶段 1→9 全流转 9/9 快照全绿", c_e2e_8_stages),
    ("Phase 9*", "bypass 3 只跳过阶段 2（target_stage-1）", c_e2e_bypass),
    ("Phase 9*", "审查门三值模型 4 种回写均合法", c_e2e_tristate),
    ("Phase 9*", "录制 1→6 全流转 6/6 快照全绿", c_e2e_record_stages),
    ("Phase 9*", "录制 4_run failed 回拨停在 4 合法", c_e2e_record_rollback),
]

CLAUSES = [
    ("§13", "§4.3 四套 mode 失败分支 6 行齐全", c_clause_gate_modes),
    ("§13", "§4.4 两类暂停门与 [skip] 语义", c_clause_pause_types),
    ("§13", "阶段 1 三道门顺序（协议 + 4 域包）", c_clause_three_gates_order),
    ("§13", "阶段 4 分级采集 / DOM 冲突对照", c_clause_stage4_discipline),
    ("§13", "阶段 5/6 探查修复与 flaky 四步", c_clause_stage5_6_discipline),
    ("§13", "证据纪律 7 条引用关系", c_clause_evidence_refs),
    ("§13", "--full 3 类必停 + 2 类确定性处理", c_clause_full_safety),
    ("§14", "域包正文不写状态文件（人工评审兜底）", c_clause_pack_no_state_write),
    ("§14", "域包只引用协议章节号", c_clause_section_refs),
    ("§13", "发布版本一致性（git tag 静态代理）", c_release_version_contract),
]

OFFICIAL = [
    ("官方", "claude plugin validate 识别 31 skills", c_official_validate),
    ("官方", "validate --profile directory 通过", c_official_directory_profile),
    ("官方", "隔离 marketplace add + install（不污染用户配置）", c_official_isolated_install),
    ("官方", "真实 -p 会话可见 31 个命令", c_official_session_visibility),
    ("官方", "真实会话执行 /tw:new-feature 并落盘校验", c_official_session_new_feature),
]

GROUPS = [
    ("静态契约", STATIC),
    ("§13/§14 条款守护", CLAUSES),
    ("状态机 fixture 与隔离", FIXTURE),
    ("反向破坏（校验器真的会拦）", NEGATIVE),
    ("端到端状态流转模拟", E2E),
    ("Claude Code 官方 CLI 冒烟", OFFICIAL),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="只跑静态契约组")
    ap.add_argument("--official", action="store_true", help="追加官方 CLI 冒烟组")
    args = ap.parse_args()

    print("TW 工作流框架 · 可复现验收套件")
    print("仓库: %s" % ROOT)
    print("模式: %s" % ("quick" if args.quick else
                       ("full+official" if args.official else "full")))
    print("=" * 78)

    groups = [GROUPS[0]] if args.quick else \
             GROUPS if args.official else GROUPS[:-1]

    passed = failed = skipped = 0
    failures = []
    for gname, cases in groups:
        print("\n[%s]  (%d 项)" % (gname, len(cases)))
        for phase, name, fn in cases:
            try:
                result = fn()
                if isinstance(result, tuple):
                    ok, detail = result
                else:
                    ok, detail = bool(result), ""
            except Exception as exc:
                ok, detail = False, "用例异常 %s: %s" % (type(exc).__name__, exc)
            if ok is None:
                skipped += 1
                tag = "SKIP"
            elif ok:
                passed += 1
                tag = "PASS"
            else:
                failed += 1
                tag = "FAIL"
                failures.append("[%s] %s → %s" % (gname, name, detail))
            print("  %-4s  %-9s %-52s %s" % (tag, phase, name, detail[:105]))

    print("\n" + "=" * 78)
    print("汇总: %d PASS / %d FAIL / %d SKIP" % (passed, failed, skipped))
    if failures:
        print("\n失败明细:")
        for f in failures:
            print("  - " + f)
    print("FINAL: %s" % ("ALL PASS" if failed == 0 else "HAS FAILURES"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
