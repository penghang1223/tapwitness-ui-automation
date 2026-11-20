---
name: record-auto
description: >
  录制工作流半自动/全自动推进。触发：record auto、录制自动。
---

# /tw:record-auto — 录制自动推进

## 职责
`--single`/默认 semi-auto（暂停点：1e / 2 / 3a / 5）；`--full` full-auto。

## 步骤
1. 读 record_state.mode；循环驱动 record-capture → casegen → dev → run → review。
2. **阶段内部子步骤门（1e / 3a）由阶段指令展示 UI**；semi-auto 本 skill 在循环里不跳过这两点，等用户输入；full-auto 不暂停、记 review_needed=true。
3. Exit Gate 级审查门（阶段 2 / 5）：非 manual 只记 review_needed=true，暂停由本 skill 出口统一展示。

## `--full` 3 类必须停 + 2 类确定性处理
1. 阶段 2 `evidence.degraded==true` → 停止报告。
2. 阶段 4 归因为环境/真实 bug → 立即停止，不改脚本绕过。
3. 任一校验器（本次 Exit Gate Step 5 的录制校验器，非 strict）报 ERROR → 停止；WARNING 不触发。
4. 阶段 4 七轮用尽 → `4_run=failed`、`current_stage` 停 4，不回拨、rework_round 不变，停止。
5. 阶段 5 结论「需修」→ 自动回拨 3，`rework_round += 1`，受 >2 约束；超限停止报告。
> `rework_round > 2` 是第 5 行的上限子约束，不是独立安全阀。

## 停止格式
```
⛔ 全自动推进已停止：<原因>
已完成阶段：<列表>
待人工决策：<问题 + 文件:行>
继续方式：修复后调 /tw:record-<stage> 或 /tw:record-auto <feature>
```
> 「停」= 终止推进并报告，不是暂停等输入。
