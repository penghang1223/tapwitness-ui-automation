# 工具目录

本目录同时提供 8 阶段工作流工具和两条工作流共用的工具。脚本位于插件目录中，宿主项目调用时应使用插件根目录定位脚本，并以宿主项目根目录作为工作目录。

| 脚本 | 适用范围 | 作用 |
|---|---|---|
| `gen_dispatchers.py` | 8 阶段 | 生成阶段 Skill，`--check` 检查漂移 |
| `validate_workflow.py` | 8 阶段与域包 | 检查 8 阶段状态、域包和 profile / dump 契约 |
| `validate_artifacts.py` | 两条工作流 | 检查指定阶段的用例、断言和引用 |
| `gen_handoff.py` | 两条工作流 | 为宿主项目生成 HANDOFF 命令映射 |
| `submit_feedback.py` | 两条工作流 | 预览、提交和核对域层反馈 |

录制驱动工作流的分发器生成器和状态校验器位于 [录制驱动工具目录](../workflows/record-driven/tools/)。两条工作流的状态校验器各自独立。

示例中把 `<插件根>` 和 `<项目根>` 替换为实际路径。

```bash
python3 "<插件根>/tw/tools/validate_workflow.py" --workflows-dir "<项目根>/.claude/workflows"
python3 "<插件根>/tw/tools/validate_artifacts.py" --workflow 8-stage --feature-dir "<项目根>/.claude/workflows/<feature>" --stage 1
python3 "<插件根>/tw/tools/validate_artifacts.py" --workflow record-driven --feature-dir "<项目根>/.claude/record-workflows/<feature>" --stage 2
python3 "<插件根>/tw/tools/gen_handoff.py" "<项目根>"
```
