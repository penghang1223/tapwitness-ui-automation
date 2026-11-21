#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录制驱动工作流校验器：录制状态机校验 + 定义自检（W3R / W8）。

模式（互斥）：
  --check-workflow      校验 workflow.yaml 定义（5 槽位 / artifacts / W3R / W8）。
  默认                  校验 .claude/record-workflows 状态机；省略 --workflows-dir 时取 CWD 下该目录。
  --strict              WARNING 升级为失败。

退出码：有 ERROR，或无 ERROR 但 --strict 且有 WARNING → 1；否则 0。
与 8 阶段校验器零耦合：不 import 任何其他校验器。
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

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1]
PACKS = ROOT / "tw" / "packs"

STAGE_KEYS = ["1_capture", "2_casegen", "3_case", "4_run", "5_review"]
COMPLETE = 6
STATUSES = {"pending", "in_progress", "done", "skipped", "failed"}
FAILED_ALLOWED = {"4_run", "5_review"}
STAGE_ARTIFACTS = {
    "1_capture": ["stage1_record.md"],
    "2_casegen": ["stage2_cases.md", "stage2_cases.json"],
    "3_case": ["stage3_plan.md", "stage3_files.md"],
    "4_run": ["stage4_run.log"],
    "5_review": ["stage5_review.md"],
}
DASH_RE = re.compile(r"\*\*\s*(\d+)\s*/\s*(\d+)\s*完成\*\*\s*\|\s*\*\*\s*(\d+)\s*进行中\*\*\s*\|\s*\*\*\s*(\d+)\s*未启动\*\*")


def load_yaml_dict(path, errors, label):
    try:
        import yaml
    except ImportError:
        errors.append("ERROR %s：缺少 PyYAML" % label)
        return None
    if not path.exists():
        errors.append("ERROR %s：文件不存在 %s" % (label, path))
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
        errors.append("ERROR %s：YAML 非法（%s）" % (label, exc))
        return None
    if not isinstance(data, dict):
        errors.append("ERROR %s：顶层不是 mapping（%s）" % (label, type(data).__name__))
        return None
    return data


def file_exists_under(directory, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return False
    try:
        path = (directory / value).resolve()
        path.relative_to(directory.resolve())
        return path.is_file()
    except (OSError, RuntimeError, ValueError):
        return False


def check_workflow_definition(errors, warnings):
    cfg = load_yaml_dict(HERE / "workflow.yaml", errors, "workflow")
    if cfg is None:
        return
    if cfg.get("workflow_id") != "record-driven":
        errors.append("ERROR：workflow_id 必须为 record-driven")
    for f in ("version", "display_name", "applies_to_packs", "state", "stages", "artifacts", "rollback", "failed_allowed", "pause_points"):
        if f not in cfg:
            errors.append("ERROR：workflow.yaml 缺字段 %s" % f)
    state_cfg = cfg.get("state")
    if not isinstance(state_cfg, dict) or state_cfg.get("max_stage") != COMPLETE:
        errors.append("ERROR：state.max_stage 必须为 %s" % COMPLETE)

    pack_ids = cfg.get("applies_to_packs")
    if not isinstance(pack_ids, list) or not all(
            isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9-]*", value)
            for value in pack_ids):
        errors.append("ERROR：applies_to_packs 必须是域包 ID 数组")
        pack_ids = []
    applies = set(pack_ids)
    declared = set()
    protocol_prefix = "../../protocols/"
    stages = cfg.get("stages")
    if not isinstance(stages, dict):
        errors.append("ERROR：stages 不是 mapping")
        stages = {}
    for i, stage_key in enumerate(STAGE_KEYS, start=1):
        if str(i) not in stages:
            errors.append("ERROR：缺阶段槽位 %s" % i)
            continue
        slot = stages[str(i)]
        if not isinstance(slot, dict):
            errors.append("ERROR：槽位 %s 不是 mapping" % i)
            continue
        if slot.get("key") != stage_key:
            errors.append("ERROR：槽位 %s key=%r 应为 %s" % (i, slot.get("key"), stage_key))
        if not isinstance(slot.get("command"), str):
            errors.append("ERROR：槽位 %s 缺 command" % i)
        pack_path = slot.get("pack_path")
        if not isinstance(pack_path, str) or not pack_path.endswith(".md"):
            errors.append("ERROR：槽位 %s pack_path 非法" % i)
        else:
            declared.add(pack_path)
            for pack_id in sorted(applies):
                if not file_exists_under(PACKS / pack_id, pack_path):
                    errors.append("ERROR：域包 %s 槽位 %s pack_path 不是域包内文件：%s"
                                  % (pack_id, i, pack_path))
        refs = slot.get("references", [])
        if not isinstance(refs, list):
            errors.append("ERROR：槽位 %s references 不是数组" % i)
            continue
        for ref in refs:
            if not isinstance(ref, str) or not ref:
                errors.append("ERROR：槽位 %s references 含非法路径：%r" % (i, ref))
            elif ref.startswith(protocol_prefix):
                if not file_exists_under(ROOT / "tw" / "protocols", ref[len(protocol_prefix):]):
                    errors.append("ERROR：槽位 %s references 不是有效共用协议：%s" % (i, ref))
            else:
                declared.add(ref)
                for pack_id in sorted(applies):
                    if not file_exists_under(PACKS / pack_id, ref):
                        errors.append("ERROR：域包 %s 槽位 %s references 不是域包内文件：%s"
                                      % (pack_id, i, ref))

    arts = cfg.get("artifacts")
    if not isinstance(arts, dict):
        errors.append("ERROR：artifacts 不是 mapping")
    else:
        for i, key in enumerate(STAGE_KEYS, start=1):
            expected = STAGE_ARTIFACTS[key]
            actual = arts.get(str(i))
            if (not isinstance(actual, list) or not all(isinstance(x, str) for x in actual)
                    or not set(expected).issubset(actual)
                    or any(not name or Path(name).is_absolute() or ".." in Path(name).parts
                           for name in actual)
                    or len(actual) != len(set(actual))):
                errors.append("ERROR：artifacts.%s 必须包含 %s 且路径合法、无重复" % (i, expected))
    if cfg.get("failed_allowed") != ["4_run", "5_review"]:
        errors.append("ERROR：failed_allowed 必须为 [4_run, 5_review]")
    if cfg.get("rollback") != {"4": 3, "5": 3}:
        errors.append("ERROR：rollback 必须为 {'4':3,'5':3}")

    has_record = set()
    for pack_dir in sorted(PACKS.iterdir()):
        if not pack_dir.is_dir() or not (pack_dir / "pack.yaml").exists():
            continue
        pcfg = load_yaml_dict(pack_dir / "pack.yaml", errors, "pack " + pack_dir.name)
        if pcfg is None:
            continue
        aux = pcfg.get("auxiliary")
        if isinstance(aux, dict) and "record" in aux:
            has_record.add(pack_dir.name)
    for pack_id in sorted(applies - has_record):
        warnings.append("WARNING W3R：applies_to_packs 含 %s 但域包无 auxiliary.record" % pack_id)
    for pack_id in sorted(has_record - applies):
        warnings.append("WARNING W3R：域包 %s 有 auxiliary.record 但不在 applies_to_packs" % pack_id)

    for pack_id in sorted(applies):
        rdir = PACKS / pack_id / "workflows" / "record-driven"
        if not rdir.exists():
            continue
        for md in sorted(rdir.rglob("*.md")):
            rel = md.relative_to(PACKS / pack_id).as_posix()
            if rel not in declared:
                warnings.append("WARNING W8：域包 %s 录制文件未声明：%s" % (pack_id, rel))


def check_state_file(path, errors, warnings):
    feature = path.parent.name
    try:
        st = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append("ERROR %s：record_state.json 无法解析（%s）" % (feature, exc))
        return
    if not isinstance(st, dict):
        errors.append("ERROR %s：record_state.json 顶层不是对象" % feature)
        return
    if "created" not in st:
        errors.append("ERROR %s：record_state.json 缺字段 created" % feature)
    if st.get("workflow") != "record-driven":
        errors.append("ERROR %s：workflow 必须为 record-driven" % feature)
    if st.get("feature") != feature:
        errors.append("ERROR %s：feature 与目录名不一致" % feature)
    mode = st.get("mode")
    if not isinstance(mode, str) or mode not in {"manual", "semi-auto", "full-auto"}:
        errors.append("ERROR %s：mode 非法 %r" % (feature, mode))
    stages = st.get("stages")
    if not isinstance(stages, dict):
        errors.append("ERROR %s：stages 不是对象" % feature)
        return None
    statuses = {}
    for key in STAGE_KEYS:
        if key not in stages:
            errors.append("ERROR %s：stages 缺键 %s" % (feature, key))
            continue
        e = stages[key]
        if not isinstance(e, dict):
            errors.append("ERROR %s：%s 不是对象" % (feature, key))
            continue
        status = e.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append("ERROR %s：%s status 非法 %r" % (feature, key, status))
            continue
        statuses[key] = status
        if status == "failed" and key not in FAILED_ALLOWED:
            errors.append("ERROR %s：failed 只允许出现在 %s" % (feature, FAILED_ALLOWED))
        hi = e.get("human_intervention")
        if isinstance(hi, str):
            errors.append("ERROR %s：%s human_intervention 是字符串" % (feature, key))
        elif hi is not None and not isinstance(hi, bool):
            errors.append("ERROR %s：%s human_intervention 必须为布尔或 null" % (feature, key))
        if status in {"done", "skipped"} and hi is None:
            errors.append("ERROR %s：%s 为 %s 但 human_intervention 为 null" % (feature, key, status))
        if hi is True and not e.get("intervention_note"):
            errors.append("ERROR %s：%s human_intervention=true 但缺 intervention_note" % (feature, key))
        if "review_needed" in e and not isinstance(e["review_needed"], bool):
            errors.append("ERROR %s：%s review_needed 必须是布尔" % (feature, key))
        if status == "done":
            for art in STAGE_ARTIFACTS[key]:
                if not (path.parent / art).is_file():
                    errors.append("ERROR %s：done 阶段 %s 缺产出 %s" % (feature, key, art))
    cur = st.get("current_stage")
    if not isinstance(cur, int) or isinstance(cur, bool) or not (1 <= cur <= COMPLETE):
        errors.append("ERROR %s：current_stage 非法 %r" % (feature, cur))
    elif len(statuses) == len(STAGE_KEYS):
        expected = next((i for i, key in enumerate(STAGE_KEYS, start=1)
                         if statuses[key] not in {"done", "skipped"}), COMPLETE)
        if cur != expected:
            errors.append("ERROR %s：current_stage=%s 与状态不自洽（应为 %s）" % (feature, cur, expected))

    by = st.get("bypasses")
    if not isinstance(by, list):
        errors.append("ERROR %s：bypasses 不是数组" % feature)
        by = []
    by_stages = set()
    for item in by:
        if not isinstance(item, dict):
            errors.append("ERROR %s：bypass 元素不是对象" % feature)
            continue
        s, reason, ts = item.get("stage"), item.get("reason"), item.get("timestamp")
        if type(s) is not int or not (1 <= s < COMPLETE):
            errors.append("ERROR %s：bypass.stage 非法 %r" % (feature, s))
        else:
            by_stages.add(s)
        if not isinstance(reason, str) or len(reason) < 5:
            errors.append("ERROR %s：bypass.reason 少于 5 字符" % feature)
        if not isinstance(ts, str) or not ts:
            errors.append("ERROR %s：bypass.timestamp 缺失" % feature)
    rw = stages.get("3_case", {}).get("rework_round") if isinstance(stages.get("3_case"), dict) else None
    if rw is not None:
        if not isinstance(rw, int) or isinstance(rw, bool):
            errors.append("ERROR %s：rework_round 必须是整数" % feature)
        elif rw > 2:
            warnings.append("WARNING %s：rework_round=%s > 2，应停止推进" % (feature, rw))
    if len(statuses) != len(STAGE_KEYS):
        return None
    skipped = {i for i, key in enumerate(STAGE_KEYS, start=1) if statuses[key] == "skipped"}
    for s in sorted(skipped - by_stages):
        errors.append("ERROR %s：阶段 %s skipped 但无 bypasses 记录" % (feature, s))
    for s in sorted(by_stages - skipped):
        errors.append("ERROR %s：bypasses 记了阶段 %s 但非 skipped" % (feature, s))
    return statuses


def dashboard_state(statuses):
    if all(v in {"done", "skipped"} for v in statuses.values()):
        return "done"
    if all(v == "pending" for v in statuses.values()):
        return "pending"
    return "active"


def check_workflows_dir(wf_dir, errors, warnings):
    if not wf_dir.exists() or not wf_dir.is_dir():
        errors.append("ERROR：录制工作流目录不存在：%s" % wf_dir)
        return
    features = {}
    for child in sorted(wf_dir.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name == "_template":
            continue
        if not (child / "record_state.json").exists():
            continue
        features[child.name] = check_state_file(child / "record_state.json", errors, warnings)
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
                errors.append("ERROR：.current 指向 %r，不是有效 feature" % target)
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
        errors.append("ERROR：dashboard 头部格式不符")
        return
    done_n, total_n, active_n, pending_n = (int(x) for x in m.groups())
    if total_n != len(features):
        warnings.append("WARNING：dashboard 总数 %s ≠ 实际 %s" % (total_n, len(features)))
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--check-workflow", action="store_true")
    ap.add_argument("--workflows-dir")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    errors, warnings = [], []

    if args.check_workflow:
        check_workflow_definition(errors, warnings)
    else:
        if args.workflows_dir:
            wf = Path(args.workflows_dir).expanduser().resolve()
        else:
            wf = Path.cwd() / ".claude" / "record-workflows"
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
