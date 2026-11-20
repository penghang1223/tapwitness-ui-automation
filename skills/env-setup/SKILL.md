---
name: env-setup
description: >
  检查并补齐测试运行环境（依赖/conftest/驱动）。触发：环境、env setup、装依赖。
---

# /tw:env-setup — 环境体检与补齐

## 职责
按域包 `auxiliary.env-setup` 指向的实现做 E1–E8 环境体检。

## 步骤
1. 解析 profile 与 pack；若 pack 未声明 `auxiliary.env-setup`，停止并提示手工准备，不跨包借用。
2. 读 `auxiliary.env-setup.file` 指向的清单，逐项检查 E1–E8。
3. 补齐缺失项；失败现场目录用 `paths.screenshot_dir`，并在其 conftest 钩子里加入 gitignore。
4. 输出体检报告：通过 / 缺失 / 需人工。
