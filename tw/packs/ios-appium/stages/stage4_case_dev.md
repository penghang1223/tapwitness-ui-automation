# 阶段 4：用例开发（ios-appium 域）【强制审查门】

## 目标
本阶段在 ios-appium 域产出「用例开发」所需的事实与文件，为下一阶段提供可核验输入。

## 前置输入
- 从磁盘重读上游产出（禁止依赖对话记忆）；缺文件即停并说明来源。
- profile 字段 `paths` / `run` / `data_layer` 的相关项。

## 步骤
### 4-0. 前置检查
确认输入齐全、profile 已解析、域包能力键可用。

### 4-a. 依协议执行（真相源 stage-registry.md §6.3）
- **4-0 重复性检查**：写代码前按 `paths.test_root` 中英双语并行查重（测试文件名关键词 + PO 英文类名）。
- **4-pre DOM 分级采集**（不全部硬采）：缓存/存量 PO 命中免采；断言密集的新页面才采集并写 `page_cache/`；其余延后由阶段 5 按需补采。
- **4a-0 DOM 冲突对照**：用真实 DOM 逐条对照 stage3 断言，`impl` 与 `route` 双轨修订，冲突登记进 `stage4_plan.md` 的「DOM 冲突修订表」。
- **4a plan 审查门**七项、**4b 每个定位符标来源**（`page_cache/xxx#L42` / 存量 PO / codegen，缺页不许猜）见 §6.3；证据落盘见 `tw/protocols/dump-artifact-protocol.md §1/§2/§5`。

### 4-b. 证据落盘
页面证据写入 `<feature>/page_cache/<slug>/` 并更新 manifest；定位符必须标来源。

## 产出要求
产出：`stage4_plan.md, stage4_files.md`。文件末尾固定两节：`## Skill 回写记录`、`## 人工介入记录`。

## 审查门判据
逐条确认产出依据与覆盖；人工批准后才推进。

## Exit Gate 输入
- 产出物：stage4_plan.md, stage4_files.md
- 审查门结论建议：证据齐全则建议通过；有 UNKNOWN/CONFLICT 则列缺口。
- 坑点候选：无新增则显式写「本阶段无新增坑点」。

## 反模式
❌ 凭想象写定位符 / 放宽断言迁就实现 / 跳过 Exit Gate。
✅ 有证据才产出 / 每步可核验 / 五步收尾缺一不可。
