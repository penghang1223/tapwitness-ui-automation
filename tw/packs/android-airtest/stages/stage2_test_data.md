# 阶段 2：测试数据构造（android-airtest 域）

## 目标
本阶段在 android-airtest 域产出「测试数据构造」所需的事实与文件，为下一阶段提供可核验输入。

## 前置输入
- 从磁盘重读上游产出（禁止依赖对话记忆）；缺文件即停并说明来源。
- profile 字段 `paths` / `run` / `data_layer` 的相关项。

## 步骤
### 2-0. 前置检查
确认输入齐全、profile 已解析、域包能力键可用。

### 2-a. 依协议执行
- 数据计划按 `tw/protocols/case-expansion-protocol.md §6`：每条用例必填 `data_plan`（前置清理 / 后置清理 / 隔离键 / 可见性验证）；写不出标「待确认」，不许默认假设。
- DB 断言通道与连接信息只按 profile 的 data_layer 配置读，profile 禁明文密码；DB 五条见 `tw/protocols/assertion-protocol.md §6`。
- 状态与产出写法见 `tw/protocols/state-protocol.md §1`；协议只引用不复述。

### 2-b. 证据落盘
页面证据写入 `<feature>/page_cache/<slug>/` 并更新 manifest；定位符必须标来源。

## 产出要求
产出：`stage2_data.md`。文件末尾固定两节：`## Skill 回写记录`、`## 人工介入记录`。

## 审查门判据
无强制审查门，按 Exit Gate 收尾。

## Exit Gate 输入
- 产出物：stage2_data.md
- 审查门结论建议：证据齐全则建议通过；有 UNKNOWN/CONFLICT 则列缺口。
- 坑点候选：无新增则显式写「本阶段无新增坑点」。

## 反模式
❌ 凭想象写定位符 / 放宽断言迁就实现 / 跳过 Exit Gate。
✅ 有证据才产出 / 每步可核验 / 五步收尾缺一不可。
