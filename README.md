# TapWitness（见信）

面向 **UI 自动化测试（UI automation / E2E testing）** 的 Claude Code 插件，用于自动化测试用例开发、UI 回归测试与端到端验证。

它把用例开发从「凭经验写脚本」变成一条可复用、可核验的流水线：8 个阶段逐段推进，每阶段必须通过 Exit Gate 才能进入下一阶段，状态写在磁盘上，跨会话可恢复。技术栈差异由**域包**吸收（Playwright / Appium / Airtest），项目差异由 **profile** 吸收，命令前缀固定为 `/tw:*`，换技术栈不用换命令。另提供**录制驱动**工作流：手工跑通一次流程，即可派生整套用例。

## 快速开始

```bash
claude plugin marketplace add penghang1223/tapwitness-ui-automation
claude plugin install tw@tw-marketplace
```

新开会话后 `/tw:` 下应可见 31 个命令。第一次接入项目，最小可跑示例：

```text
/tw:project-scan          # 扫描项目，生成 profile 与脚手架
/tw:new-feature login     # 建立 8 阶段工作流
/tw:business-context      # 阶段 1：业务知识与三道门
/tw:workflow-next         # 按 Exit Gate 推进到下一阶段
```

完整流程、自动推进与录制驱动见下方[使用教程](#使用教程)。

## 两条工作流

| | 8 阶段 | 录制驱动 |
|---|---|---|
| 适用 | 需求明确、从零建用例 | 已能手工跑通一条流程 |
| 入口 | `/tw:new-feature` | `/tw:record-feature` |
| 阶段 | 8：业务知识 → 数据 → 断言 → 用例 → 验证 → E2E → 报告 → 知识反哺 | 5：录制 → 用例生成 → 开发 → 执行 → 审查 |
| 状态文件 | `.claude/workflows/<feature>/state.json` | `.claude/record-workflows/<feature>/record_state.json` |

两者刻意零耦合，各自独立的协议、状态机与看板。状态文件是唯一真相源，`/tw:continue` 从 `.current` 恢复；阶段中发现的坑点按三层路由回流到域包知识库。

## 使用教程

### 第 0 步：接入项目（一次性）

```text
/tw:project-scan
```

扫描宿主项目的技术栈，生成 `.claude/project_profile.md` 与子目录脚手架（`.claude/workflows/`、`.claude/record-workflows/`、看板、`tw_feedback.md`、`CLAUDE.md` 中的 TW 章节）。域包由 `tw/packs/*/pack.yaml` 注册表打分判定，推荐结果需你确认；缺 `CLAUDE.md` 时先执行 `/init`。profile 不记明文密码，只记配置位置与所需环境变量。

### 工作流 A：从零开发（8 阶段）

```text
/tw:new-feature login         # 建 feature（kebab-case），初始化 state.json、.current、看板
/tw:business-context          # 阶段 1：业务知识召回，逐道确认需求背景与用例清单
/tw:ui-test-data              # 阶段 2：测试数据构造
/tw:ui-test-assertion         # 阶段 3：断言设计与校验点
/tw:ui-test-case              # 阶段 4：用例开发 / 页面对象
/tw:verify                    # 阶段 5：本地验证、探查修复循环
/tw:ui-test-e2e               # 阶段 6：端到端 / 全量回归
/tw:report                    # 阶段 7：开发汇报与覆盖率
/tw:wiki-feedback             # 阶段 8：知识反哺，写回知识库
```

每阶段结束走 **Exit Gate**：产物齐备且校验器 0 ERROR 才允许推进，状态由 Gate 写入 `state.json`，其他命令不写状态。手动推进时用 `/tw:workflow-next` 读取 `current_stage` 并告诉你下一条该执行的阶段命令。

按需要选择推进方式：

```text
/tw:auto login                # 半自动：阶段 1/3/4/5 出口暂停，展示 [Enter]/[edit]/[skip]/[exit] 审查门
/tw:auto-full login           # 全自动：无暂停；阶段 5 七轮验证用尽或任一校验器 ERROR 即停止报告
/tw:continue                  # 按 state.mode 从暂停点恢复，不重跑已完成阶段
/tw:workflow-status           # 只读查看阶段状态、完成度、待确认项与下一个命令
/tw:workflow-bypass 3 "理由"  # 跳过阶段 2（跳过的是目标阶段 -1），写 bypasses 留痕
```

跳过阶段会置 `status=skipped` 并记录 `human_intervention`，校验器会对账 `bypasses ↔ skipped`，不留痕的跳阶段不会被接受。

阶段产物与进度落在 `.claude/workflows/<feature>/state.json` 和 `dashboard.md`；`.claude/workflows/.current` 记住当前 feature，换会话、换机器拉到同一目录即可接着跑。

### 工作流 B：录制驱动（5 阶段）

```text
/tw:record-feature login      # 建录制 feature 与 record_state.json
/tw:record-capture            # 阶段 1：录制主流程（1e 人工核对录制结果）
/tw:record-casegen --single   # 阶段 2：拆解录制、派生用例
/tw:record-dev                # 阶段 3：写用例代码（3a plan）
/tw:record-run                # 阶段 4：执行并修复（最多 7 轮）
/tw:record-review             # 阶段 5：独立审核与用例对账
```

```text
/tw:record-auto login         # 半自动：在 1e / 2 / 3a / 5 暂停等你确认
/tw:record-auto login --full  # 全自动：遇证据 degraded、环境/真实 bug、校验器 ERROR 即停并报告
/tw:record-status             # 查看录制进度
```

状态在 `.claude/record-workflows/<feature>/record_state.json`，与 8 阶段工作流互不干扰。`/tw:record` 是独立录制工具，不进状态机。

### 辅助命令

| 场景 | 命令 |
|---|---|
| 抓取页面证据 | `/tw:dump-page` |
| 失败归因诊断 | `/tw:ui-test-diagnosis` |
| 派生新场景 | `/tw:ui-test-extend` |
| 提交域层坑点 | `/tw:feedback` |
| 运行环境体检 | `/tw:env-setup` |
| 移动端 MCP 配置 | `/tw:setup-mcp` |

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
- [验收套件说明](tests/README.md)：`python3 tests/run_acceptance.py --official`（含官方 CLI 冒烟与真实会话执行）

## 反馈

在宿主项目执行 `/tw:feedback`，坑点先写入 `.claude/tw_feedback.md`，再自动提交为 Issue 到本仓库：内容按白名单字段脱敏（绝对路径、URL、邮箱、凭据不进入公开 Issue）后经 `gh issue create` 提交，打 `tw-feedback` 标签，成功回写队列状态 `已提交(Issue #N,<日期>)` 并写入去重记录。

- 前置：本机安装并登录 GitHub CLI（`gh auth login`）；对公开仓库开 Issue 不需要额外权限。
- 失败（未装 `gh` / 未登录 / 网络）：反馈**保留在本地队列不丢失**，脚本打印预填链接供人工提交。
- 只预览不提交：`python3 <插件根>/tw/tools/submit_feedback.py --dry-run`；关闭自动提交：把 profile 的 `feedback_channel.auto_submit` 设为 `false`。
- 也可直接手动新建：[反馈表单](https://github.com/penghang1223/tapwitness-ui-automation/issues/new?template=tw-feedback.yml)。

## License

[AGPL-3.0](LICENSE) © 2026 TapWitness Maintainers。修改本框架并通过网络提供服务时，需按 §13 向使用者提供对应源码。
