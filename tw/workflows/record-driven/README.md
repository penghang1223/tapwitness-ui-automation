# 录制驱动工作流

这里定义录制驱动工作流本身。

| 位置 | 职责 |
|---|---|
| `workflow.yaml` | 定义阶段、产物、暂停点和适用域包 |
| `protocols/` | 定义录制状态和门禁规则 |
| `templates/` | 提供录制状态和看板模板 |
| `tools/` | 生成录制分发器并校验录制工作流 |

技术栈相关的录制步骤放在域包的 `workflows/record-driven/` 中。例如 [Playwright 录制阶段](../../packs/playwright-python/workflows/record-driven/stages/)负责该栈的录制、用例派生和执行做法。

`workflow.yaml` 中的 `pack_path` 和域包级 `references` 相对激活域包根目录解析。共用协议引用按 [架构设计方案 §5.6](../../../docs/架构设计方案.md) 解析。

录制状态保存在宿主项目的 `.claude/record-workflows/`；8 阶段状态保存在 `.claude/workflows/`。有关共用产物校验和反馈工具的范围，见 [工具目录说明](../../tools/README.md)。
