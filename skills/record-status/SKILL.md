---
name: record-status
description: >
  只读查看录制工作流进度。触发：录制状态、record status。
---

# /tw:record-status — 录制工作流状态

## 职责
只读展示 `.claude/record-workflows/.current` 指向 feature 的 5 阶段状态。禁止写状态。

## 步骤
1. 读 `.current` → feature；读 record_state.json。
2. 逐阶段打印 status / human_intervention / rework_needed / rework_round。
3. 打印 current_stage 与下一命令；运行录制校验器展示告警。
