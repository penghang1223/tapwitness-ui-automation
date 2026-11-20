# 阶段 5：注册 runner（子步骤）（ios-appium 域）

## 目标
本阶段在 ios-appium 域产出「注册 runner（子步骤）」所需的事实与文件，为下一阶段提供可核验输入。

## 前置输入
- 从磁盘重读上游产出（禁止依赖对话记忆）；缺文件即停并说明来源。
- profile 字段 `paths` / `run` / `data_layer` 的相关项。

## 步骤
### 5-0. 前置检查
确认输入齐全、profile 已解析、域包能力键可用。

### 5-a. 依协议执行（真相源 stage-registry.md §6.4）
- **从磁盘重读 stage3/stage4 产出**，禁用对话记忆。
- **≤7 轮探查-修复循环**：测试命令取 `run.test_command`；失败先读 `paths.screenshot_dir` 下的 `.png` + `.html` 现场；按断言三维归因（超时→脚本/环境，值不对→产品缺陷，C 类→仅告警）；缺 DOM 事实时按需采集单页写回 `page_cache/`。
- **禁止放宽断言迁就实现**（`tw/protocols/assertion-protocol.md §4`）。用尽后按 `tw/protocols/gate-protocol.md §4.3` 四套 mode 分支处理，manual/semi-auto 提示 `/tw:ui-test-diagnosis`。

### 5-b. 证据落盘
页面证据写入 `<feature>/page_cache/<slug>/` 并更新 manifest；定位符必须标来源。

## 产出要求
产出：`stage5_verify.log`。文件末尾固定两节：`## Skill 回写记录`、`## 人工介入记录`。

## 审查门判据
无强制审查门，按 Exit Gate 收尾。

## Exit Gate 输入
- 产出物：stage5_verify.log
- 审查门结论建议：证据齐全则建议通过；有 UNKNOWN/CONFLICT 则列缺口。
- 坑点候选：无新增则显式写「本阶段无新增坑点」。

## 反模式
❌ 凭想象写定位符 / 放宽断言迁就实现 / 跳过 Exit Gate。
✅ 有证据才产出 / 每步可核验 / 五步收尾缺一不可。
