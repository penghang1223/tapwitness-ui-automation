#!/usr/bin/env python3
"""校验阶段刚生成的结构化产物，失败时阻止该阶段推进。"""
import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def load_object(path, errors):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append("%s 无法解析（%s）" % (path.name, exc))
        return None
    if not isinstance(value, dict):
        errors.append("%s 顶层必须是对象" % path.name)
        return None
    return value


def check_cases(path, feature, workflow, errors):
    data = load_object(path, errors)
    if data is None:
        return None
    if data.get("feature") != feature:
        errors.append("%s 的 feature 与目录名不一致" % path.name)
    if data.get("workflow") != workflow:
        errors.append("%s 的 workflow 应为 %s" % (path.name, workflow))
    mode = data.get("expansion_mode")
    if mode not in ("full", "single"):
        errors.append("%s 的 expansion_mode 必须为 full 或 single" % path.name)
    evidence = data.get("evidence")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("degraded"), bool):
        errors.append("%s 的 evidence.degraded 必须是布尔值" % path.name)
        evidence = {}
    cases = data.get("cases")
    if not isinstance(cases, list):
        errors.append("%s 的 cases 必须是数组" % path.name)
        return None
    if mode == "single" and len(cases) != 1:
        errors.append("%s 的 single 模式必须恰有一条用例" % path.name)
    ids = set()
    for index, case in enumerate(cases, 1):
        label = "%s cases[%s]" % (path.name, index)
        if not isinstance(case, dict):
            errors.append("%s 必须是对象" % label)
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append("%s 缺少有效 id" % label)
        elif case_id in ids:
            errors.append("%s id 重复：%s" % (path.name, case_id))
        else:
            ids.add(case_id)
        category = case.get("category")
        if category not in ("正向", "边界", "负面"):
            errors.append("%s category 非法" % label)
        if evidence.get("degraded") is True and category != "正向":
            errors.append("%s 降级时只允许正向用例" % label)
        if case.get("evidence_level") not in ("confirmed", "inferred"):
            errors.append("%s evidence_level 非法" % label)
        if category in ("边界", "负面") and (
                not isinstance(case.get("evidence"), str) or not case["evidence"].strip()):
            errors.append("%s 边界或负面用例缺少 evidence" % label)
        plan = case.get("data_plan")
        if not isinstance(plan, dict):
            errors.append("%s 缺少 data_plan 对象" % label)
        else:
            for field in ("precondition_data", "data_source", "setup", "cleanup", "isolation_key", "verified"):
                if field not in plan:
                    errors.append("%s data_plan 缺少 %s" % (label, field))
            if "verified" in plan and not isinstance(plan["verified"], bool):
                errors.append("%s data_plan.verified 必须是布尔值" % label)
    return ids


def check_assertions(path, feature, case_ids, errors):
    data = load_object(path, errors)
    if data is None:
        return
    if data.get("feature") != feature:
        errors.append("%s 的 feature 与目录名不一致" % path.name)
    assertions = data.get("assertions")
    if not isinstance(assertions, list):
        errors.append("%s 的 assertions 必须是数组" % path.name)
        return
    ids = set()
    for index, assertion in enumerate(assertions, 1):
        label = "%s assertions[%s]" % (path.name, index)
        if not isinstance(assertion, dict):
            errors.append("%s 必须是对象" % label)
            continue
        assertion_id = assertion.get("id")
        if not isinstance(assertion_id, str) or not assertion_id.strip():
            errors.append("%s 缺少有效 id" % label)
        elif assertion_id in ids:
            errors.append("%s id 重复：%s" % (path.name, assertion_id))
        else:
            ids.add(assertion_id)
        case_id = assertion.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append("%s 缺少有效 case_id" % label)
        elif case_ids is not None and case_id not in case_ids:
            errors.append("%s 引用了不存在的用例 %s" % (label, case_id))
        route = assertion.get("route")
        if not isinstance(route, list) or not route or any(
                not isinstance(item, str) or item not in ("UI", "DB", "API") for item in route):
            errors.append("%s route 必须是非空 UI/DB/API 数组" % label)
        if assertion.get("severity") not in ("A", "B", "C"):
            errors.append("%s severity 非法" % label)
        if assertion.get("assertion_type") not in ("hard", "soft", "negative", "conditional"):
            errors.append("%s assertion_type 非法" % label)


def load_case_ids(path, feature, errors):
    data = load_object(path, errors)
    if data is None:
        return None
    cases = data.get("cases")
    if not isinstance(cases, list):
        errors.append("%s 的 cases 必须是数组" % path.name)
        return None
    if data.get("feature") != feature:
        errors.append("%s 的 feature 与目录名不一致" % path.name)
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"].strip():
            errors.append("%s 包含无有效 id 的用例" % path.name)
            continue
        if case["id"] in ids:
            errors.append("%s id 重复：%s" % (path.name, case["id"]))
        ids.add(case["id"])
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__, prog=Path(__file__).name)
    parser.add_argument("--workflow", choices=("8-stage", "record-driven"), required=True)
    parser.add_argument("--feature-dir", required=True, help="宿主项目 feature 目录")
    parser.add_argument("--stage", type=int, required=True)
    args = parser.parse_args()
    directory = Path(args.feature_dir).expanduser().resolve()
    errors = []
    if not directory.is_dir():
        errors.append("feature 目录不存在：%s" % directory)
    elif args.workflow == "8-stage" and args.stage == 1:
        check_cases(directory / "stage1_cases.json", directory.name, args.workflow, errors)
    elif args.workflow == "8-stage" and args.stage == 3:
        case_path = directory / "stage1_cases.json"
        case_ids = load_case_ids(case_path, directory.name, errors) if case_path.exists() else None
        if case_ids is None and not case_path.exists():
            print("WARNING：未找到 stage1_cases.json，无法对账断言与用例")
        check_assertions(directory / "stage3_assertions.json", directory.name, case_ids, errors)
    elif args.workflow == "record-driven" and args.stage == 2:
        check_cases(directory / "stage2_cases.json", directory.name, args.workflow, errors)
    else:
        errors.append("该工作流的阶段 %s 没有结构化产物校验" % args.stage)
    for error in errors:
        print("ERROR：%s" % error)
    print("%s：%s ERROR" % ("FAIL" if errors else "PASS", len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
