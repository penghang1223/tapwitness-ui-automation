---
name: record-dev
description: "[TW 录制阶段3] 开发用例。<触发词：录制用例开发 / 写录制用例代码 / 3a plan / record dev>"
---

# /tw:record-dev — 开发用例

> 本技能是录制驱动工作流 L0 的薄分发器，只做五步编排；门禁与做法的真相源是录制侧协议与域包指令。
> 本 plugin 根目录下的 tw/ 子目录（相对本 SKILL.md 为 ../../tw/）；路径不确定就 Glob 搜 **/tw/workflows/record-driven/protocols/gate-protocol.md。

## Step 1 · Gate Check
读取 .claude/record-workflows/.current 指向的 feature，打开 .claude/record-workflows/<feature>/record_state.json，按 tw/workflows/record-driven/protocols/gate-protocol.md §2 的四分支校验 current_stage（本命令对应阶段 3，状态键 3_case）。回拨进入本阶段时写 rework_round（次数严格等于回拨次数）。

## Step 2 · 解析 profile
按 tw/protocols/gate-protocol.md §3 解析两级 profile 与端解析；录制仅适用于 workflow.yaml.applies_to_packs 声明的域包。

## Step 3 · 加载域包
从激活域包读取 workflow.yaml 中 stages."3" 的 pack_path / references 并加载；能力键门控按 auxiliary 判断，不硬编码域包名。

## Step 4 · 执行阶段指令
严格按域包录制阶段指令执行。3-pre DOM 准备 → 3a plan 审查（含 steps→方法覆盖表）→ 3b 编码 → 3c stage3_files.md。
证据纪律见 tw/protocols/case-expansion-protocol.md 与 tw/protocols/assertion-protocol.md；证据落盘见 tw/protocols/dump-artifact-protocol.md。

## Step 5 · Exit Gate
按 tw/workflows/record-driven/protocols/gate-protocol.md §4 的五步收尾：①写产出物 ②审查门（substep（3a plan 审查门））③更新状态（只有 Exit Gate 写状态）④坑点三层路由（无新增也要显式写明）⑤刷新看板并运行 `python tw/workflows/record-driven/tools/validate_record_workflow.py --workflows-dir .claude/record-workflows`。
定位符证据必须是可核验三元组：证据位置 / 验证了什么 / 易失效项的验证动作。

## 命令边界
| 想做的事 | 走哪个 |
|---|---|
| 从零理解业务再开发 | 8 阶段 `/tw:new-feature` |
| 已能手工跑通一条流程，想派生整套用例 | `/tw:record-feature` |
| 给已有用例加测试点 | `/tw:ui-test-case` |
| 基于已开发完成的用例派生新场景 | `/tw:ui-test-extend` |
| 修 bug / 调试失败 | `/tw:ui-test-diagnosis` |
| 只想录一段代码骨架 | `/tw:record`（不进状态机） |
