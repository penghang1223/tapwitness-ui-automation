# 录制工作流阶段 2：生成用例（playwright-python 域）

## 目标
完成录制工作流第 2 阶段的栈相关做法。

## 前置输入
从磁盘重读上游产出；缺文件即停。

## 步骤
### 2-0. 前置检查
确认输入齐全。
### 2-a. 依录制协议执行（真相源 record gate-protocol.md §7 阶段 2）
- 先定 `full`（默认）/ `single`（cases 长度 1、expansion_mode="single"）→ 2-0 前置检查 → 2a 拆解 → 2b 三路依据（KB > DOM > 查重）→ 2c 派生 → 2d 挂断言 → 2e `data_plan` → 2f 双格式 → 2g 强制审查门。
- 禁止凭空生成 / full·single / 三路依据 / 降级策略见 `tw/protocols/case-expansion-protocol.md §1/§2/§3`；三路皆空**不编造**，只出正向变体，`evidence.degraded=true`，md 顶部显式降级说明。
- `--full` 安全阀 1 见 record gate-protocol.md §5.4。

## 产出要求
按 workflow.yaml.artifacts.2 写文件。

## 审查门判据
按 workflow.yaml 的 review_gate 执行。

## Exit Gate 输入
- 产出物：见 artifacts.2
- 坑点候选：无新增则显式写「本阶段无新增坑点」。
