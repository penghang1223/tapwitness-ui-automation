# Record State Protocol — 录制状态机

## 1. schema（§5.5）
顶层必填：`feature` / `workflow`(恒为 "record-driven") / `created` / `mode` / `current_stage` / `stages` / `bypasses`。
阶段键：`1_capture` / `2_casegen` / `3_case` / `4_run` / `5_review`。

## 2. 枚举与自洽
`mode`: manual / semi-auto / full-auto；status: pending / in_progress / done / skipped / failed。
`current_stage` ∈ 1..6，等于第一个 status ∉ {done,skipped} 的阶段号；全终态为 6。
`failed` 只允许在 `4_run` / `5_review`。`4_run=failed` 停在 4（自洽），不参与回拨。
`5_review=done` 且已回拨时，current_stage 由 `3_case.status=in_progress` 决定为 3。

## 3. 回拨与 rework_round
`rework_round` 写在 `3_case` 上，语义严格是「回拨进入阶段 3 的次数」。首次回拨时才写入，模板不含。
阶段 4 七轮用尽：manual/semi-auto 回拨 3 且 rework_round += 1；full-auto 停 4、不加一。
阶段 5 结论「需修」：三种 mode 都回拨 3、rework_round += 1，>2 停止。
阶段 5 审核动作本身失败：置 `5_review=failed`、current_stage 停 5、不回拨、rework_round 不变。

## 4. 审查门三值模型
与 L0 §4.3 一致：批准 false/false；edit/skip/accept true/false+note；exit 保留退出前的 human_intervention 与 review_needed=true；full-auto false/true。已完成阶段在 semi-auto 审查门退出时保持 false/true。
`[skip]` / `[accept]` 不写 bypasses。

## 5. bypasses
与 L0 一致：只记阶段级 skipped，reason ≥5，双向对账。
