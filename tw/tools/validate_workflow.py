#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""8 阶段工作流校验器：状态机校验 + 域包自检 + profile 契约 + dump 契约。

模式（互斥）：
  默认             校验 .claude/workflows 下的状态机；省略 --workflows-dir 时取 CWD/.claude/workflows；
                   该目录不存在 → ERROR（禁止回落到脚本所在目录）。
  --check-pack [D] 域包 C1/C2/C5/C2R 自检；省略 D 时扫描 tw/packs/*。
  --check-profile-contract   检查 <section>.<field> 引用是否都在 profile 模板中定义。
  --check-dump-contract      dump 产物协议契约。

退出码：有 ERROR，或无 ERROR 但 --strict 且有 WARNING → 1；否则 0。
"""
import sys
import re
import json
import argparse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
PACKS = ROOT / "tw" / "packs"
TEMPLATES = ROOT / "tw" / "templates"
PROTOCOLS = ROOT / "tw" / "protocols"

STAGE_KEYS = ["1_business", "2_data", "3_assertion", "4_case",
              "5_verify", "6_e2e", "7_report", "8_kb_feedback"]
COMPLETE = 9
STATUSES = {"pending", "in_progress", "done", "skipped", "failed"}
STAGE_ARTIFACTS = {
    "1_business": ["stage1_business.md", "stage1_cases.md", "stage1_cases.json"],
    "2_data": ["stage2_data.md"],
    "3_assertion": ["stage3_assertions.md", "stage3_assertions.json"],
    "4_case": ["stage4_plan.md", "stage4_files.md"],
    "5_verify": ["stage5_verify.log"],
    "6_e2e": ["stage6_e2e.md"],
    "7_report": ["stage7_report.md"],
    "8_kb_feedback": ["stage8_kb_feedback.md"],
}
PACK_SCAN_DIRS = {"stages", "references", "tools"}
PACK_EXEMPT_DIRS = {"workflows"}
DASH_RE = re.compile(r"\*\*\s*(\d+)\s*/\s*(\d+)\s*完成\*\*\s*\|\s*\*\*\s*(\d+)\s*进行中\*\*\s*\|\s*\*\*\s*(\d+)\s*未启动\*\*")
PROFILE_SECTIONS = ("paths", "run", "data_layer", "kb", "dashboard", "feedback_channel", "subsystems")
FIELD_RE = re.compile(r"(?<![\w.])(" + "|".join(PROFILE_SECTIONS) + r")\.([A-Za-z_][A-Za-z0-9_]*)\b")
BARE_DUMP_RE = re.compile(r"\b(?:page_dump[^.\s]*\.(?:html|png|xml)|page_source[^.\s]*\.xml)\b", re.I)
SECTION_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


def load_yaml_dict(path, errors, label):
    """安全加载 YAML；空文件/列表/标量 → 干净 FAIL，绝不抛 AttributeError。"""
    try:
        import yaml
    except ImportError:
        errors.append("ERROR %s：缺少 PyYAML，无法解析 %s" % (label, path))
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append("ERROR %s：无法读取 %s（%s）" % (label, path, exc))
        return None
    if not text.strip():
        errors.append("ERROR %s：%s 为空文件" % (label, path))
        return None
    try:
        data = yaml.safe_load(text)
    except Exception as exc:
        errors.append("ERROR %s：%s YAML 非法（%s）" % (label, path, exc))
        return None
    if not isinstance(data, dict):
        errors.append("ERROR %s：%s 顶层不是 mapping（实际 %s）" % (label, path, type(data).__name__))
        return None
    return data


def check_state_file(path, errors, warnings):
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append("ERROR %s：state.json 无法解析（%s）" % (path.parent.name, exc))
        return None
    if not isinstance(state, dict):
        errors.append("ERROR %s：state.json 顶层不是对象" % path.parent.name)
        return None
    feature = path.parent.name
    for key in ("feature", "created", "mode", "current_stage", "stages", "bypasses"):
        if key not in state:
            errors.append("ERROR %s：state.json 缺字段 %s" % (feature, key))
    if state.get("feature") != feature:
        errors.append("ERROR %s：state.feature=%r 与目录名不一致" % (feature, state.get("feature")))
    mode = state.get("mode")
    if not isinstance(mode, str) or mode not in {"manual", "semi-auto", "full-auto"}:
        errors.append("ERROR %s：mode 非法 %r" % (feature, mode))

    stages = state.get("stages")
    if not isinstance(stages, dict):
        errors.append("ERROR %s：stages 不是对象" % feature)
        return None
    statuses = {}
    for key in STAGE_KEYS:
        if key not in stages:
            errors.append("ERROR %s：stages 缺键 %s" % (feature, key))
            continue
        entry = stages[key]
        if not isinstance(entry, dict):
            errors.append("ERROR %s：%s 不是对象" % (feature, key))
            continue
        status = entry.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append("ERROR %s：%s status 非法 %r" % (feature, key, status))
            continue
        statuses[key] = status
        hi = entry.get("human_intervention", None)
        if isinstance(hi, str):
            errors.append("ERROR %s：%s human_intervention 是字符串（必须布尔三态）" % (feature, key))
        elif hi is not None and not isinstance(hi, bool):
            errors.append("ERROR %s：%s human_intervention 必须为布尔或 null" % (feature, key))
        if status in {"done", "skipped"} and hi is None:
            errors.append("ERROR %s：%s 为 %s 但 human_intervention 为 null" % (feature, key, status))
        if status == "pending" and hi is not None:
            warnings.append("WARNING %s：%s 为 pending 但 human_intervention 非 null" % (feature, key))
        if hi is True and not entry.get("intervention_note"):
            errors.append("ERROR %s：%s human_intervention=true 但缺 intervention_note" % (feature, key))
        rv = "review_needed"
        if rv in entry and not isinstance(entry[rv], bool):
            errors.append("ERROR %s：%s review_needed 必须是布尔" % (feature, key))
        if status == "done":
            for art in STAGE_ARTIFACTS[key]:
                if not (path.parent / art).is_file():
                    warnings.append("WARNING %s：done 阶段 %s 缺产出 %s" % (feature, key, art))
        if status == "failed" and key != "5_verify":
            warnings.append("WARNING %s：failed 出现在 %s（只允许 5_verify）" % (feature, key))

    cur = state.get("current_stage")
    if not isinstance(cur, int) or isinstance(cur, bool) or not (1 <= cur <= COMPLETE):
        errors.append("ERROR %s：current_stage 非法 %r" % (feature, cur))
    elif len(statuses) == len(STAGE_KEYS):
        expected = next((i for i, key in enumerate(STAGE_KEYS, start=1)
                         if statuses[key] not in {"done", "skipped"}), COMPLETE)
        if (mode in ("manual", "semi-auto") and statuses["5_verify"] == "failed"
                and expected >= 4):
            expected = 4
        if cur != expected:
            errors.append("ERROR %s：current_stage=%s 与状态不自洽（应为 %s）" % (feature, cur, expected))

    by = state.get("bypasses")
    if not isinstance(by, list):
        errors.append("ERROR %s：bypasses 不是数组" % feature)
        by = []
    by_stages = set()
    for item in by:
        if not isinstance(item, dict):
            errors.append("ERROR %s：bypasses 元素不是对象" % feature)
            continue
        stg, reason, ts = item.get("stage"), item.get("reason"), item.get("timestamp")
        if type(stg) is not int or not (1 <= stg < COMPLETE):
            errors.append("ERROR %s：bypass.stage 非法 %r" % (feature, stg))
        else:
            by_stages.add(stg)
        if not isinstance(reason, str) or len(reason) < 5:
            errors.append("ERROR %s：bypass.reason 少于 5 字符" % feature)
        if not isinstance(ts, str) or not ts:
            errors.append("ERROR %s：bypass.timestamp 缺失" % feature)
    if len(statuses) != len(STAGE_KEYS):
        return None
    skipped = {i for i, key in enumerate(STAGE_KEYS, start=1) if statuses[key] == "skipped"}
    for stg in sorted(skipped - by_stages):
        errors.append("ERROR %s：阶段 %s 为 skipped 但无 bypasses 记录" % (feature, stg))
    for stg in sorted(by_stages - skipped):
        errors.append("ERROR %s：bypasses 记了阶段 %s 但状态非 skipped" % (feature, stg))
    return statuses


def dashboard_state(statuses):
    if all(v in {"done", "skipped"} for v in statuses.values()):
        return "done"
    if all(v == "pending" for v in statuses.values()):
        return "pending"
    return "active"


def check_workflows_dir(wf_dir, errors, warnings):
    if not wf_dir.exists() or not wf_dir.is_dir():
        errors.append("ERROR：工作流目录不存在：%s（请传 --workflows-dir <项目>/.claude/workflows）" % wf_dir)
        return
    features = {}
    for child in sorted(wf_dir.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name == "_template":
            continue
        sf = child / "state.json"
        if not sf.exists():
            continue
        features[child.name] = check_state_file(sf, errors, warnings)

    current = wf_dir / ".current"
    if not current.exists():
        errors.append("ERROR：.current 不存在：%s" % current)
    else:
        try:
            target = current.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            errors.append("ERROR：.current 无法读取（%s）" % exc)
        else:
            if target not in features:
                errors.append("ERROR：.current 指向 %r，不是有效 feature（有效：%s）"
                              % (target, list(features)))

    dash = wf_dir / "dashboard.md"
    if not dash.exists():
        errors.append("ERROR：dashboard.md 不存在：%s" % dash)
        return
    try:
        text = dash.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append("ERROR：dashboard.md 无法读取（%s）" % exc)
        return
    m = DASH_RE.search(text)
    if not m:
        errors.append("ERROR：dashboard.md 头部不符合 **X / N 完成** | **Y 进行中** | **Z 未启动**")
        return
    done_n, total_n, active_n, pending_n = (int(x) for x in m.groups())
    if total_n != len(features):
        warnings.append("WARNING：dashboard 总数 %s ≠ 实际 feature 数 %s" % (total_n, len(features)))
    if all(statuses is not None for statuses in features.values()):
        counts = {"done": 0, "active": 0, "pending": 0}
        for statuses in features.values():
            counts[dashboard_state(statuses)] += 1
        for bucket, label, actual in (("done", "完成", done_n), ("active", "进行中", active_n),
                                      ("pending", "未启动", pending_n)):
            if actual != counts[bucket]:
                warnings.append("WARNING：dashboard %s数 %s ≠ 实际 %s"
                                % (label, actual, counts[bucket]))
    for name in features:
        if name not in text:
            warnings.append("WARNING：dashboard 未登记 feature %s" % name)
    if "_template" in text:
        warnings.append("WARNING：dashboard 不应登记 _template")


def declared_paths(cfg):
    out = set()
    stages = cfg.get("stages")
    if isinstance(stages, dict):
        for v in stages.values():
            if not isinstance(v, dict):
                continue
            for k in ("file", "kb.recall_protocol", "kb.writeback_protocol"):
                val = v.get(k)
                if isinstance(val, str):
                    out.add(val)
            for k in ("references", "substeps"):
                val = v.get(k)
                if isinstance(val, list):
                    out.update(x for x in val if isinstance(x, str))
    aux = cfg.get("auxiliary")
    if isinstance(aux, dict):
        for v in aux.values():
            if isinstance(v, dict) and isinstance(v.get("file"), str):
                out.add(v["file"])
    for key in ("pitfalls", "kb"):
        val = cfg.get(key)
        if isinstance(val, str):
            out.add(val)
    kb = cfg.get("kb")
    if isinstance(kb, dict):
        for v in kb.values():
            if isinstance(v, str):
                out.add(v)
    return out


def pack_file_exists(pack_dir, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return False
    try:
        path = (pack_dir / value).resolve()
        path.relative_to(pack_dir.resolve())
        return path.is_file()
    except (OSError, RuntimeError, ValueError):
        return False


def check_pack(pack_dir, errors, warnings):
    cfg_path = pack_dir / "pack.yaml"
    if not cfg_path.exists():
        errors.append("ERROR %s：pack.yaml 缺失" % pack_dir.name)
        return
    cfg = load_yaml_dict(cfg_path, errors, "pack " + pack_dir.name)
    if cfg is None:
        return
    expected_id = pack_dir.name
    if cfg.get("pack_id") != expected_id:
        errors.append("ERROR %s：pack_id=%r 与目录名不一致" % (expected_id, cfg.get("pack_id")))
    for f in ("version", "display_name", "min_core_version", "tech", "stages", "auxiliary", "artifacts"):
        if f not in cfg:
            errors.append("ERROR %s：pack.yaml 缺字段 %s" % (expected_id, f))

    stages = cfg.get("stages")
    if not isinstance(stages, dict):
        errors.append("ERROR %s：stages 不是 mapping" % expected_id)
        stages = {}
    for i in range(1, COMPLETE):
        if str(i) not in stages:
            errors.append("ERROR %s：C1 缺阶段槽位 %s" % (expected_id, i))
            continue
        slot = stages[str(i)]
        if not isinstance(slot, dict):
            errors.append("ERROR %s：槽位 %s 不是 mapping" % (expected_id, i))
            continue
        if slot.get("status") not in ("implemented", "stub"):
            errors.append("ERROR %s：槽位 %s status 非法 %r" % (expected_id, i, slot.get("status")))
        if slot.get("status") == "implemented":
            f = slot.get("file")
            if not pack_file_exists(pack_dir, f):
                errors.append("ERROR %s：C2 槽位 %s file 不是域包内文件：%s" % (expected_id, i, f))
            for key in ("references", "substeps"):
                val = slot.get(key, [])
                if not isinstance(val, list):
                    errors.append("ERROR %s：C2 槽位 %s %s 必须是路径数组" % (expected_id, i, key))
                    continue
                for item in val:
                    if not pack_file_exists(pack_dir, item):
                        errors.append("ERROR %s：C2 槽位 %s %s 不是域包内文件：%s"
                                      % (expected_id, i, key, item))

    artifacts = cfg.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("ERROR %s：artifacts 不是 mapping" % expected_id)
    else:
        for i, key in enumerate(STAGE_KEYS, start=1):
            expected = STAGE_ARTIFACTS[key]
            actual = artifacts.get(str(i))
            if (not isinstance(actual, list) or not all(isinstance(x, str) for x in actual)
                    or not set(expected).issubset(actual)
                    or any(not name or Path(name).is_absolute() or ".." in Path(name).parts
                           for name in actual)
                    or len(actual) != len(set(actual))):
                errors.append("ERROR %s：artifacts.%s 必须包含 %s 且路径合法、无重复"
                              % (expected_id, i, expected))

    aux = cfg.get("auxiliary")
    if not isinstance(aux, dict):
        errors.append("ERROR %s：auxiliary 不是 mapping" % expected_id)
    else:
        for key, val in aux.items():
            if not isinstance(val, dict) or not isinstance(val.get("file"), str):
                errors.append("ERROR %s：auxiliary.%s.file 缺失" % (expected_id, key))
            elif not pack_file_exists(pack_dir, val["file"]):
                errors.append("ERROR %s：C2 auxiliary.%s.file 不是域包内文件：%s"
                              % (expected_id, key, val["file"]))

    kb = cfg.get("kb", {})
    if not isinstance(kb, dict):
        errors.append("ERROR %s：kb 不是 mapping" % expected_id)
    else:
        for key in ("recall_protocol", "writeback_protocol"):
            if key in kb and not pack_file_exists(pack_dir, kb[key]):
                errors.append("ERROR %s：C2 kb.%s 不是域包内文件：%s" % (expected_id, key, kb[key]))

    pit = cfg.get("pitfalls")
    if not pack_file_exists(pack_dir, pit):
        errors.append("ERROR %s：C5 pitfalls 不是域包内文件：%s" % (expected_id, pit))

    declared = declared_paths(cfg)
    for d in PACK_SCAN_DIRS:
        folder = pack_dir / d
        if not folder.exists():
            continue
        for md in sorted(folder.rglob("*.md")):
            rel = md.relative_to(pack_dir).as_posix()
            if rel not in declared:
                warnings.append("WARNING %s：C2R 未声明文件 %s" % (expected_id, rel))
    for child in sorted(pack_dir.iterdir()):
        if child.is_dir() and child.name not in PACK_SCAN_DIRS | PACK_EXEMPT_DIRS:
            warnings.append("WARNING %s：C2R 顶层目录未纳入扫描/豁免：%s" % (expected_id, child.name))


def profile_template_fields():
    """取两份模板 frontmatter 中字段定义的交集（引用的 field 必须在两份模板都有定义）。"""
    per_template = []
    for name in ("project_profile.template.md", "subsystem_profile.template.md"):
        path = TEMPLATES / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        front = text.split("---", 2)[1] if text.count("---") >= 2 else ""
        fields = set()
        section = None
        for line in front.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            m = SECTION_FIELD_RE.match(line.strip())
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if indent == 0:
                section = key if (val == "" and key in PROFILE_SECTIONS) else None
            elif section and indent <= 2:
                fields.add("%s.%s" % (section, key))
        per_template.append(fields)
    if not per_template:
        return set()
    common = set(per_template[0])
    for fields in per_template[1:]:
        common &= fields
    return common


def check_profile_contract(errors):
    defined = profile_template_fields()
    referenced = {}
    roots = [ROOT / "skills", ROOT / "tw" / "packs", ROOT / "tw" / "protocols", ROOT / "tw" / "workflows"]
    for root in roots:
        if not root.exists():
            continue
        for f in sorted(root.rglob("*")):
            if f.suffix.lower() not in {".md", ".py", ".yaml"}:
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                continue
            for m in FIELD_RE.finditer(text):
                ref = m.group(0)
                if ref.endswith(".md") or ref.endswith(".py") or ref.endswith(".yaml") or ref.endswith(".json"):
                    continue
                referenced.setdefault(ref, f.relative_to(ROOT).as_posix())
    for ref, where in sorted(referenced.items()):
        if ref not in defined:
            errors.append("ERROR：profile 契约引用 %s 未在模板定义（出现于 %s）" % (ref, where))
    for ref in sorted(defined - set(referenced)):
        print("[INFO] profile 字段 %s 已定义但未被消费（预留字段）" % ref)


def check_dump_contract(errors):
    proto = PROTOCOLS / "dump-artifact-protocol.md"
    if not proto.exists():
        errors.append("ERROR：dump-artifact-protocol.md 不存在")
    for pack_dir in sorted(PACKS.iterdir()):
        if not pack_dir.is_dir():
            continue
        cfg_path = pack_dir / "pack.yaml"
        if not cfg_path.exists():
            continue
        cfg = load_yaml_dict(cfg_path, errors, "pack " + pack_dir.name)
        if cfg is None:
            continue
        aux = cfg.get("auxiliary")
        if not isinstance(aux, dict) or "dump-page" not in aux:
            continue
        val = aux["dump-page"]
        f = val.get("file") if isinstance(val, dict) else None
        if not pack_file_exists(pack_dir, f):
            errors.append("ERROR %s：dump-page.file 不是域包内文件：%s" % (pack_dir.name, f))
            continue
        body = (pack_dir / f).read_text(encoding="utf-8")
        if "dump-artifact-protocol.md" not in body:
            errors.append("ERROR %s：%s 未引用 dump-artifact-protocol.md" % (pack_dir.name, f))
    for root in (ROOT / "skills", PACKS):
        if not root.exists():
            continue
        for f in sorted(root.rglob("*")):
            if f.suffix.lower() not in {".md", ".py"}:
                continue
            text = f.read_text(encoding="utf-8")
            for m in BARE_DUMP_RE.finditer(text):
                errors.append("ERROR：裸 dump 文件名 %s（出现于 %s）" % (m.group(0), f.relative_to(ROOT)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--check-pack", nargs="?", const="", metavar="DIR", help="域包自检")
    group.add_argument("--check-profile-contract", action="store_true")
    group.add_argument("--check-dump-contract", action="store_true")
    ap.add_argument("--workflows-dir", help="宿主项目 .claude/workflows 路径")
    ap.add_argument("--strict", action="store_true", help="WARNING 升级为失败")
    args = ap.parse_args()

    errors, warnings = [], []

    if args.check_pack is not None:
        if args.check_pack:
            target = Path(args.check_pack).expanduser().resolve()
            check_pack(target, errors, warnings)
        else:
            found = sorted(p for p in PACKS.iterdir() if p.is_dir() and (p / "pack.yaml").exists())
            if not found:
                errors.append("ERROR：tw/packs 下无域包")
            for p in found:
                check_pack(p, errors, warnings)
    elif args.check_profile_contract:
        check_profile_contract(errors)
    elif args.check_dump_contract:
        check_dump_contract(errors)
    else:
        if args.workflows_dir:
            wf = Path(args.workflows_dir).expanduser().resolve()
        else:
            wf = Path.cwd() / ".claude" / "workflows"
        check_workflows_dir(wf, errors, warnings)

    for w in warnings:
        print(w)
    for e in errors:
        print(e)
    failed = bool(errors) or (args.strict and bool(warnings))
    print("%s：%d ERROR / %d WARNING" % ("FAIL" if failed else "PASS", len(errors), len(warnings)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
