# 录制工作流阶段 4：执行并修复（playwright-python 域）

## 目标
完成录制工作流第 4 阶段的栈相关做法。

## 前置输入
从磁盘重读上游产出；缺文件即停。

## 步骤
### 4-0. 前置检查
确认输入齐全。
### 4-a. 依录制协议执行（真相源 record gate-protocol.md §7 阶段 4）
- 7 轮探查-修复循环，归因逻辑同 `tw/protocols/stage-registry.md §6.4`；归因为环境问题 / 真实 bug → **立即停止报告，不改脚本绕过**（改了就是假绿）。
- `--full` 安全阀 2 与确定性处理 4 见 record gate-protocol.md §5.4；状态按 record-driven/protocols/state-protocol.md §3。

## 产出要求
按 workflow.yaml.artifacts.4 写文件。

## 审查门判据
按 workflow.yaml 的 review_gate 执行。

## Exit Gate 输入
- 产出物：见 artifacts.4
- 坑点候选：无新增则显式写「本阶段无新增坑点」。
