---
name: ui-test-extend
description: >
  基于已开发完成的用例派生新场景。触发：派生用例、扩展用例、extend。
---

# /tw:ui-test-extend — 派生新场景

## 职责
从已实现用例派生新场景，不重走整条 8 阶段流程。

## 步骤
1. 定位已完成 feature 的 `stage1_cases.json` 与用例文件；中英双语并行查重。
2. 按 case-expansion-protocol 做三路依据与派生；新场景挂到同一 feature 的 cases 数组（新 id）。
3. 只补差异步骤，不复制整条用例；`evidence_level` 不得为 assumed。
4. 更新 stage1_cases.json / .md 并运行校验器。
