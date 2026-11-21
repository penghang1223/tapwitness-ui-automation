---
name: new-feature
description: >
  新建 8 阶段工作流 feature，建目录/state/.current/dashboard。触发：新功能、新特性、new feature。
---

# /tw:new-feature — 新建功能工作流

## 职责
创建 8 阶段工作流的 feature 目录与初始状态。是唯一允许初始化 state.json 的入口。

## 步骤
1. 校验 feature 名（kebab-case，与目录名一致），已存在则拒绝。
2. 解析 profile（见 gate-protocol §3）；缺 profile 引导 `/tw:project-scan`。
3. 在 `.claude/workflows/<feature>/` 建目录；从 `tw/templates/_template/state.json` 复制并填 `feature` / `created`。
4. 写 `.claude/workflows/.current`（仅 feature 名，UTF-8）。
5. 更新 `.claude/workflows/dashboard.md` 头部计数，登记新 feature 到「未启动」桶（阶段 1 已 in_progress 则入「进行中」）。
6. 在宿主项目根运行 `python3 "<插件根>/tw/tools/validate_workflow.py" --workflows-dir .claude/workflows`，0 ERROR 才算完成。

## 边界
本命令只初始化，不做业务召回。下一步 `/tw:business-context`。

本 plugin 根目录 tw/ 相对本 SKILL.md 为 ../../tw/；路径不确定就 Glob 搜 **/tw/protocols/gate-protocol.md。
