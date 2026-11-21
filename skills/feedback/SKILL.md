---
name: feedback
description: >
  把域层坑点写入项目待提交队列，并预览和提交 Issue。触发：反馈、提交坑点、feedback。
---

# /tw:feedback — 域层反馈提交

## 职责
把域层坑点追加到 `.claude/tw_feedback.md` 待提交队列，预览后向框架仓库提交 Issue：
`https://github.com/penghang1223/tapwitness-ui-automation/issues/new?template=tw-feedback.yml`

反馈目标由 `feedback_channel.issue_repo` 指定，默认是 `penghang1223/tapwitness-ui-automation`。

## 步骤
0. **去重**：读 `tw/protocols/feedback_absorbed.json`（框架已吸收）与
   `.claude/tw_feedback_submitted.json`（本项目已提交），用「来源项目 + 来源 feature + 现象摘要」
   做唯一键；已吸收 / 已入队 / 已提交 → 跳过并说明。
1. 定位队列文件 `.claude/tw_feedback.md`（`feedback_channel` 指向）；不存在则建表头。
2. 追加行：`| 日期 | 阶段 | 现象 | 根因 | 对策 | 适用平台 | 来源 feature | 待提交 |`。
3. 打印队列计数：`✓ 域层坑点已入队 .claude/tw_feedback.md（当前队列 N 条待提交）`。
4. **预览**：运行以下命令，向用户展示目标仓库、标题与完整正文。用户可以修改队列后重新预览。
   ```
   python3 <插件根>/tw/tools/submit_feedback.py --project-root <宿主项目根> --dry-run
   ```
   `<插件根>` = 本 SKILL.md 所在目录的上两级（`skills/feedback/SKILL.md` → 插件根）；
   脚本内部路径由 `__file__` 推导，无需配置环境变量。
   - 脚本按字段构造正文，并对常见路径、URL、邮箱、IP 与凭据格式脱敏。自由文本仍须人工检查。
   - 用户明确确认预览内容和目标仓库后，运行同一命令并将 `--dry-run` 改为 `--yes --approval <预览校验值>`，调用 `gh issue create`。如 `feedback_channel.auto_submit: false`，保持预览。提交时队列内容或目标仓库发生变化，必须重新预览。
   - 成功：队列状态改为 `已提交(Issue #N,<日期>)`，写入 `.claude/tw_feedback_submitted.json`，
     打印 Issue URL。
   - 未装 gh / 未登录：反馈保留在本地队列，脚本打印预填 Issue 链接。
   - 远端提交结果不明确：保留待核对记录并停止自动重试。按标识检查目标仓库，确认已创建时使用 `--resolve <KEY> --issue-url <URL>`；确认未创建时使用 `--resolve <KEY> --confirm-absent`，之后可重新提交。
   - 提交锁因进程异常残留时，确认没有提交进程后删除提示中的锁目录。
5. 维护者合入域包后写 `feedback_absorbed.json` 并涨版本。

## 纪律
- 提交到公开仓库的内容必须脱敏；凭据、内网地址、客户数据不得写入队列。
- 域包正文不得写状态文件；坑点三层路由见 `tw/protocols/gate-protocol.md` §4.3
  与 `tw/protocols/stage-registry.md` §6。
- 禁止直接改 plugin 缓存内的域包文件（升级会丢失）。
