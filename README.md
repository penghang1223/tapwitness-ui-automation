# TapWitness（点证）— UI 自动化测试工作流框架

> **每一次点击，都要留下可核验的证据。**
> `Tap`（界面交互）+ `Witness`（证据）= `TW`。命令前缀 `/tw:*`、插件标识 `tw` 保持不变。

TapWitness 是一个 Claude Code plugin，把 **UI 自动化测试（UI automation / E2E testing）** 做成跨项目、跨技术栈可复用的流程流水线：从业务知识、测试数据、断言设计，到测试用例开发、执行验证与回归，按 8 阶段状态机逐段推进，每阶段有 Exit Gate 门禁；另支持录制驱动（record & replay）生成用例。覆盖 Playwright、Appium、Airtest 等栈。
命令恒定（`/tw:*`），技术栈差异由**域包**吸收，项目差异由 **profile** 吸收。

## 名字与定位

| | |
|---|---|
| 中文名 | 点证（点击 + 取证） |
| 英文名 | TapWitness |
| 一句话 | 8 阶段 × 每阶段 Exit Gate，每个结论都要有可核验的证据 |
| 领域 | UI 自动化测试 / E2E testing / 测试用例工作流 |

品牌名负责「认出你」；「被领域词搜到」由仓库 Description、Topics、README 与介绍文章里的领域词负责——纯造词本身不提供语义信号。命名评估与发布清单见 [docs/install.md](docs/install.md)。

## 适用场景与关键词
面向需要**自动化测试用例开发、UI 回归测试、端到端 E2E 测试**的团队。常见检索词：
`UI 自动化`、`UI 自动化测试`、`ui automation`、`E2E testing`、`自动化测试用例`、
`Playwright`、`Appium`、`Airtest`、`Claude Code 插件`、`测试用例工作流`、`Exit Gate 门禁`、
`TapWitness`、`点证`。

## 三层架构
- **L0 流程内核**：`tw/protocols/` + `tw/tools/` + `tw/templates/` + 31 个命令。
- **L1 域包**：`tw/packs/<pack_id>/`，每栈一本 8 阶段作业手册 + 坑点库 + 工具实现。
- **L2 项目适配**：宿主项目 `.claude/project_profile.md` / `.claude/profiles/*.md`。

## 命令（31）
8 阶段工作流 22 个：`new-feature`、`business-context`、`ui-test-data`、`ui-test-assertion`、
`ui-test-case`、`verify`、`ui-test-e2e`、`report`、`wiki-feedback`、`workflow-status`、
`workflow-next`、`workflow-bypass`、`auto`、`auto-full`、`continue`、`project-scan`、
`env-setup`、`feedback`、`dump-page`、`ui-test-diagnosis`、`setup-mcp`、`ui-test-extend`。
录制驱动工作流 9 个：`record-feature`、`record-capture`、`record-casegen`、`record-dev`、
`record-run`、`record-review`、`record-auto`、`record-status`、`record`（独立工具，不进状态机）。

## 域包
| 域包 | version | 录制 |
|---|---|---|
| playwright-python | 1.10.0 | 支持 |
| ios-appium | 1.3.0 | 未实现 |
| android-appium | 1.3.0 | 未实现 |
| android-airtest | 1.3.0 | 未实现 |

## 安装
```bash
claude plugin marketplace add penghang1223/tapwitness-ui-automation
claude plugin install tw@tw-marketplace
```
新开会话后 `/tw:` 应可见 31 个命令。

本地开发可用目录市场：`claude plugin marketplace add <本仓库路径>` 后
`claude plugin install tw@tw-marketplace`。
详见 [docs/install.md](docs/install.md)。教程见 [docs/使用教程.md](docs/使用教程.md)。
架构与重建规格见 [docs/架构设计方案.md](docs/架构设计方案.md)。

## 自检与验收
```bash
python3 tests/run_acceptance.py            # 51 项：静态契约 + §13 条款守护 + fixture + 反向破坏 + 状态流转
python3 tests/run_acceptance.py --quick    # 21 项：只跑静态契约
python3 tests/run_acceptance.py --official # 56 项：追加官方 CLI 冒烟与真实会话执行 slash 命令
```
覆盖 §12 Phase 0–8、§13 不变式与 §14 风险项（含域包正文不写状态文件的静态守护）；
`tests/README.md` 说明各用例与仍需人工验证的条目。

## License
**AGPL-3.0**（GNU Affero General Public License v3.0）— 全文见 [LICENSE](LICENSE)。
Copyright (c) 2026 TapWitness Maintainers。

AGPL-3.0 为强 copyleft 协议：修改本框架并**通过网络向用户提供服务**时，
需按 §13 向使用者提供对应源码；仅作为本地 Claude Code 插件使用不触发该义务。
