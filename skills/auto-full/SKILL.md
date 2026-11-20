---
name: auto-full
description: >
  全自动模式推进，无暂停；失败即停不假装成功。触发：auto-full、全自动。
---

# /tw:auto-full — 全自动推进

## 职责
把 `state.mode` 置 `full-auto`，不暂停地推进全部阶段。

## 步骤
1. 置 mode=full-auto，循环调用各阶段命令。
2. Exit Gate Step 2 记 `review_needed=true`、`human_intervention=false`，无人审查。
3. **阶段 5 七轮用尽**：记 `5_verify=failed`，`current_stage` 停在 5（不自洽回拨 4），**停止推进并报告**，不继续阶段 6。想跑回归须显式把 5_verify 置 skipped 并写 bypasses 留痕。
4. 任何校验器 ERROR 即停止报告。
5. 结束刷新 dashboard。
