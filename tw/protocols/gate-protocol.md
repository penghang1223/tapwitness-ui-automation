# Gate Protocol — 所有阶段命令的执行框架

> 分发器五步编排的门禁细节集中在本文件；分发器只给指针。

## §2 Gate Check 四分支（C=current_stage, N=本命令阶段）
| 分支 | 条件 | 行为 |
|---|---|---|
| a | C < N | 拒绝："请先完成阶段 C" |
| b | C > N 且阶段 N 为 done | 提示已完成；重跑需先改产出并手动重置 |
| b' | C > N 且阶段 N 为 skipped | 提示"阶段 N 已被 bypass"，拒绝重跑；需移除 bypasses 并重置 |
| c | C == N 且 status ∈ {pending, failed} | 置 in_progress（写 started_at），继续 |
| d | C == N 且 status == in_progress | 继续（恢复中断） |

特殊分支：8 阶段 `C==4` 且 `4_case=done` 且 `5_verify=failed` → 视同分支 c 重跑阶段 5。
`C == N` 且 status 为 done/skipped 在自洽规则下不可能出现。

## §3 profile 解析（两级 + 端解析）
两级：feature 带 subsystem 且 `.claude/profiles/<subsystem>.md` 存在 → 用子系统 profile；否则用 `.claude/project_profile.md`；两者都缺 → 停止并引导 /tw:project-scan。
端解析：feature 有 `platform` 且 profile 有 `pack_by_platform` → pack = 映射值；否则 pack = profile 的 `pack`。
`kb` / `external_sync` 始终从仓库级 profile 读。

## §4 Exit Gate 五步（缺一不可）
1. **写产出物**：按 `pack.yaml.artifacts.<N>` 写文件；末尾固定 `## Skill 回写记录` + `## 人工介入记录`。
2. **审查门**：强制门为阶段 1/3/4。manual 暂停；semi-auto 记 `review_needed=true` 继续；full-auto 记 true 无人审。
   四选项：`[Enter]` / `[edit]` / `[skip]` / `[exit]`。[skip] 跳的是审查门，不写 bypasses。
3. **更新状态**：`status=done`、`completed_at=now`、`human_intervention`、`current_stage=N+1`；N<8 时置下一阶段 in_progress。完成值为 9，不建第 9 个键。
4. **坑点三层路由**：无新增也要显式写"本阶段无新增坑点"。Q1 换同栈项目还会出现吗（否→项目层 project_profile 坑点表）；Q2 换栈还会吗（否→域层 .claude/tw_feedback.md，禁止直接改缓存）；Q3 是业务语义吗（是→业务层 KB，按 kb.writeback）。域层入队必须打印队列计数。
5. **刷新 dashboard + 校验**：按 state-protocol §7 刷看板；运行非 strict 的 `tw/tools/validate_workflow.py`。

### §4.3 失败路径（按 mode 四套独立规则，表为唯一裁决）

| 场景 | mode | 状态变更 | 回拨 / 计数 |
|---|---|---|---|
| 8 阶段 5，7 轮用尽 | manual / semi-auto | `5_verify=failed`，`current_stage=4` | 回拨到 4；提示 `/tw:ui-test-diagnosis` |
| 8 阶段 5，7 轮用尽 | full-auto | `5_verify=failed`，`current_stage` 停在 5 | **不回拨；停止推进并报告**（不继续阶段 6） |
| 录制 4，7 轮用尽 | manual / semi-auto | `4_run=failed`，`current_stage=3`，`3_case.status=in_progress` | 回拨到 3；`rework_round += 1` |
| 录制 4，7 轮用尽 | full-auto | `4_run=failed`，`current_stage` **保持 4**（首个非 done/skipped 即 4，自洽） | **不回拨，`rework_round` 不变**；停止推进 |
| 录制 5，结论「需修」 | manual / semi-auto / full-auto | `5_review=done`，`current_stage=3`，`3_case.status=in_progress` | 回拨到 3；`rework_round += 1`；full-auto 同样自动回拨，受 `> 2` 上限约束 |
| 录制 5，审核链路本身失败 | 任意 | `5_review=failed`，`current_stage` **保持 5** | 不回拨、不计数；停止并报告 |

> `rework_round` 严格是「**回拨进入阶段 3 的次数**」，没有发生回拨就不加一（故 full-auto 阶段 4 用尽、`5_review=failed` 都不计数）。`rework_round > 2` 是第 5 行的上限子约束，不是独立的安全阀。
>
> **`5_review=failed` 的语义**：只保留给审核动作本身没能完成（独立子代理启动失败、审核产物不完整、审核所需输入缺失）；正常结论「需修」写 `5_review=done` + 回拨阶段 3。
>
> **8 阶段 full-auto 的源码矛盾裁决**：源码 `auto-full` 曾写阶段 5 失败后「继续推进阶段 6」，但 `current_stage` = 第一个非 done/skipped 的阶段号，5 既然 failed 只能是 5，继续推进会让状态文件非法。**裁决：记录 `failed` 后停止推进并报告**。确实想跑回归时只能显式把 `5_verify` 置 `skipped` 并写 bypass 留痕，不能靠 failed 着往下走。
>
> 录制侧细则见 `tw/workflows/record-driven/protocols/state-protocol.md §3`，两处口径必须一致。

## §4.4 自动推进模式与两类暂停机制

| 命令 | mode | 暂停点 | 异常处理 |
|---|---|---|---|
| `new-feature` + `workflow-next` | manual | 每阶段出口 | 用户逐段驱动 |
| `auto` | semi-auto | 阶段 1/3/4/5 出口 | 阶段 5 失败让用户选 fix/skip/exit |
| `auto-full` | full-auto | 无 | 阶段 5 失败 → 记录 failed 并停止推进（见 §4.3 裁决） |
| `continue` | 读 state | 同原 mode | 从 `current_stage` 恢复 |
| `record-feature` + 单阶段命令 | manual | 阶段级 | — |
| `record-auto` | semi-auto | 阶段 1e / 2 出口 / 3a / 5 出口 | 回拨感知，超限停止 |
| `record-auto --full` | full-auto | 无（不等待用户） | 3 类必须停 + 2 类确定性处理（录制 gate-protocol §5.4） |

**两类暂停门不可混用**：

1. **Exit Gate 级审查门 / 自动模式暂停点**：Step 2 读 `state.json.mode`；manual 当场暂停，非 manual 先记 `review_needed=true` 不暂停。**暂停由 auto / record-auto skill 在 Exit Gate 完成后统一展示**，阶段 skill 不得重复实现。统一四选项 `[Enter] / [edit] / [skip] / [exit]`。
2. **阶段内部子步骤门（录制 1e / 3a）**：不在 Exit Gate，**UI 由阶段指令展示**。manual 暂停；**semi-auto 会停**（record-auto 把 1e/3a 当作与阶段 2/5 出口同级的暂停点，等用户输入）；full-auto 不暂停但记 `review_needed=true`。不要套用「非 manual 一律只记不暂停」——那条只适用于第 1 类。阶段内部选项：1e 只有 `Enter/edit/exit`（无 skip）；录制阶段 5 为 `Enter/fix/accept/exit`。

**`[skip]` 跳的是审查门、不是阶段**：两条工作流一致，审查门的跳过**不写 `bypasses`**；`bypasses` 只记阶段级跳过（与 `status: skipped` 双向对账）。状态回写按 §4.3 三值模型：批准 `false/false`；edit/skip/accept `true/false` + note；exit `null/true`；full-auto `false/true`。录制阶段 5 的 `[fix]` 回拨阶段 3、`[accept]` 用户裁定放行记 note，二者都不写 bypasses。

## §5 职责边界
L0 协议只写与方法无关的规则；栈细节下沉域包阶段指令；域包只引用协议章节号、不复述条款；状态只由 Exit Gate 写。阶段级作业纪律见 `stage-registry.md §6`。
