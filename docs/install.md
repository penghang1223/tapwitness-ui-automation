# 安装与发布 — TapWitness（见信）

## 安装
```bash
claude plugin marketplace add penghang1223/tapwitness-ui-automation
claude plugin install tw@tw-marketplace
```
新开会话后 `/tw:` 应可见 31 个命令。

本地开发可用目录市场：`claude plugin marketplace add <本仓库路径>` 后
`claude plugin install tw@tw-marketplace`。

## 发布
1. 改 `.claude-plugin/plugin.json` 的 `version`（唯一发布开关）；
2. git tag 与版本一致（`claude plugin tag`）；
3. 用户侧 `claude plugin update tw@tw-marketplace` + 重开会话生效。

## 可发现性：让别人搜到本框架
前提：项目必须**公开发布**。本仓库已发布在
`https://github.com/penghang1223/tapwitness-ui-automation`（公开）。
搜索引擎与 GitHub 索引需要时间；只有本地文件时，任何人搜任何关键词都搜不到。

发布清单（✅ 已完成 / ⬜ 仍待做）：
- ✅ 公开 GitHub 仓库，仓库名带领域词 `tapwitness-ui-automation`
  （单用 `TW` 或纯造词不会被领域词命中）。
- ✅ 仓库 Description 中英双语，含 `UI 自动化测试 / UI automation / E2E testing`。
- ✅ Topics：`ui-automation`、`e2e-testing`、`test-automation`、`playwright`、
  `appium`、`airtest`、`claude-code`、`claude-code-plugin`、`qa`。
- ✅ `marketplace.json` 含领域词与 `category: testing`；README 首段与
  「适用场景与关键词」段铺中英检索词。
- ✅ 远程安装链路实测通过（隔离 `CLAUDE_CONFIG_DIR` 下执行上面两条安装命令：
  GitHub HTTPS clone → `install tw@tw-marketplace` → `enabled: true, v1.31.0`）。
- ⬜ 提交到 Claude 插件目录站收录。
- ⬜ 至少发一篇中文介绍文章（掘金 / 知乎 / 公众号）链接回仓库——
  长尾词的实际排名载体是文章与内容站，不是仓库页面本身。
- ⬜ `claude plugin tag` 与 version 对齐的 git tag。

现实预期：
- 搜 `UI 自动化` / `ui automation` 这类大词：被 Selenium、Playwright、
  Appium、UiPath 与大量教程占据，新项目基本进不了前列。
- 搜长尾组合词（`Claude Code UI 自动化`、`Playwright 用例工作流`、
  `UI 自动化 门禁 状态机`）：靠上述元数据 + 文章可以命中。
- 搜品牌名 `TapWitness`：合成造词零同名，命中率最高。品牌名决定「认出你」，
  副标题与 description 里的领域词决定「被领域词搜到」。

### 命名评估实测（2026-11-20）
- `"TapWitness"` 精确检索：**零同名项目**，但未被收录前搜索引擎会拆词兜底，
  返回 The Witness 游戏 / Witness HQ / TapVisit 等噪声；需仓库页 + 一篇外链文章压住。
- `witness` 词根在 AI 编码 agent 领域已有语义邻居：`taskwitness`（npm，
  「No evidence = no green check」）、`witness-recorder`（npm）、
  `Witness`（CNCF in-toto）。无同名撞车，但语义区分度低于预期。
- 带 `UI automation / Claude Code` 检索时，结果全为 Chrome MCP 教程、
  Momentic、webapp-testing skill、computer use 文档等内容站，
  印证领域词位置由内容与外链决定，与品牌名无关。

## 项目接手
在宿主项目跑 `/tw:project-scan` 生成 `.claude/project_profile.md` 与脚手架；
缺 CLAUDE.md 先 `/init`。profile 禁明文密码。

## 反馈渠道

仓库 Issues 已启用，并配好 `tw-feedback` 标签与
`.github/ISSUE_TEMPLATE/tw-feedback.yml` 结构化表单。
宿主项目里执行 `/tw:feedback` 会先预览坑点，用户确认后通过 `gh issue create` 提交；
使用者需自行安装并登录 GitHub CLI，未登录时反馈保留在本地队列不丢失。
维护者合入域包后更新 `tw/protocols/feedback_absorbed.json` 并涨版本。

## FAQ
- 命令名不变，做法由域包吸收；换栈只需换 pack。
- 状态文件是唯一真相源，跨会话从 `.current` 恢复。
- 两条工作流零耦合，看板与状态目录互不干扰。
- 反馈默认预览，确认后提交；设 `feedback_channel.auto_submit: false` 可保持预览模式。
