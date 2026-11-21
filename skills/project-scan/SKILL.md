---
name: project-scan
description: >
  项目接入唯一入口：扫描技术栈、生成 profile 与脚手架。触发：接入项目、扫描项目、project scan。
---

# /tw:project-scan — 项目接入扫描

## 职责
扫描宿主项目，生成/增量更新 `.claude/project_profile.md` 与子目录脚手架。域包注册表就是 `tw/packs/*/pack.yaml`，无需改 L0。

## 步骤
1. **分端**：混合子系统（同子系统含 web+app）逐端检测，输出「端 / 信号文件 / 命中内容 / 指向栈」。
2. **取信号 + 计分**：遍历每个 `pack.yaml.tech.platforms` + `tech.signals`。`deps_*` 命中 ×3；`files_any_of`（框架配置类 glob）×2；`dirs_any_of` ×1；`negative` 命中 ×(−5)。
3. **判定**：总分 <3 不成候选；negative 使总分 ≤0 直接排除；最高分唯一且 ≥3 → 推荐（须用户确认）；并列 → 列全部由用户选，不代选。
4. **无匹配**：有实质源码但候选全 <3 → 「存量项目但栈未注册」：列已注册域包后停止，不生成骨架。
5. **greenfield**：信号全 0 且仓库近乎空（无依赖清单/框架配置/测试目录，或源码文件 ≤10）→ 询问目标栈，标 `greenfield: true`。
6. **步骤 2.5 MCP 检测**：若域包声明 `auxiliary.mcp-setup-guide`，读该文档检测 MCP 安装；否则跳过。
7. **写脚手架**：`.claude/project_profile.md`、`.claude/profiles/<sub>.md`、`tw_feedback.md`、`workflows/` 与 `record-workflows/` 的 `_template`/`.current`/`.gitignore`/`dashboard.md`；CLAUDE.md 用 `<!-- tw:start -->` / `<!-- tw:end -->` 标记追加「TW 工作流」章节（缺 CLAUDE.md 提示 `/init`）；HANDOFF.md 调 `python3 "<插件根>/tw/tools/gen_handoff.py" "<项目根>"` 生成映射段。插件根为本 SKILL.md 所在目录的上两级。
8. **重扫**：检测类字段刷新；人工确认字段（`run.*` / `data_layer.*` / `kb.path` / `feedback_channel`）与正文默认保留，逐项展示 diff 由用户选。
9. 安全红线：`page_cache/`、`storage_state.json`、`.current` 写入 gitignore；profile 禁明文密码，只记 `data_layer.db_config.location` / `password_scheme` / `required_env`。
