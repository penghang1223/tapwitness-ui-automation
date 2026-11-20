---
name: continue
description: >
  按 state.mode 从暂停点恢复推进。触发：continue、恢复、继续。
---

# /tw:continue — 从暂停点恢复

## 职责
读 `state.json.mode`，选择 auto / auto-full / manual 的恢复路径。

## 步骤
1. 读 mode：semi-auto → 复用 `auto` 的暂停逻辑；full-auto → 复用 `auto-full`；manual → 提示用 `workflow-next`。
2. 从 `current_stage` 继续，不重跑已完成阶段。
3. 若存在 `review_needed=true` 的未完成审查门，先展示审查门 UI 再推进。
