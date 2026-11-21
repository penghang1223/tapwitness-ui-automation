# 阶段 3：断言设计（android-airtest 域）【强制审查门】

## 目标
本阶段在 android-airtest 域产出「断言设计」所需的事实与文件，为下一阶段提供可核验输入。

## 前置输入
- 从磁盘重读上游产出（禁止依赖对话记忆）；缺文件即停并说明来源。
- profile 字段 `paths` / `run` / `data_layer` 的相关项。

## 步骤
### 3-0. 前置检查
确认输入齐全、profile 已解析、域包能力键可用。

### 3-a. 依协议执行
- **从磁盘重读 `stage1_cases.json`**（stage-registry.md 强制重读规则），禁用对话记忆。
- 三维分类 / 路由与 `route_provisional` / 等待与断言分离 / DB 五条 / 业务语义封装，见 `tw/protocols/assertion-protocol.md §1/§2/§3/§6/§7`。
- 双格式与 `review` 字段见 `tw/protocols/case-expansion-protocol.md §7`；`review` 与 state 的 `review_needed` 不得互相推导。

### 3-b. 证据落盘
页面证据写入 `<feature>/page_cache/<slug>/` 并更新 manifest；定位符必须标来源。

## 产出要求
产出：`stage3_assertions.md, stage3_assertions.json`。Markdown 文件末尾固定两节：`## Skill 回写记录`、`## 人工介入记录`；JSON 文件保持合法 JSON。

## 审查门判据
逐条确认产出依据与覆盖；人工批准后才推进。

## Exit Gate 输入
- 产出物：stage3_assertions.md, stage3_assertions.json
- 审查门结论建议：证据齐全则建议通过；有 UNKNOWN/CONFLICT 则列缺口。
- 坑点候选：无新增则显式写「本阶段无新增坑点」。

## 反模式
❌ 凭想象写定位符 / 放宽断言迁就实现 / 跳过 Exit Gate。
✅ 有证据才产出 / 每步可核验 / 五步收尾缺一不可。
