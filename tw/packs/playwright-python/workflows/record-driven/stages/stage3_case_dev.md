# 录制工作流阶段 3：开发用例（playwright-python 域）

## 目标
完成录制工作流第 3 阶段的栈相关做法。

## 前置输入
从磁盘重读上游产出；缺文件即停。

## 步骤
### 3-0. 前置检查
确认输入齐全。
### 3-a. 依录制协议执行（真相源 record gate-protocol.md §7 阶段 3）
- 3-pre DOM 准备（缓存/存量 PO 命中免采）→ **3a plan 审查**（定位符证据为可核验三元组：证据位置/验证了什么/易失效项的验证动作；**steps→方法覆盖表**逐条有归属，single 必填）→ 3b 编码 → 3c `stage3_files.md`。
- 3a 属阶段内部子步骤门，暂停机制见 §4.4；证据落盘见 `tw/protocols/dump-artifact-protocol.md §1/§2`。

## 产出要求
按 workflow.yaml.artifacts.3 写文件。

## 审查门判据
按 workflow.yaml 的 review_gate 执行。

## Exit Gate 输入
- 产出物：见 artifacts.3
- 坑点候选：无新增则显式写「本阶段无新增坑点」。
