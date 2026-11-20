---
name: feedback
description: >
  把域层坑点写入项目待提交队列，并自动向框架仓库提交 Issue。触发：反馈、提交坑点、feedback。
---

# /tw:feedback — 域层反馈提交

## 职责
把域层坑点追加到 `.claude/tw_feedback.md` 待提交队列，并**自动向框架仓库提交 Issue**：
`https://github.com/penghang1223/tapwitness-ui-automation/issues/new?template=tw-feedback.yml`

反馈目标由 `feedback_channel.issue_repo` 指定，默认是 `penghang1223/tapwitness-ui-automation`。

## 步骤
0. **去重**：读 `tw/protocols/feedback_absorbed.json`（框架已吸收）与
   `.claude/tw_feedback_submitted.json`（本项目已提交），用「来源项目 + 来源 feature + 现象摘要」
   做唯一键；已吸收 / 已入队 / 已提交 → 跳过并说明。
1. 定位队列文件 `.claude/tw_feedback.md`（`feedback_channel` 指向）；不存在则建表头。
2. 追加行：`| 日期 | 阶段 | 现象 | 根因 | 对策 | 适用平台 | 来源 feature | 待提交 |`。
3. 打印队列计数：`✓ 域层坑点已入队 .claude/tw_feedback.md（当前队列 N 条待提交）`。
4. **自动提交**（`feedback_channel.auto_submit: false` 时跳过）：
   ```
   python3 <插件根>/tw/tools/submit_feedback.py --project-root <宿主项目根> --yes
   ```
   `<插件根>` = 本 SKILL.md 所在目录的上两级（`skills/feedback/SKILL.md` → 插件根）；
   脚本内部路径由 `__file__` 推导，无需配置环境变量。
   - 脚本按白名单字段构造正文并脱敏（绝对路径 / URL / 邮箱 / 凭据一律不进公开 Issue），
     去重后调用 `gh issue create` 提交到 `feedback_channel.issue_repo`，打 `tw-feedback` 标签。
   - 成功：队列状态改为 `已提交(Issue #N,<日期>)`，写入 `.claude/tw_feedback_submitted.json`，
     打印 Issue URL。
   - 失败（未装 gh / 未登录 / 网络异常）：**反馈保留在本地队列，不丢失**；脚本打印
     预填 Issue 链接作为人工降级，并说明原因。
   - 只预览不提交：去掉 `--yes`（脚本默认即 `--dry-run`）。
5. 维护者合入域包后写 `feedback_absorbed.json` 并涨版本。

## 纪律
- 提交到公开仓库的内容必须脱敏；凭据、内网地址、客户数据不得写入队列。
- 域包正文不得写状态文件；坑点三层路由见 `tw/protocols/gate-protocol.md` §4.3
  与 `tw/protocols/stage-registry.md` §6。
- 禁止直接改 plugin 缓存内的域包文件（升级会丢失）。
