# Android Airtest 域坑点库

> 每条对策必须是「判据 + 动作」；来源项目用于溯源。

| 日期 | 阶段 | 现象 | 根因 | 对策 | 适用平台 | 来源项目 |
|---|---|---|---|---|---|---|
| 2026-10-20 | 4 用例开发 | 页面加载慢导致定位符偶发失败 | 断言前未等元素可见 | 先用 wait_condition=element_present 再断言，禁止 sleep | android | example-project |
