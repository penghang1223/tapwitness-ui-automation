"""静态契约与协议条款验收。"""

import json
import re
import tempfile
from pathlib import Path

from .common import (
    GEN8, GENR, HANDOFF, PACKS, REC_TOOLS, ROOT, SKILLS, TOOLS, VAL8, VALR,
    expect_ok, py, read, skill_dirs, skill_names,
)


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
        ".gitignore", "README.md",
        "docs/install.md", "docs/使用教程.md", "docs/架构设计方案.md",
        ".github/ISSUE_TEMPLATE/tw-feedback.yml",
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
        "tw/tools/README.md", "tw/tools/validate_artifacts.py",
        "tw/workflows/record-driven/README.md",
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
    # 动态发现所有工具脚本：新增工具自动纳入卫生检查。
    scripts = sorted(TOOLS.glob("*.py")) + sorted(REC_TOOLS.glob("*.py"))
    need_root = [p for p in scripts if p.name != "gen_handoff.py"]
    bad = []
    for p in scripts:
        text = read(p)
        if "sys.stdout.reconfigure" not in text:
            bad.append(p.name + ": 缺 UTF-8 重配置")
        if p in need_root and "Path(__file__)" not in text:
            bad.append(p.name + ": 路径未由 __file__ 推导")
    return (not bad), ("PASS / %d 个脚本 UTF-8 + %d 个 __file__ 路径" %
                       (len(scripts), len(need_root))) if not bad \
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
    auto = read(SKILLS / "auto" / "SKILL.md")
    resume = read(SKILLS / "continue" / "SKILL.md")
    rec = read(SKILLS / "record-auto" / "SKILL.md")
    for label, condition in (
        ("阶段号 N", "记录本轮进入的阶段号 N" in auto and "不得以返回后" in auto),
        ("已完成阶段退出", "human_intervention 应保持 false" in auto),
        ("按模式恢复", "full-auto 恢复时保留" in resume and "semi-auto 恢复时" in resume),
        ("录制阶段号", "记录阶段号 N" in rec),
    ):
        if not condition:
            miss.append(label)
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
