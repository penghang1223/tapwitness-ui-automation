# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这个仓库是什么

TapWitness（见信，`/tw:*` 前缀不变）是一个 **Claude Code 插件**（不是应用程序）：面向 UI 自动化 / E2E 测试用例开发的流程框架。产物是 Markdown 指令 + YAML/JSON 契约，由 31 个 `/tw:*` skill 编排执行。没有构建步骤、没有服务、没有数据库。Python 3.8+ 与 PyYAML 只用于校验器和生成器（其余仅用标准库）。

仓库内容全部用中文书写；新增正文、文档与诊断信息请保持中文。

`docs/架构设计方案.md` 是按章节编号组织的权威规格书（schema、不变式、风险）。出现歧义时，以该文档为准，而不是 README 措辞或 skill 正文。

## 命令

```bash
# 验收套件（宣布完成前必须跑）
python3 tests/run_acceptance.py            # 全套：静态契约 + 条款守护 + fixture + 反向破坏 + 状态流转模拟
python3 tests/run_acceptance.py --quick    # 只跑静态契约，快
python3 tests/run_acceptance.py --official # 追加 Claude Code CLI 冒烟（较慢，需要本机 claude CLI）

# 8 阶段状态机
python3 tw/tools/validate_workflow.py --workflows-dir .claude/workflows
python3 tw/tools/validate_workflow.py --check-pack [tw/packs/<id>] --strict
python3 tw/tools/validate_workflow.py --check-profile-contract
python3 tw/tools/validate_workflow.py --check-dump-contract

# 录制驱动状态机（独立校验器，绝不 import 另一个）
python3 tw/workflows/record-driven/tools/validate_record_workflow.py --check-workflow
python3 tw/workflows/record-driven/tools/validate_record_workflow.py --workflows-dir .claude/record-workflows

# 改模板后重新生成分发器（然后跑 --check）
python3 tw/tools/gen_dispatchers.py
python3 tw/tools/gen_dispatchers.py --check                 # 漂移/缺失时退出码 1
python3 tw/workflows/record-driven/tools/gen_record_dispatchers.py
python3 tw/workflows/record-driven/tools/gen_record_dispatchers.py --check
python3 tw/tools/gen_handoff.py <项目根> [--check|--stdout]

# 插件 manifest / 安装冒烟
claude plugin validate . --profile directory
claude plugin marketplace add <仓库路径> && claude plugin install tw@tw-marketplace
```

所有校验器的退出码约定：有 ERROR → 1；只有 WARNING → 仅 `--strict` 下为 1。成功输出里含有 `0 ERROR / 0 WARNING` 字样，所以**不要用子串统计诊断行**——按行首 `ERROR`/`WARNING` 正则匹配（见 `tests/README.md`）。

## 架构

三层，依赖方向单向：

- **L0 流程内核** —— `skills/`（31 个分发器）、`tw/protocols/`、`tw/tools/`、`tw/templates/`。与技术栈无关。
- **L1 域包** —— `tw/packs/<pack_id>/`（playwright-python、ios-appium、android-appium、android-airtest）。每个域包是一本 8 阶段作业手册 + 坑点库 + 工具实现。域包可以按章节号引用 L0 协议；**不得**写状态文件。
- **L2 项目适配** —— 生成在**宿主项目**里：`.claude/project_profile.md`、`.claude/profiles/<subsystem>.md`。不含框架逻辑。

**两条刻意解耦的工作流**，禁止合并，也不要抽象出统一状态机：

| | 8 阶段 | 录制驱动 |
|---|---|---|
| 入口 | `/tw:new-feature` | `/tw:record-feature` |
| 阶段 | 8（`current_stage` 1–9） | 5（`current_stage` 1–6） |
| 状态 | `.claude/workflows/state.json` | `.claude/record-workflows/record_state.json` |
| 协议 | `tw/protocols/` | `tw/workflows/record-driven/protocols/` |
| 生成器 / 校验器 | `tw/tools/` | `tw/workflows/record-driven/tools/` |

共享的只有断言 / 用例派生 / dump 产物这几个方法论协议，且只是**文档级复用**。

**分发器骨架** —— 每个阶段 skill 只做五步：Gate Check → 解析 profile → 加载域包 → 执行域包阶段指令 → Exit Gate。Gate Check 的四分支、Exit Gate 五步、审查门三值模型、四套 mode 失败分支的真相源在 `tw/protocols/gate-protocol.md`；skill 只指向协议，不复述条款。录制驱动的对应文件在 `tw/workflows/record-driven/protocols/gate-protocol.md`。

**唯一写者** —— 只有 Exit Gate 能推进 `state.json` / `record_state.json` / `.current` / `dashboard.md`。域包阶段文件不得写它们。`state.json` 必须自洽：`current_stage` 等于第一个 status ∉ {done, skipped} 的阶段号（例外：`5_verify=failed` 回拨为 4）。

**生成 vs 手写** —— 8 个 8 阶段分发器和 5 个录制分发器由各自的生成器从单一模板 + `STAGES` 字典产出；其 `SKILL.md` 的 description 带 `[TW 阶段N]` / `[TW 录制阶段N]`，**不得手改**。其余入口 / 元命令 / 辅助 skill 为手写。

**能力键门控** —— skill 通过 `pack.yaml.auxiliary` 的键（`dump-page`、`failure-taxonomy`、`record`、`env-setup`、`setup-mcp`、`mcp-setup-guide`）判断功能是否可用，并读取键指向的 `file`。**禁止**在 skill 里硬编码 pack-id 白名单。

## 校验器强制的编辑规则

- 改生成的分发器 = 改生成器的 `STAGES`/模板，然后重新生成；`--check` 必须 PASS。
- 域包 `stages/`、`references/`、`tools/` 下的每个文件都必须在 `pack.yaml` 中声明；新增顶层目录要登记进 `validate_workflow.py` 的 `PACK_SCAN_DIRS` 或 `PACK_EXEMPT_DIRS`（C2R，WARNING，`--strict` 下失败）。
- 分发器与域包不得复述协议内容——只引用协议章节号。协议文件是唯一真相源。
- 域包阶段指令正文不得出现 `state.json`、`record_state.json`、`dashboard.md`、`.current`。
- Python 脚本：stdout/stderr 重配置为 UTF-8；路径用 `Path(__file__)` 推导；`yaml.safe_load` 结果做 `isinstance(dict)` 守卫；两个校验器**不得**互相 import。
- 冻结标识符（命令名、阶段键、产出文件名、状态目录、status/mode 枚举）见 `docs/架构设计方案.md` §3.4——改名会破坏存量接入项目。
- `plugin.json.version` 是唯一发布开关；涨版本时同步打同版本 git tag。README 的命令数与域包表必须与实际一致（验收套件会检查）。
- 运行时产物不得入库：`page_cache/`、`storage_state.json`、`.current`。

## 去哪里查

- `docs/架构设计方案.md` —— 完整规格：§3 契约、§4 运行模型、§5 schema、§6/§7 阶段纪律、§9 域包规则、§10 工具链、§13 不变式、§14 陷阱。
- `tw/protocols/*` —— 状态、门禁、阶段注册表、断言、用例派生、dump 产物协议。
- `tests/README.md` —— 套件覆盖了什么，以及**尤其重要的**：哪些仍需人工验证。不要把「仅人工可验」的条目当成已测。
