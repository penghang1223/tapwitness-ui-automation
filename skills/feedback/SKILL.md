---
name: feedback
description: >
  把域层坑点写入项目待提交队列。触发：反馈、提交坑点、feedback。
---

# /tw:feedback — 域层反馈提交

## 职责
把域层坑点追加到 `.claude/tw_feedback.md` 待提交队列。

## 步骤
0. **去重**：读 `tw/protocols/feedback_absorbed.json`，用「来源项目 + 来源 feature + 现象摘要」做唯一键；已吸收 or 已入队 → 跳过并说明。
1. 定位队列文件 `.claude/tw_feedback.md`（`feedback_channel` 指向）；不存在则建表头。
2. 追加行：`| 日期 | 阶段 | 现象 | 根因 | 对策 | 适用平台 | 来源 feature | 待提交 |`。
3. 打印队列计数：`✓ 域层坑点已入队 .claude/tw_feedback.md（当前队列 N 条待提交）`。
4. 按 `feedback_channel.issue_url` 给出预填 Issue 链接；维护者合入域包后写 `feedback_absorbed.json` 并涨版本。
