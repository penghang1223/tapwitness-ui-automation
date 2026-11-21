# 阶段 1：业务知识召回（playwright-python 域）【强制审查门】

## 目标
本阶段在 playwright-python 域产出「业务知识召回」所需的事实与文件，为下一阶段提供可核验输入。

## 前置输入
- 从磁盘重读上游产出（禁止依赖对话记忆）；缺文件即停并说明来源。
- profile 字段 `paths` / `run` / `data_layer` 的相关项。

## 步骤
### 1-0. 前置检查
确认输入齐全、profile 已解析、域包能力键可用。

### 1-a. 依协议执行（阶段 1 三道门顺序固定，真相源 stage-registry.md §6.2）
- **第 0 步 · 前置确认门**（召回之前）：列 profile 实际值（`kb.path` 是否 none/失效、`paths` 存量检索范围、`data_layer` 概要）、问有无额外材料、回显被测范围；manual 暂停等确认，**确认前不开始召回**；非 manual 记 `review_needed=true`，full-auto 产出顶部标注「⚠️ 召回范围未经用户确认」。
- 召回与完整性检查、用例派生：禁止凭空生成 / full·single / 三路依据 / 降级策略，见 `tw/protocols/case-expansion-protocol.md §1/§2/§3`。
- **第 4 步 · 实质缺口门**（条件触发）：依据分 已确认 / DOM 推断 / UNKNOWN / CONFLICT / 资料缺失，只有影响用例派生的缺口才停，选项 `[provide]/[confirm]/[single]`。
- **第 6 步 · 用例审核门**（强制）：逐条展示 编号/标题/类别/依据/证据级别/优先级/AI 建议，`[keep]/[merge]/[delete]/[edit]`，AI 主动给合并删除建议；非 manual 产出顶部标注「⚠️ 用例清单未经用户审核」。
- 三道门未全部通过不得进入 Exit Gate；自动模式归属见 §6.2 末段。本节只给顺序与指针，条款全文以协议为准，不复述。

### 1-b. 证据落盘
页面证据写入 `<feature>/page_cache/<slug>/` 并更新 manifest；定位符必须标来源。

## 产出要求
产出：`stage1_business.md, stage1_cases.md, stage1_cases.json`。Markdown 文件末尾固定两节：`## Skill 回写记录`、`## 人工介入记录`；JSON 文件保持合法 JSON。

## 审查门判据
逐条确认产出依据与覆盖；人工批准后才推进。

## Exit Gate 输入
- 产出物：stage1_business.md, stage1_cases.md, stage1_cases.json
- 审查门结论建议：证据齐全则建议通过；有 UNKNOWN/CONFLICT 则列缺口。
- 坑点候选：无新增则显式写「本阶段无新增坑点」。

## 反模式
❌ 凭想象写定位符 / 放宽断言迁就实现 / 跳过 Exit Gate。
✅ 有证据才产出 / 每步可核验 / 五步收尾缺一不可。
