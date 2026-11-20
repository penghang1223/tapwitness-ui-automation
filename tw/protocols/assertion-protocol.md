# Assertion Protocol — 断言方法论

## 1. 三维分类
- 按目标：UI / DB / API（可多选，`route` 是数组）。
- 按严重度：A 阻塞 / B 功能 / C 提示。
- 按类型：hard / soft / negative / conditional。

## 2. 验证目标决定路由
用户在界面能看到的结果 → UI；落库事实且 UI 不展示 → DB；接口返回契约 → API。
`route_provisional=true` 表示路由待阶段 4 用真实 DOM/表结构核实。

## 3. 等待与断言分离
`wait_condition` ∈ {toast_visible, element_present, url_contains, none}，先等条件再断言；禁止用 sleep 代替条件等待。

## 4. 失败契约
超时 → 脚本/环境；值不对 → 产品缺陷；C 类 → 仅告警不阻塞。禁止放宽断言迁就实现。

## 5. 负面断言
负面场景必须有明确的负向预期（错误提示/不落库/不可达），不得写"不报错"这类空断言。

## 6. DB 五条
1) 先 `information_schema` 定位表 → 2) `DESCRIBE` 看字段 → 3) 闭环验证查询 → 4) 只断言本用例隔离的数据 → 5) 连接信息只从 data_layer.db_config 读，profile 禁明文密码。

## 7. 业务语义封装
断言写业务语义，不写 selector；selector 由阶段 4 回填 `selector_source`。

## 8. 排除项
本阶段不拍板 DOM 细节、不做数据构造、不写代码。
