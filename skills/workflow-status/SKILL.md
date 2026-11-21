---
name: workflow-status
description: >
  只读查看 8 阶段工作流进度。触发：状态、进度、status。
---

# /tw:workflow-status — 工作流状态

## 职责
只读展示 `.claude/workflows/.current` 指向 feature 的阶段状态、完成度、待确认项。禁止写任何状态文件。

## 步骤
1. 读 `.current` → feature；读 `state.json`。
2. 按 stage-registry 的 8 槽位逐条打印 status / human_intervention / review_needed。
3. 打印 `current_stage` 与下一个待执行命令。
4. 在宿主项目根运行 `python3 "<插件根>/tw/tools/validate_workflow.py" --workflows-dir .claude/workflows` 展示是否有告警。插件根为本 SKILL.md 所在目录的上两级。
