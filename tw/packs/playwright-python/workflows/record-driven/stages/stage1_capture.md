# 录制工作流阶段 1：录制（playwright-python 域）

## 目标
完成录制工作流第 1 阶段的栈相关做法。

## 前置输入
从磁盘重读上游产出；缺文件即停。

## 步骤
### 1-0. 前置检查
确认输入齐全。
### 1-a. 依录制协议执行（真相源 record gate-protocol.md §7 阶段 1）
- 1-0 依赖检查缺一即停；**只录一条正向主流程**，异常分支不录；codegen 带 `--viewport-size <run.viewport>`（缺省不得回落 1280×720）；后处理委托 `tools/record.md`（语法/引号/POM/自动复用已有登录方法/storage_state.json 加入 .gitignore）；`stage1_record.md` 登记流程描述与操作序列。
- **1e 操作序列人工核对**：逐条列序号/目标/值请用户确认无遗漏；single 模式无阶段 2 拆解兜底，**不可跳**。
- 1e 属阶段内部子步骤门，暂停机制见 §4.4（semi-auto 在此会停）；不执行 record.md 的 `--with-assertion` 段。

## 产出要求
按 workflow.yaml.artifacts.1 写文件。

## 审查门判据
按 workflow.yaml 的 review_gate 执行。

## Exit Gate 输入
- 产出物：见 artifacts.1
- 坑点候选：无新增则显式写「本阶段无新增坑点」。
