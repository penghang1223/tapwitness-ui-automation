---
name: record
description: >
  单次录制代码骨架，不进状态机。触发：录一段、单次录制、record。
---

# /tw:record — 单次录制工具

## 职责
调用域包 `auxiliary.record` 指向的实现，录一条流程骨架，不创建 record_state.json。

## 步骤
1. 解析 profile 与 pack；若 pack 未声明 `auxiliary.record`，明确拒绝并提示不支持（录制唯一支持 playwright-python）。
2. 读 `run.base_url` 与 `run.viewport`；codegen 命令必须带 `--viewport-size <viewport>`，缺省不得回落 1280×720。
3. 按 record.md 后处理：语法检查 / 引号转义 / POM 生成 / 自动复用已有登录方法（auth fixture > LoginPage > api_login，无需人工确认）/ 补充缺失操作 / `storage_state.json` 加入 gitignore。
4. 不执行 `--with-assertion` 段（断言归录制阶段 2）。
