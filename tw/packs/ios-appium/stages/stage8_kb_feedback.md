# 阶段 8：知识反哺（ios-appium 域）

## 目标
本阶段在 ios-appium 域产出「知识反哺」所需的事实与文件，为下一阶段提供可核验输入。

## 前置输入
- 从磁盘重读上游产出（禁止依赖对话记忆）；缺文件即停并说明来源。
- profile 字段 `paths` / `run` / `data_layer` 的相关项。

## 步骤
### 8-0. 前置检查
确认输入齐全、profile 已解析、域包能力键可用。

### 8-a. 依协议执行
- KB 写回按 `kb.path` 与 `kb.writeback`（auto|manual|off），`kb` / `external_sync` 只从仓库级 profile 读。
- 坑点三层路由 + 已吸收注册表见 `tw/protocols/gate-protocol.md §4` Step 4；无新增也要显式写「本阶段无新增坑点」。
- 反馈队列格式见 `tw/protocols/feedback_absorbed.json` 与 `.issue_templates/feedback.md`。

### 8-b. 证据落盘
页面证据写入 `<feature>/page_cache/<slug>/` 并更新 manifest；定位符必须标来源。

## 产出要求
产出：`stage8_kb_feedback.md`。文件末尾固定两节：`## Skill 回写记录`、`## 人工介入记录`。

## 审查门判据
无强制审查门，按 Exit Gate 收尾。

## Exit Gate 输入
- 产出物：stage8_kb_feedback.md
- 审查门结论建议：证据齐全则建议通过；有 UNKNOWN/CONFLICT 则列缺口。
- 坑点候选：无新增则显式写「本阶段无新增坑点」。

## 反模式
❌ 凭想象写定位符 / 放宽断言迁就实现 / 跳过 Exit Gate。
✅ 有证据才产出 / 每步可核验 / 五步收尾缺一不可。
