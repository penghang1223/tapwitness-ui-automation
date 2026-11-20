# 阶段 6：端到端（playwright-python 域）

## 目标
本阶段在 playwright-python 域产出「端到端」所需的事实与文件，为下一阶段提供可核验输入。

## 前置输入
- 从磁盘重读上游产出（禁止依赖对话记忆）；缺文件即停并说明来源。
- profile 字段 `paths` / `run` / `data_layer` 的相关项。

## 步骤
### 6-0. 前置检查
确认输入齐全、profile 已解析、域包能力键可用。

### 6-a. 依协议执行（真相源 stage-registry.md §6.5）
- 全量回归命令取 `run.suite_command`，不硬编码；从磁盘重读全部上游产出。
- **flaky quarantine 四步**：识别（重跑 2–3 次）→ 隔离（skip/xfail + 单独套件）→ 归因（等待/数据/环境/产品）→ 治理（修或转 issue）；禁止长期挂着不处理。

### 6-b. 证据落盘
页面证据写入 `<feature>/page_cache/<slug>/` 并更新 manifest；定位符必须标来源。

## 产出要求
产出：`stage6_e2e.md`。文件末尾固定两节：`## Skill 回写记录`、`## 人工介入记录`。

## 审查门判据
无强制审查门，按 Exit Gate 收尾。

## Exit Gate 输入
- 产出物：stage6_e2e.md
- 审查门结论建议：证据齐全则建议通过；有 UNKNOWN/CONFLICT 则列缺口。
- 坑点候选：无新增则显式写「本阶段无新增坑点」。

## 反模式
❌ 凭想象写定位符 / 放宽断言迁就实现 / 跳过 Exit Gate。
✅ 有证据才产出 / 每步可核验 / 五步收尾缺一不可。
