---
name: dump-page
description: >
  抓 DOM/截图/a11y 树落盘到 page_cache。触发：抓页面、dump page、抓 DOM、截图证据。
---

# /tw:dump-page — 页面证据抓取

## 职责
按域包 `auxiliary.dump-page` 指向的实现抓取页面证据。位置/文件名/manifest 以 dump-artifact-protocol 为唯一真相源。

## 步骤
1. 检查 pack 是否声明 `auxiliary.dump-page`；未声明 → 按栈给通用兜底并说明可能不完整。
2. 读该能力键的 `file`，按其实现执行单页 / 批量 / 按需抓取。
3. 证据写入 `<feature>/page_cache/<slug>/`：dom.html 或 ui.xml、screenshot.png、可选 a11y_tree.txt；同步更新 manifest.json。
4. 消费顺序固定：screenshot → a11y_tree → 结构树。
