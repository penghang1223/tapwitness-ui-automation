#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录制驱动工作流分发器生成器（单一模板 + STAGES 参数字典）。

护栏（见架构规格 §10.2，录制侧补齐覆盖护栏）：
  1. 引用契约：渲染内容中出现的 tw/**.md|yaml|py 路径必须真实存在；默认渲染和 --check 都执行。
  2. 零耦合断言：录制渲染内容不得出现 .claude/workflows。
  3. 覆盖护栏（仅 --check）：含 [TW 录制阶段N] 的 skill 必须是 STAGES 登记的对应命令。

用法：
  python tw/workflows/record-driven/tools/gen_record_dispatchers.py
  python tw/workflows/record-driven/tools/gen_record_dispatchers.py --check
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

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"

STAGES = {
    1: dict(command="record-capture", title="录制", stage_key="1_capture",
            triggers="录制主流程 / codegen / 录屏生成用例 / record capture",
            review_gate="none（阶段内 1e 人工核对，不可跳）",
            gate_check_extra="1e 操作序列人工核对是阶段内门；single 模式尤其不可跳。",
            step3_extra="按 pack.yaml.auxiliary.record 判断录制能力是否存在。",
            exec_notes="1-0 依赖检查 → 录一条正向主流程 → 后处理 → 1e 人工核对操作序列。",
            closing="不执行 record.md 的 --with-assertion 段（断言归阶段 2）。"),
    2: dict(command="record-casegen", title="生成用例", stage_key="2_casegen",
            triggers="录制生成用例 / 拆解录制 / 派生用例 / casegen",
            review_gate="mandatory（用例清单审查门）",
            gate_check_extra="full（默认）/ single 模式先定；三路依据与证据分级见 case-expansion-protocol。",
            step3_extra="",
            exec_notes="2-0 前置检查 → 2a 拆解 → 2b 三路依据 → 2c 派生 → 2d 挂断言 → 2e data_plan → 2f 双格式 → 2g 审查门。",
            closing="degraded=true 时只出正向变体并在 md 顶部显式标注依据缺失。"),
    3: dict(command="record-dev", title="开发用例", stage_key="3_case",
            triggers="录制用例开发 / 写录制用例代码 / 3a plan / record dev",
            review_gate="substep（3a plan 审查门）",
            gate_check_extra="回拨进入本阶段时写 rework_round（次数严格等于回拨次数）。",
            step3_extra="",
            exec_notes="3-pre DOM 准备 → 3a plan 审查（含 steps→方法覆盖表）→ 3b 编码 → 3c stage3_files.md。",
            closing="定位符证据必须是可核验三元组：证据位置 / 验证了什么 / 易失效项的验证动作。"),
    4: dict(command="record-run", title="执行并修复", stage_key="4_run",
            triggers="录制用例执行 / 跑录制用例 / 7 轮修复 / record run",
            review_gate="none",
            gate_check_extra="4 类回拨/停止分支按 mode 区分，见录制 gate-protocol §5。",
            step3_extra="",
            exec_notes="7 轮探查-修复循环，归因逻辑同 8 阶段；环境/真实 bug 不改脚本绕过。",
            closing="用尽 7 轮按 mode 决定回拨 3 或停在 4。"),
    5: dict(command="record-review", title="代码审核", stage_key="5_review",
            triggers="录制代码审核 / 独立子代理审核 / 用例对账 / record review",
            review_gate="mandatory（最终代码审核门）",
            gate_check_extra="审核对象是跑通后存活的最终代码；5-0 前置检查未跑通则回阶段 4。",
            step3_extra="",
            exec_notes="必须拉起独立审核子代理；五类检查逐条对账 stage2_cases.json。",
            closing="结论「需修」→ 回拨 3 并重走 3→4→5（rework_round>2 停止）；审核动作本身失败才写 5_review=failed。"),
}

TEMPLATE = """---
name: {command}
description: "[TW 录制阶段{num}] {title}。<触发词：{triggers}>"
---

# /tw:{command} — {title}

> 本技能是录制驱动工作流 L0 的薄分发器，只做五步编排；门禁与做法的真相源是录制侧协议与域包指令。
> 本 plugin 根目录下的 tw/ 子目录（相对本 SKILL.md 为 ../../tw/）；路径不确定就 Glob 搜 **/tw/workflows/record-driven/protocols/gate-protocol.md。

## Step 1 · Gate Check
读取 .claude/record-workflows/.current 指向的 feature，打开 .claude/record-workflows/<feature>/record_state.json，按 tw/workflows/record-driven/protocols/gate-protocol.md §2 的四分支校验 current_stage（本命令对应阶段 {num}，状态键 {stage_key}）。{gate_check_extra}

## Step 2 · 解析 profile
按 tw/protocols/gate-protocol.md §3 解析两级 profile 与端解析；录制仅适用于 workflow.yaml.applies_to_packs 声明的域包。

## Step 3 · 加载域包
从激活域包读取 workflow.yaml 中 stages."{num}" 的 pack_path / references 并加载；能力键门控按 auxiliary 判断，不硬编码域包名。{step3_extra}

## Step 4 · 执行阶段指令
严格按域包录制阶段指令执行。{exec_notes}
证据纪律见 tw/protocols/case-expansion-protocol.md 与 tw/protocols/assertion-protocol.md；证据落盘见 tw/protocols/dump-artifact-protocol.md。

## Step 5 · Exit Gate
按 tw/workflows/record-driven/protocols/gate-protocol.md §4 的五步收尾：①写产出物 ②审查门（{review_gate}）③更新状态（只有 Exit Gate 写状态）④坑点三层路由（无新增也要显式写明）⑤刷新看板并运行 `python3 "<插件根>/tw/workflows/record-driven/tools/validate_record_workflow.py" --workflows-dir .claude/record-workflows`。插件根为本 SKILL.md 的上两级；工作流目录相对宿主项目根。
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
FORBIDDEN = (".claude/workflows",)


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
            errors.append("零耦合断言失败：录制渲染内容出现了 " + token)


def guard_coverage(errors):
    for skill in sorted(SKILLS.glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        for num in re.findall(r"\[TW 录制阶段(\d+)\]", text):
            stage = STAGES.get(int(num))
            if stage is None or stage["command"] != skill.parent.name:
                errors.append("覆盖护栏失败：%s 未登记为录制阶段 %s 的分发器" % (skill.parent.name, num))


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
    print("PASS：5 个录制分发器%s（引用契约 / 零耦合%s）" %
          ("一致" if args.check else "已生成", " / 覆盖护栏" if args.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
