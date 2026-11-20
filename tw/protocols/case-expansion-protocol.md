# Case Expansion Protocol — 凭什么派生用例

## 1. 禁止凭空生成
无依据 → 不生成，或列入 `not_generated`。`evidence_level` 只允许 `confirmed | inferred`，禁止 `assumed`。

## 2. full / single
`full`（默认）：完整用例集（正向/边界/负面）；`single`：只开发录制的一条，`cases` 长度 1，`expansion_mode="single"`。

## 3. 三路依据（优先级）
KB > 真实 DOM > 查重（存量用例）。每条边界/负面用例必须填出 `evidence`
。三路皆空 → `evidence.degraded=true`，只出正向变体，md 顶部显式标注依据缺失。

## 4. 证据分级
`confirmed`：来自 KB / DOM / 用户确认；`inferred`：基于通用健壮性推断，须写清推断依据。

## 5. 派生规则
同一前置 + 同步骤 + 同预期 → 1 条用例，数据差异进 `data_rows`（parametrize），不拆用例。
正向变体只取会走不同代码分支的组合，不做笛卡尔积。

## 6. 数据计划
每条用例必填 `data_plan`：`precondition_data` / `data_source` / `setup` / `cleanup` / `isolation_key` / `verified`。
`data_source` + `cleanup` 写不出 → 标"待确认"，不许默认假设。

## 7. JSON 格式
双格式产出 `.md` + `.json`；`review.required/approved/actions` 与 state 的 `review_needed` 不是一回事，不得互相推导。
