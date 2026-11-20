---
name: record-capture
description: "[TW 录制阶段1] 录制。<触发词：录制主流程 / codegen / 录屏生成用例 / record capture>"
---

# /tw:record-capture — 录制

> 本技能是录制驱动工作流 L0 的薄分发器，只做五步编排；门禁与做法的真相源是录制侧协议与域包指令。
> 本 plugin 根目录下的 tw/ 子目录（相对本 SKILL.md 为 ../../tw/）；路径不确定就 Glob 搜 **/tw/workflows/record-driven/protocols/gate-protocol.md。

## Step 1 · Gate Check
读取 .claude/record-workflows/.current 指向的 feature，打开 .claude/record-workflows/<feature>/record_state.json，按 tw/workflows/record-driven/protocols/gate-protocol.md §2 的四分支校验 current_stage（本命令对应阶段 1，状态键 1_capture）。1e 操作序列人工核对是阶段内门；single 模式尤其不可跳。

## Step 2 · 解析 profile
按 tw/protocols/gate-protocol.md §3 解析两级 profile 与端解析；录制仅适用于 workflow.yaml.applies_to_packs 声明的域包。

## Step 3 · 加载域包
从激活域包读取 workflow.yaml 中 stages."1" 的 pack_path / references 并加载；能力键门控按 auxiliary 判断，不硬编码域包名。按 pack.yaml.auxiliary.record 判断录制能力是否存在。

## Step 4 · 执行阶段指令
严格按域包录制阶段指令执行。1-0 依赖检查 → 录一条正向主流程 → 后处理 → 1e 人工核对操作序列。
证据纪律见 tw/protocols/case-expansion-protocol.md 与 tw/protocols/assertion-protocol.md；证据落盘见 tw/protocols/dump-artifact-protocol.md。

## Step 5 · Exit Gate
按 tw/workflows/record-driven/protocols/gate-protocol.md §4 的五步收尾：①写产出物 ②审查门（none（阶段内 1e 人工核对，不可跳））③更新状态（只有 Exit Gate 写状态）④坑点三层路由（无新增也要显式写明）⑤刷新看板并运行 `python tw/workflows/record-driven/tools/validate_record_workflow.py --workflows-dir .claude/record-workflows`。
不执行 record.md 的 --with-assertion 段（断言归阶段 2）。

## 命令边界
| 想做的事 | 走哪个 |
|---|---|
| 从零理解业务再开发 | 8 阶段 `/tw:new-feature` |
| 已能手工跑通一条流程，想派生整套用例 | `/tw:record-feature` |
| 给已有用例加测试点 | `/tw:ui-test-case` |
| 基于已开发完成的用例派生新场景 | `/tw:ui-test-extend` |
| 修 bug / 调试失败 | `/tw:ui-test-diagnosis` |
| 只想录一段代码骨架 | `/tw:record`（不进状态机） |
