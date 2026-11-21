---
name: auto
description: >
  半自动模式推进 8 阶段工作流，阶段 1/3/4/5 出口暂停。触发：auto、半自动。
---

# /tw:auto — 半自动推进

## 职责
把 `state.mode` 置 `semi-auto`，循环驱动阶段；在阶段 1/3/4/5 出口暂停展示审查门 UI。

## 步骤
1. 读 `.current`；置 mode=semi-auto。
2. 每轮先记录本轮进入的阶段号 N，再调用 `workflow-next` 选择并执行对应阶段命令；阶段命令的 Exit Gate Step 2 在非 manual 模式下**只记 review_needed=true、不暂停**。
3. **暂停由本 skill 统一处理**：阶段命令成功返回后，若本轮执行的 N ∈ {1,3,4,5}，确保阶段 N 的 `review_needed=true`，对阶段 N 展示 `[Enter]/[edit]/[skip]/[exit]`，等用户输入后按 §4.3 三值模型回写阶段 N 的 human_intervention / review_needed / intervention_note。不得以返回后已推进的 current_stage 代替 N。阶段失败时按失败路径处理。
4. 阶段 5 失败时让用户选 fix/skip/exit；fix 回拨阶段 4。
5. 用户 [exit] → 保持 review_needed=true 和退出前的 human_intervention，停止推进并报告；若阶段已 done，human_intervention 应保持 false，恢复时先处理此审查门。
6. 每轮结束刷新 dashboard 并运行非 strict 校验器。
