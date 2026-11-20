---
name: ui-test-data
description: "[TW 阶段2] 测试数据构造。<触发词：测试数据 / 造数 / 前置数据 / 数据可见性 / test data>"
---

# /tw:ui-test-data — 测试数据构造

> 本技能是 TW 框架 L0 的薄分发器，只做五步编排；门禁与做法的真相源是协议与域包指令，本文件不复述条款。
> 本 plugin 根目录下的 tw/ 子目录（相对本 SKILL.md 为 ../../tw/）；路径不确定就 Glob 搜 **/tw/protocols/gate-protocol.md。

## Step 1 · Gate Check
读取宿主项目 .current 指向的 feature，打开 .claude/workflows/<feature>/state.json，按 tw/protocols/gate-protocol.md §2 的四分支校验 current_stage（本命令对应阶段 2，状态键 2_data）。阶段边界见 tw/protocols/stage-registry.md。

## Step 2 · 解析 profile
按 tw/protocols/gate-protocol.md §3 解析两级 profile 与端解析（pack_by_platform）；记录 paths / run / data_layer / kb / external_sync 与项目坑点表。

## Step 3 · 加载域包
从解析出的 pack.yaml 读取 `stages."2"` 的 file / references / substeps 并加载；能力键门控按 auxiliary 判断，不硬编码域包名。

## Step 4 · 执行阶段指令
严格按域包阶段指令执行。按域包指令定数据方案并验证数据在被测端可见；数据计划写入 stage2_data.md。
证据纪律：用例派生见 tw/protocols/case-expansion-protocol.md，断言设计见 tw/protocols/assertion-protocol.md，页面证据落盘见 tw/protocols/dump-artifact-protocol.md。

## Step 5 · Exit Gate
按 tw/protocols/gate-protocol.md §4 的五步收尾：①写产出物 ②审查门（无强制审查门） ③更新状态（只有 Exit Gate 写状态）④坑点三层路由（无新增也要显式写明）⑤刷新看板并运行 `python tw/tools/validate_workflow.py --workflows-dir .claude/workflows`。


## 命令边界
| 想做的事 | 走哪个 |
|---|---|
| 从零理解业务再开发 | 8 阶段 `/tw:new-feature` |
| 已能手工跑通一条流程，想派生整套用例 | `/tw:record-feature` |
| 给已有用例加测试点 | `/tw:ui-test-case` |
| 基于已开发完成的用例派生新场景 | `/tw:ui-test-extend` |
| 修 bug / 调试失败 | `/tw:ui-test-diagnosis` |
| 只想录一段代码骨架 | `/tw:record`（不进状态机） |
