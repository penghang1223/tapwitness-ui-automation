---
name: record-feature
description: >
  新建录制驱动工作流 feature。触发：录制新功能、record feature。
---

# /tw:record-feature — 新建录制工作流

## 职责
创建录制驱动工作流的 feature 与 `record_state.json`。

## 步骤
1. 校验 feature 名；确认 profile 的 pack 在 `tw/workflows/record-driven/workflow.yaml.applies_to_packs` 中，否则停止。
2. 建 `.claude/record-workflows/<feature>/`；从 `tw/workflows/record-driven/templates/record_state.json` 复制并填 feature / created。
3. 写 `.claude/record-workflows/.current`；更新录制 dashboard。
4. 运行 `python tw/workflows/record-driven/tools/validate_record_workflow.py --workflows-dir .claude/record-workflows`。

## 边界
workflow = "record-driven" 恒为固定值；current_stage 1..6。
