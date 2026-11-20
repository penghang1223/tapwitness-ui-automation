# 录制工作流阶段 5：代码审核（playwright-python 域）

## 目标
完成录制工作流第 5 阶段的栈相关做法。

## 前置输入
从磁盘重读上游产出；缺文件即停。

## 步骤
### 5-0. 前置检查
确认输入齐全。
### 5-a. 依录制协议执行（真相源 record gate-protocol.md §7 阶段 5）
- **必须拉起独立审核子代理**（subagent），不能同一上下文自审；审核对象是跑通后存活的最终代码（含阶段 4 改动）。
- 五类检查：① PO 规范 ② 断言覆盖（对 `stage2_cases.json` **逐条对账**，含数据准备/清理）③ 域包坑点扫描 ④ 脆弱定位符 ⑤ 过度设计（只覆盖「多写」，全部建议级、永不判阻塞）。清单见 `workflows/record-driven/references/code_review_checklist.md`。
- 结论「需修」→ 回拨阶段 3、`rework_round += 1`（record state-protocol.md §3）；审核链路本身失败置 `5_review=failed`、停 5、不回拨不计数。
- 本门 mandatory，四选项 `Enter/fix/accept/exit` 见 §4.4。

## 产出要求
按 workflow.yaml.artifacts.5 写文件。

## 审查门判据
按 workflow.yaml 的 review_gate 执行。

## Exit Gate 输入
- 产出物：见 artifacts.5
- 坑点候选：无新增则显式写「本阶段无新增坑点」。
