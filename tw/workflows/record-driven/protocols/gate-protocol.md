# Record Gate Protocol — 录制门禁

## §2 Gate Check 四分支
同 L0 gate-protocol §2。特殊分支：`C==3` 且 `3_case=done` 且（`4_run=failed` 或 `5_review=done`）→ 视同 c 重跑阶段 3。
`5_review=failed` 不在此列 —— 修复审核能力后直接重跑 record-review（C==5 的 failed）。

## §4 Exit Gate 五步
1. 写产出物：按 workflow.yaml.artifacts.<N>。阶段 2 在审查及更新状态前运行 `python3 "<插件根>/tw/tools/validate_artifacts.py" --workflow record-driven --feature-dir ".claude/record-workflows/<feature>" --stage 2`。将占位符换成实际路径；非零退出码即停止，修正产物后重试，不推进状态。该检查只针对本次阶段产出。
2. 审查门：阶段 2 / 5 为 mandatory，阶段 3 在 3a 子步。四选项：阶段 5 用 `[Enter]/[fix]/[accept]/[exit]`；1e 用 `Enter/edit/exit`。
3. 更新状态：完成值 6；回拨按 record state-protocol §3。
4. 坑点三层路由：同 L0，无新增也要显式写。
5. 刷新 dashboard + 在宿主项目根运行 `python3 "<插件根>/tw/workflows/record-driven/tools/validate_record_workflow.py" --workflows-dir .claude/record-workflows`。

## §4.4 暂停门两类
Exit Gate 级审查门：manual 当场暂停；非 manual 记 review_needed=true，暂停由 record-auto 统一展示。
阶段内部子步骤门（1e / 3a）：UI 由阶段指令展示；record-auto 在循环里不跳过；semi-auto 会停，full-auto 不停但记 review_needed=true。

## §5.4 full-auto 安全阀（3 类必须停 + 2 类确定性处理）

> 「停」= **终止推进并报告**，不是暂停等输入。按是否需要判断力分两类：

| # | 情形 | 处理 | 类别 |
|---|---|---|---|
| 1 | 阶段 2 `evidence.degraded == true` | 停止报告——依据不足的用例集不该无人确认就进入开发 | **必须停** |
| 2 | 阶段 4 归因为环境问题 / 真实 bug | 立即停止，不改脚本绕过（改了就是假绿） | **必须停** |
| 3 | 任一校验器报 ERROR | 停止报告（WARNING 不触发） | **必须停** |
| 4 | 阶段 4 七轮修复用尽仍失败 | `4_run=failed`、`current_stage` 停 4、停止推进；**不自动回拨**，`rework_round` 不变 | 确定性处理（停止） |
| 5 | 阶段 5 阻塞项（结论「需修」） | **自动回拨阶段 3** 重走 3→4→5，`rework_round += 1`，受 `> 2` 约束；超限转停止报告 | 确定性处理（回拨） |

> `rework_round > 2` **不是独立的第 5 条安全阀**，而是第 5 行的上限子约束。真正「不得跳过、触发即停」的只有前 3 条；第 4 行也停，但属状态机可判定的确定性结果。
>
> **第 3 条「校验器」范围**：指本阶段 Exit Gate Step 5 实际运行的那一个——录制用 `tw/workflows/record-driven/tools/validate_record_workflow.py --workflows-dir .claude/record-workflows`，**非 strict**（WARNING 不触发停止）。不要把另一套校验器的结果混进来。

停止格式（由 `record-auto` 输出）：
```
⛔ 全自动推进已停止：<原因>
已完成阶段：<列表>
待人工决策：<具体问题 + 相关文件:行>
继续方式：修复后调 /tw:record-<stage> 或 /tw:record-auto <feature>
```

## §7 录制阶段关键纪律（域包录制 stage 只引用本节章节号）

- **阶段 1 录制**：1-0 依赖检查缺一即停；只录一条正向主流程，异常分支不录；codegen 带 `--viewport-size <profile.run.viewport>`（缺省不得回落 1280×720）；后处理委托域包 `tools/record.md`（语法检查 / 引号转义 / POM 生成 / 自动复用已有登录方法 / `storage_state.json` 加入 .gitignore）；`stage1_record.md` 登记流程描述与操作序列。**1e 操作序列人工核对**：逐条列序号/目标/值请用户确认无遗漏；single 模式无阶段 2 拆解兜底，**不可跳**。不执行 `record.md` 的 `--with-assertion` 段（断言归阶段 2）。
- **阶段 2 生成用例**：先定 `full`（默认）/ `single`（cases 长度 1、`expansion_mode="single"`）；流程 2-0 前置检查 → 2a 拆解（按操作类型/页面边界/提交动作切段，场景须能独立执行）→ 2b 三路依据（KB > DOM > 查重）→ 2c 派生 → 2d 挂断言 → 2e `data_plan` → 2f 双格式 → 2g 强制审查门。single 跳过拆解与派生，但依据纪律与断言挂载照常生效。三路皆空**不编造**，只出正向变体，`evidence.degraded=true`，md 顶部显式降级说明。
- **阶段 3 开发用例**：3-pre DOM 准备（缓存/存量 PO 命中免采）；**3a plan 审查**含文件清单 / PO 方法设计（定位符证据为**可核验三元组**：证据位置 / 验证了什么 / 易失效项的验证动作）/ 用例→方法映射 / **steps→方法覆盖表**（逐条 step 有归属，无归属即缺口，single 必填）/ 阶梯自检 / 项目约定对照；3b 编码；3c 写 `stage3_files.md`。
- **阶段 4 执行并修复**：7 轮探查-修复循环，归因逻辑同 L0 `stage-registry.md §6.4`；归因为环境/真实 bug → 停止报告，**不改脚本绕过**。
- **阶段 5 代码审核**：**必须拉起独立审核子代理**（`subagent`），不能同一上下文自审；审核对象是**跑通后存活的最终代码**（含阶段 4 改动）；五类检查：① PO 规范 ② 断言覆盖（对 `stage2_cases.json` **逐条对账**，含 ②.5 数据准备/清理）③ 域包坑点扫描 ④ 脆弱定位符 ⑤ 过度设计（只覆盖「多写」，全部「建议」级，永不判阻塞）。清单见 `tw/packs/playwright-python/workflows/record-driven/references/code_review_checklist.md`。结论「需修」→ 回拨阶段 3 重走整轮，受 `rework_round > 2` 上限。
