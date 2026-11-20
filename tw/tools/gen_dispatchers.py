#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""8 阶段工作流分发器生成器（单一模板 + STAGES 参数字典）。

护栏（见架构规格 §10.2）：
  1. 引用契约：渲染内容中出现的 tw/**.md|yaml|py 路径必须真实存在；默认渲染和 --check 都执行。
     默认渲染时若失败必须 abort，不得写入任何文件。
  2. 零耦合断言：渲染内容不得出现 record-workflows / record_state。
  3. 覆盖护栏（仅 --check）：任何含 [TW 阶段N] 的 skill 必须出现在 STAGES 中。

用法：
  python tw/tools/gen_dispatchers.py           # 渲染并写入 skills/
  python tw/tools/gen_dispatchers.py --check   # 只 diff，漂移/缺失退出码 1
"""
import sys
import re
import argparse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"

STAGES = {
    1: dict(command="business-context", title="业务知识召回", stage_key="1_business",
            triggers="业务知识召回 / 需求背景 / PRD / KB / 用例清单 / business context",
            review_gate="（**强制**：用例清单审核门）",
            gate_check_extra="入口阶段，无前置阶段；三道门见本阶段域包指令。",
            step3_extra="同时加载 pack.yaml.kb.recall_protocol 指向的召回协议。",
            exec_notes="按域包指令执行前置确认门 → 召回 → 完整性检查 → 用例派生 → 实质缺口门 → 用例审核门。",
            closing="三道门未全部通过不得进入 Exit Gate。"),
    2: dict(command="ui-test-data", title="测试数据构造", stage_key="2_data",
            triggers="测试数据 / 造数 / 前置数据 / 数据可见性 / test data",
            review_gate="（无强制审查门）",
            gate_check_extra="阶段边界见 tw/protocols/stage-registry.md。",
            step3_extra="",
            exec_notes="按域包指令定数据方案并验证数据在被测端可见；数据计划写入 stage2_data.md。",
            closing=""),
    3: dict(command="ui-test-assertion", title="断言设计", stage_key="3_assertion",
            triggers="断言 / 校验点 / severity / 路由 / assertion",
            review_gate="（**强制**：断言审核门）",
            gate_check_extra="阶段边界见 tw/protocols/stage-registry.md。",
            step3_extra="",
            exec_notes="按域包指令做三维分类、两层覆盖与路由；方法规则见 tw/protocols/assertion-protocol.md。",
            closing="route_provisional 为 true 的断言须在阶段 4 用真实 DOM 修订。"),
    4: dict(command="ui-test-case", title="用例开发", stage_key="4_case",
            triggers="写用例 / 生成测试代码 / 页面对象 / DOM / plan / case development",
            review_gate="（**强制**：plan 审查门）",
            gate_check_extra="阶段边界见 tw/protocols/stage-registry.md。",
            step3_extra="references/substeps 随阶段指令一并加载。",
            exec_notes="执行 4-0 中英双语查重 → 4-pre 分级采集 DOM → 4a-0 冲突对照 → 4a plan 审查 → 4b 编码；每个定位符必须标来源。",
            closing="stage4_plan.md 必须含 DOM 冲突修订表与 steps→方法映射。"),
    5: dict(command="verify", title="本地验证", stage_key="5_verify",
            triggers="跑测试 / 本地验证 / 修测试 / 探查修复循环 / verify / 失败归因",
            review_gate="（无强制审查门）",
            gate_check_extra="特殊分支与失败回拨以 tw/protocols/gate-protocol.md §2 / §4.3 为准。",
            step3_extra="substeps 在 Exit Gate 步骤中执行（如 runner 注册）。",
            exec_notes="按域包指令跑单测并按断言三维字段归因；≤7 轮，禁止放宽断言迁就实现。",
            closing="失败路径的 mode 分支见 tw/protocols/gate-protocol.md §4.3。"),
    6: dict(command="ui-test-e2e", title="端到端", stage_key="6_e2e",
            triggers="全量回归 / 端到端 / flaky / 不稳定用例 / e2e",
            review_gate="（无强制审查门）",
            gate_check_extra="阶段边界见 tw/protocols/stage-registry.md。",
            step3_extra="",
            exec_notes="按域包指令跑全量回归并做 flaky quarantine 四步治理。",
            closing=""),
    7: dict(command="report", title="开发汇报", stage_key="7_report",
            triggers="开发汇报 / 覆盖率 / 待确认项 / 完成报告 / report",
            review_gate="（无强制审查门）",
            gate_check_extra="阶段边界见 tw/protocols/stage-registry.md。",
            step3_extra="",
            exec_notes="按域包指令产出四项汇报 + 介入点汇总。",
            closing=""),
    8: dict(command="wiki-feedback", title="知识反哺", stage_key="8_kb_feedback",
            triggers="知识反哺 / 写回知识库 / KB / 闭环 / wiki feedback",
            review_gate="（无强制审查门）",
            gate_check_extra="阶段边界见 tw/protocols/stage-registry.md。",
            step3_extra="按 pack.yaml.kb.writeback_protocol 加载写回协议。",
            exec_notes="按 kb.writeback 策略把阶段坑点写回 KB，完成闭环。",
            closing=""),
}

TEMPLATE = """---
name: {command}
description: "[TW 阶段{num}] {title}。<触发词：{triggers}>"
---

# /tw:{command} — {title}

> 本技能是 TW 框架 L0 的薄分发器，只做五步编排；门禁与做法的真相源是协议与域包指令，本文件不复述条款。
> 本 plugin 根目录下的 tw/ 子目录（相对本 SKILL.md 为 ../../tw/）；路径不确定就 Glob 搜 **/tw/protocols/gate-protocol.md。

## Step 1 · Gate Check
读取宿主项目 .current 指向的 feature，打开 .claude/workflows/<feature>/state.json，按 tw/protocols/gate-protocol.md §2 的四分支校验 current_stage（本命令对应阶段 {num}，状态键 {stage_key}）。{gate_check_extra}

## Step 2 · 解析 profile
按 tw/protocols/gate-protocol.md §3 解析两级 profile 与端解析（pack_by_platform）；记录 paths / run / data_layer / kb / external_sync 与项目坑点表。

## Step 3 · 加载域包
从解析出的 pack.yaml 读取 `stages."{num}"` 的 file / references / substeps 并加载；能力键门控按 auxiliary 判断，不硬编码域包名。{step3_extra}

## Step 4 · 执行阶段指令
严格按域包阶段指令执行。{exec_notes}
证据纪律：用例派生见 tw/protocols/case-expansion-protocol.md，断言设计见 tw/protocols/assertion-protocol.md，页面证据落盘见 tw/protocols/dump-artifact-protocol.md。

## Step 5 · Exit Gate
按 tw/protocols/gate-protocol.md §4 的五步收尾：①写产出物 ②审查门{review_gate} ③更新状态（只有 Exit Gate 写状态）④坑点三层路由（无新增也要显式写明）⑤刷新看板并运行 `python tw/tools/validate_workflow.py --workflows-dir .claude/workflows`。
{closing}

## 命令边界
| 想做的事 | 走哪个 |
|---|---|
| 从零理解业务再开发 | 8 阶段 `/tw:new-feature` |
| 已能手工跑通一条流程，想派生整套用例 | `/tw:record-feature` |
| 给已有用例加测试点 | `/tw:ui-test-case` |
| 基于已开发完成的用例派生新场景 | `/tw:ui-test-extend` |
| 修 bug / 调试失败 | `/tw:ui-test-diagnosis` |
| 只想录一段代码骨架 | `/tw:record`（不进状态机） |
"""

REF_RE = re.compile(r"tw/[\w./-]+\.(?:md|yaml|py)")
FORBIDDEN = ("record-workflows", "record_state")


def render(num):
    s = STAGES[num]
    text = TEMPLATE
    for key, value in [("num", num), ("command", s["command"]), ("title", s["title"]),
                       ("triggers", s["triggers"]), ("review_gate", s["review_gate"]),
                       ("gate_check_extra", s["gate_check_extra"]), ("step3_extra", s["step3_extra"]),
                       ("exec_notes", s["exec_notes"]), ("closing", s["closing"]),
                       ("stage_key", s["stage_key"])]:
        text = text.replace("{" + key + "}", str(value))
    return text


def guard_rendered(text, errors):
    for match in REF_RE.finditer(text):
        rel = match.group(0)
        if not (ROOT / rel).exists():
            errors.append("引用契约失败：渲染内容引用了不存在的文件 " + rel)
    for token in FORBIDDEN:
        if token in text:
            errors.append("零耦合断言失败：8 阶段渲染内容出现了 " + token)


def guard_coverage(errors):
    for skill in sorted(SKILLS.glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        for num in re.findall(r"\[TW 阶段(\d+)\]", text):
            if int(num) not in STAGES:
                errors.append("覆盖护栏失败：%s 含 [TW 阶段%s] 但不在 STAGES" % (skill.parent.name, num))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="只比对，不写入")
    args = ap.parse_args()

    rendered = {}
    errors = []
    for num in sorted(STAGES):
        text = render(num)
        rendered[STAGES[num]["command"]] = text
        guard_rendered(text, errors)

    if args.check:
        guard_coverage(errors)
        for command, text in rendered.items():
            path = SKILLS / command / "SKILL.md"
            if not path.exists():
                errors.append("缺失分发器：" + str(path.relative_to(ROOT)))
            elif path.read_text(encoding="utf-8") != text:
                errors.append("分发器漂移：" + str(path.relative_to(ROOT)))
    else:
        if errors:
            print("护栏未通过，abort，未写入任何文件：")
            for e in errors:
                print("  ✗ " + e)
            return 1
        for command, text in rendered.items():
            path = SKILLS / command / "SKILL.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    if errors:
        print("FAIL：%d 个问题" % len(errors))
        for e in errors:
            print("  ✗ " + e)
        return 1
    print("PASS：8 个 8 阶段分发器%s（引用契约 / 零耦合%s）" %
          ("一致" if args.check else "已生成", " / 覆盖护栏" if args.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
