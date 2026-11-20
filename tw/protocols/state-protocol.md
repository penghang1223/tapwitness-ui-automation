# State Protocol — 8 阶段状态机唯一规范

> 本文件是 8 阶段 `state.json` 的唯一真相源。域包与分发器只引用本文件，不复述条款。

## 1. 字段（schema §5.4）
顶层必填：`feature` / `created` / `mode` / `current_stage` / `stages` / `bypasses`。
可选顶层：`subsystem` / `platform` / `_schema_notes`。
阶段键固定八个：`1_business` / `2_data` / `3_assertion` / `4_case` / `5_verify` / `6_e2e` / `7_report` / `8_kb_feedback`。
阶段条目：`status` / `human_intervention` / `intervention_note`；进行中另有 `started_at`，完成另有 `completed_at`。

## 2. 枚举
- `mode`: `manual | semi-auto | full-auto`
- `status`: `pending | in_progress | done | skipped | failed`
- `human_intervention`: 布尔三态 `true | false | null`，**禁止字符串**。

## 3. 自洽规则
`current_stage` ∈ 1..9，等于第一个 status ∉ {done, skipped} 的阶段号；全部终态为 9。
唯一例外：`5_verify=failed` 时 `current_stage=4`（回拨）。
`failed` 只允许出现在 `5_verify`。
`done` / `skipped` 的 `human_intervention` 不得为 null；`true` 时必须写 `intervention_note`。
`review_needed` 为可选阶段级布尔字段，非 manual 模式下「审查门尚未被人工审查」时置 true（§4.3 三值模型）。

## 4. 审查门三值模型
| 动作 | human_intervention | review_needed |
|---|---|---|
| [Enter] 批准 | false | false |
| [edit]/[skip]/[accept] | true + note | false |
| [exit] | null | true |
| full-auto 未展示 | false | true |

## 5. bypasses
`bypasses[]`: `{stage:int, reason:str(≥5), timestamp:ISO-8601}`，与 `skipped` 双向对账。
只记阶段级跳过；审查门的 [skip] 不写这里。

## 6. 状态写入者
只有 Exit Gate 能推进状态；域包阶段指令禁止写 `state.json` / `.current` / `dashboard.md`。
例外：`workflow-bypass` 按本协议改。

## 7. dashboard 格式
头部：`**X / N 完成** | **Y 进行中** | **Z 未启动**`。
分桶：🟢 已完成（current_stage==9 或全终态）/ 🟡 进行中（按阶段倒序）/ 🔴 未启动（全 pending）。
`_template` 不计入功能数、不登记。
