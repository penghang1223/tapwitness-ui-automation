# 验收套件说明

`run_acceptance.py` 把架构规格 §12 Phase 0–8 的验收命令、§13 不变式中可静态
验证的条目、反向破坏测试、端到端状态流转模拟，以及 Claude Code 官方 CLI 冒烟
固化成一条命令。全部用例只读仓库，需要改文件的反向测试都在 `try/finally` 中恢复。

## 运行

```bash
python3 tests/run_acceptance.py             # 51 项：静态契约 + 条款守护 + fixture + 反向 + 状态流转
python3 tests/run_acceptance.py --quick     # 21 项：只跑静态契约
python3 tests/run_acceptance.py --official  # 56 项：追加官方 CLI 冒烟（含真实会话执行 slash 命令）
```

退出码：全部 PASS（SKIP 不算失败）→ 0；任一 FAIL → 1。

环境要求：Python 3.8+ 与 PyYAML（域包/工作流 YAML 解析需要）。
`--official` 额外需要本机安装 `claude` CLI；真实会话用例在未登录时返回 SKIP
而非 FAIL。隔离安装使用临时 `CLAUDE_CONFIG_DIR`，**不会**改动用户真实插件配置。

## 覆盖的分组

| 分组 | 数量 | 内容 |
|---|---|---|
| 静态契约 | 21 | manifest、31 个 SKILL.md frontmatter、README 一致性、§15.1 文件清单、两个生成器 `--check`、5 个契约校验器、零耦合、能力键门控、脚本卫生、六段结构、HANDOFF 幂等 |
| §13/§14 条款守护 | 10 | §4.3 四套 mode 失败分支、§4.4 两类暂停门、阶段 1 三道门顺序、阶段 4 分级采集与 DOM 冲突对照、阶段 5/6 探查修复与 flaky 四步、证据纪律 7 条引用、`--full` 安全阀 5 行表、**域包正文不写状态文件**、域包只引用章节号、发布版本一致性 |
| 状态机 fixture 与隔离 | 6 | Phase 4/5 官方 fixture、默认/显式/相对路径一致、无目录报错、两套工作流隔离、dashboard 缺失 |
| 反向破坏 | 9 | 自洽漂移、字符串型 `human_intervention`、bypass 缺失/短 reason、`5_verify=failed`、录制 rework 分级、分发器漂移、未声明 md、录制覆盖护栏逃逸 |
| 端到端状态流转 | 5 | 8 阶段 1→9 共 9 个快照、录制 1→6 共 6 个快照、bypass `target_stage-1` 语义、审查门三值模型 4 种回写、失败回拨停在 4 |
| 官方 CLI 冒烟 | 5 | `claude plugin validate`（含 `--profile directory`）、隔离 marketplace add→install→list→details、真实 `-p` 会话列出 31 个命令、**真实会话执行 `/tw:new-feature` 并落盘状态机通过 strict 校验** |

反向破坏组是刻意验证「校验器真的会拦」，而不只是「空跑能过」。端到端组会为
每个 `done` 阶段创建产出文件、同步看板头部，因此走的是 `--strict`（WARNING
也会失败）口径。

## 未覆盖（需人工执行，不要在报告里当成已测）

1. **§12 Phase 9 剩余的交互式会话**：`/tw:new-feature` 已由
   `c_official_session_new_feature` 在隔离宿主项目里真实跑通（创建
   `state.json` / `.current` / `dashboard.md`，并由套件独立复核 `--strict`
   0 ERROR / 0 WARNING）。**仍需人工**的是依赖多轮人机交互与真实被测系统的部分：
   阶段 1 三道门的实际暂停与实质缺口门条件触发、`/tw:auto` 在 1/3/4/5 出口停、
   `/tw:record-auto --full` 的 3 类必停与 `evidence.degraded=true` 安全阀终止推进。
   这些无法用静态脚本断言。
2. **`plugin.json.version` 与 git tag 一致**：项目已初始化 git 并发布到
   `github.com/penghang1223/tapwitness-ui-automation`（v1.31.0 已推送），
   但 `claude plugin tag` 与 `v1.31.0` tag 仍未执行。套件以
   `c_release_version_contract` 做静态代理（semver 合法 / marketplace 名字一致 /
   域包 `min_core_version` 不高于内核版本）；真正打 tag 需人工执行。
3. **域包实战资产真实性**：按 §15.3「功能等价」口径，阶段判据、坑点条目、
   录制细节为符合六段结构与引用关系的占位内容，需领域专家补全。
   本轮已补齐 §6.2–§6.5 / §7.2 的**纪律条款与章节号引用**，但未写真实栈经验。
4. **另一台机器的 `marketplace add` + `install`**：远程 GitHub 安装链路已实测
   通过（隔离配置目录下 `claude plugin marketplace add penghang1223/tapwitness-ui-automation`
   走 HTTPS clone → `install tw@tw-marketplace` → `enabled: true, v1.31.0`），
   不再是本地路径市场。但仍在**同一台机器**上验证，未覆盖跨机器/跨网络环境。

> 此前列为「需人工评审」的 **§13「域包阶段指令不写状态文件」** 已由
> `c_clause_pack_no_state_write` 自动化：扫描 38 份阶段指令，正文不得出现
> `state.json` / `record_state.json` / `dashboard.md` / `.current`（用词边界区分
> `storage_state.json` 这类浏览器认证态文件）。不再需要人工兜底。

## 已知实现口径

- 校验器成功输出含 `PASS：0 ERROR / 0 WARNING` 字样，因此套件用**行首**
  `ERROR` / `WARNING` 正则统计诊断行，不能用子串计数。
- 真实会话输出可能混入 Claude Code 的环境提示（如工作区未信任时忽略
  `settings.local.json` 的两行警告）。`c_official_session_visibility` 只把
  匹配 `^[a-z][a-z0-9-]*$` 的裸命令名计入集合，不修改用户全局信任设置。
- `gen_handoff.py` 只写用户显式指定的项目目录，不依赖 `__file__` 推导仓库根，
  因此脚本卫生检查只对另外 4 个脚本要求 `Path(__file__)`。
- `claude plugin validate --strict` 会把 icon 缺失等提示计入，本套件按
  官方默认 + `--profile directory` 两种口径验收，均要求 rc=0。
- `--official` 的最后一项会在**临时宿主项目**里起真实 Claude Code 会话执行
  `/tw:new-feature`。Claude Code 默认把 `.claude/` 视为敏感路径并拒绝写入，
  故该用例使用 `--permission-mode bypassPermissions`；作用范围仅限该临时目录，
  不触碰用户真实项目与全局插件配置。未登录时返回 SKIP 而非 FAIL。
  两项真实会话都会调用模型 API，`--official` 比默认模式慢约 1–2 分钟。
