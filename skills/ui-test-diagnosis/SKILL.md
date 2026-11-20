---
name: ui-test-diagnosis
description: >
  失败五分类诊断与归因。触发：诊断、调试失败、为什么失败。
---

# /tw:ui-test-diagnosis — 失败诊断

## 职责
按五分类归因失败测试：超时 / 定位符 / 值不符 / 环境 / 产品缺陷。

## 步骤
1. 读失败现场（`paths.screenshot_dir` 下 .png + .html）与 `stage5_verify.log`。
2. 按断言三维字段自动归因：`timeout` → 脚本/环境；值不对 → 产品缺陷；C 类 → 仅告警。
3. 若 pack 声明 `auxiliary.failure-taxonomy`，读该 file 补充分类细节；否则只用通用五分类表。
4. 归因为定位符/断言不符且缺 DOM 事实 → 调 `/tw:dump-page` 按需补采单页。
5. 输出归因结论 + 证据位置 + 建议动作；禁止直接放宽断言。
