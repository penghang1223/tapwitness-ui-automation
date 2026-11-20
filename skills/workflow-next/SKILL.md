---
name: workflow-next
description: >
  按状态推进 8 阶段工作流到下一阶段。触发：下一步、next、继续推进。
---

# /tw:workflow-next — 驱动下一步

## 职责
根据 `current_stage` 调用对应的阶段命令，其余编排交给该阶段分发器。

## 步骤
1. 读 state；若 `current_stage==9` 提示已完成。
2. 若该阶段域包 slot `status=stub`，告警并停止推进（不绕过）。
3. 映射到命令：1→business-context … 8→wiki-feedback；打印并引导用户执行对应 `/tw:<cmd>`。
4. 状态推进只由阶段 Exit Gate 完成，本命令不写 state。
