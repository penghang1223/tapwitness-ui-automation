# Stage Registry — 8 个槽位恒定

| # | 槽位 id | 阶段 | 命令 | 默认产出 |
|---|---|---|---|---|
| 1 | 1_business | 业务知识 | business-context | stage1_business.md + stage1_cases.json |
| 2 | 2_data | 数据准备 | ui-test-data | stage2_data.md |
| 3 | 3_assertion | 断言设计 | ui-test-assertion | stage3_assertions.json |
| 4 | 4_case | 用例开发 | ui-test-case | stage4_plan.md |
| 5 | 5_verify | 本地验证 | verify | stage5_verify.log |
| 6 | 6_e2e | 端到端 | ui-test-e2e | stage6_e2e.md |
| 7 | 7_report | 开发汇报 | report | stage7_report.md |
| 8 | 8_kb_feedback | 知识反哺 | wiki-feedback | stage8_kb_feedback.md |

## 强制重读规则
下游阶段必须从磁盘重读上游产出（不依赖对话记忆）：阶段 3 读 stage1_cases.json；阶段 4 读 stage3_assertions.json；阶段 5 读 stage3/stage4 产出；阶段 6/7 读全部产出。
槽位契约 C1：8 槽位齐全、status ∈ {implemented, stub}；stub 时 /tw:workflow-next 告警并停止推进。
工作流外边界：给已有用例加测试点走 /tw:ui-test-case；派生新场景走 /tw:ui-test-extend；修 bug 走 /tw:ui-test-diagnosis。

## §6 阶段关键纪律（域包阶段指令只引用本节章节号，不复述条款）

### §6.2 阶段 1 三道门（顺序固定，最容易做错）

1. **前置确认门（第 0 步，召回之前）**：列出 profile 实际值（`kb.path` 含 none/失效、`paths` 存量代码检索范围、`data_layer` 概要），问用户有无额外材料（PRD/需求/接口文档），回显被测模块/页面/功能点范围。manual 模式暂停等确认，**确认前不开始召回**。非 manual 记 `review_needed=true`，full-auto 产出顶部标注「⚠️ 召回范围未经用户确认」。
2. **实质缺口门（第 4 步，条件触发）**：把依据分为 已确认 / DOM 推断 / UNKNOWN / CONFLICT / 资料缺失；影响用例派生的缺口暂停问用户，选项 `[provide]` / `[confirm]` / `[single]`。无缺口则不触发，不得强行暂停。
3. **用例审核门（第 6 步，强制）**：展示 编号/标题/类别/依据/证据级别/优先级/AI 建议，逐条 `[keep]` / `[merge]` / `[delete]` / `[edit]`；AI 必须主动给合并/删除建议。非 manual 时产出顶部标注「⚠️ 用例清单未经用户审核」。

**三道门在自动模式下的归属**：semi-auto 的 `/tw:auto` 在阶段 1 出口统一暂停，**同时补做**前置确认与用例审核；用户确认后，阶段条目上的 `review_needed` 按 `gate-protocol.md §4.3` 三值模型清零（edit/skip 记 `human_intervention=true`）。full-auto 不停、不补，`review_needed` 保持 `true`，产出顶部两个 ⚠️ 标注都要写。
**三道门未全部通过不得进入 Exit Gate。**

### §6.3 阶段 4 的 4-pre 与 4a-0

- **4-0 重复性检查**：写代码前，中英双语并行搜索 `profile.paths.test_root`（测试文件名关键词 + PO 英文类名），命中即提示重叠。
- **4-pre DOM 分级采集**（不全部硬采）：缓存/存量 PO 命中 → 免采；断言密集的新页面 → MCP 自动导航/脚本主动采集写入 `page_cache/`；其余 → 延后标注，由阶段 5 按需补采。禁止一次性全量硬采（token 与时间双爆）。
- **4a-0 DOM 冲突对照**：用已采集的真实 DOM 逐条对照 stage3 断言；`impl` 与 `route` 双轨修订（`route_provisional` 可改路由），冲突必须登记进 `stage4_plan.md` 的「DOM 冲突修订表」。
- **4a plan 审查门**：文件清单 / PO 方法设计 / 采集状态表 / 冲突修订表 / 断言实现映射 / 阶梯自检 / 项目约定对照。
- **4b 编码**：每个定位符标来源（`page_cache/xxx#L42` / 存量 PO / codegen），缺页不许猜。正向变体只取会走不同代码分支的组合，不做笛卡尔积。

### §6.4 阶段 5 探查-修复循环（≤7 轮）

每轮：① 跑测试（命令取 `profile.run.test_command`，不硬编码）→ ② 失败优先读 conftest 自动保存的失败现场（`profile.paths.screenshot_dir` 下 `.png` + `.html`）→ ③ 按断言三维字段自动归因（超时→脚本/环境；值不对→产品缺陷；C 类→仅告警）→ ④ 归因为定位符/断言不符且缺 DOM 事实 → **按需采集单页**写回 `page_cache/` → ⑤ 修 → 重跑 → ⑥ 用尽 → `5_verify=failed`，按 `gate-protocol.md §4.3` 四套 mode 分支处理，manual/semi-auto 提示 `/tw:ui-test-diagnosis`。
**禁止放宽断言迁就实现。**

### §6.5 阶段 6 flaky quarantine 四步

识别（重跑 2–3 次）→ 隔离（标记 skip/xfail + 单独套件）→ 归因（等待 / 数据 / 环境 / 产品）→ 治理（修或转 issue，禁止长期挂着不处理）。

### 引用关系（§13 证据纪律）

`case-expansion-protocol.md`（禁止凭空生成 / full·single / 三路依据 / 降级策略）由阶段 1 与录制阶段 2 引用；`assertion-protocol.md`（三维分类 / 路由规则 / 等待与断言分离 / DB 五条 / 业务语义封装）由阶段 3 引用；`dump-artifact-protocol.md`（证据落盘唯一位置）由阶段 4 与录制阶段 3 引用。
