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
2. 循环：调用 `workflow-next` 选出的阶段命令；阶段命令的 Exit Gate Step 2 在非 manual 模式下**只记 review_needed=true、不暂停**。
3. **暂停由本 skill 统一处理**：阶段命令返回后，若当前阶段 ∈ {1,3,4,5}，展示 `[Enter]/[edit]/[skip]/[exit]`，等用户输入后按 §4.3 三值模型回写阶段条目的 human_intervention / review_needed / intervention_note。
4. 阶段 5 失败时让用户选 fix/skip/exit；fix 回拨阶段 4。
5. 用户 [exit] → 保持 review_needed=true、human_intervention=null，停止推进并报告。
6. 每轮结束刷新 dashboard 并运行非 strict 校验器。
