---
name: workflow-bypass
description: >
  按 target_stage-1 语义跳过一个阶段并写 bypasses。触发：跳过阶段、bypass。
---

# /tw:workflow-bypass — 跳过阶段并留痕

## 职责
阶段级跳过（与审查门 [skip] 无关）。语义：`workflow-bypass 3 "reason"` 跳过的是**阶段 2**（target_stage-1）。

## 步骤
1. 解析 target_stage 与 reason（≥5 字符）。
2. 定位被跳阶段 `target_stage-1`，校验其 status ∈ {pending, in_progress}。
3. 置该阶段 `status=skipped`、`human_intervention=true`、`intervention_note=reason`。
4. 追加 `bypasses[]`：`{stage: N, reason, timestamp: now}`。
5. 重算 `current_stage`（第一个非 done/skipped 阶段号），刷新 dashboard。
6. 运行校验器确认 bypasses ↔ skipped 双向对账通过。
