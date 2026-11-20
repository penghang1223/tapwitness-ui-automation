# TapWitness（见信）

面向 **UI 自动化测试（UI automation / E2E testing）** 的 Claude Code 插件，用于自动化测试用例开发、UI 回归测试与端到端验证。

它把用例开发从「凭经验写脚本」变成一条可复用、可核验的流水线：8 个阶段逐段推进，每阶段必须通过 Exit Gate 才能进入下一阶段，状态写在磁盘上，跨会话可恢复。技术栈差异由**域包**吸收（Playwright / Appium / Airtest），项目差异由 **profile** 吸收，命令前缀固定为 `/tw:*`，换技术栈不用换命令。另提供**录制驱动**工作流：手工跑通一次流程，即可派生整套用例。

## 快速开始

```bash
claude plugin marketplace add penghang1223/tapwitness-ui-automation
claude plugin install tw@tw-marketplace
```

新开会话后 `/tw:` 下应可见 31 个命令。第一次接入项目：

```text
/tw:project-scan          # 扫描项目，生成 profile 与脚手架
/tw:new-feature login     # 建立 8 阶段工作流
/tw:business-context      # 阶段 1：业务知识与三道门
/tw:workflow-next         # 按 Exit Gate 推进到下一阶段
```

`/tw:auto <name>` 半自动推进（阶段 1/3/4/5 暂停），`/tw:auto-full <name>` 全自动；`/tw:workflow-status` 随时查看进度与看板。

已能手工跑通一条流程时走录制驱动：`/tw:record-feature <name>` → `/tw:record-capture` → `/tw:record-casegen --single` → `/tw:record-dev` → `/tw:record-run` → `/tw:record-review`。

## 两条工作流

| | 8 阶段 | 录制驱动 |
|---|---|---|
| 入口 | `/tw:new-feature` | `/tw:record-feature` |
| 阶段 | 8：业务知识 → 数据 → 断言 → 用例 → 验证 → E2E → 报告 → 知识反哺 | 5：录制 → 用例生成 → 开发 → 执行 → 审查 |
| 状态文件 | `.claude/workflows/<feature>/state.json` | `.claude/record-workflows/<feature>/record_state.json` |

两者刻意零耦合，各自独立的协议、状态机与看板。状态文件是唯一真相源，`/tw:continue` 从 `.current` 恢复；阶段中发现的坑点按三层路由回流到域包知识库。

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

## 文档

- [安装与发布](docs/install.md) · [使用教程](docs/使用教程.md) · [架构设计方案（重建规格书）](docs/架构设计方案.md)
- [验收套件说明](tests/README.md)：`python3 tests/run_acceptance.py --official`（56 项，含官方 CLI 冒烟与真实会话执行）

## License

[AGPL-3.0](LICENSE) © 2026 TapWitness Maintainers。修改本框架并通过网络提供服务时，需按 §13 向使用者提供对应源码。
