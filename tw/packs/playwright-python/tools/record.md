# record（playwright-python）

本文件是域包 `auxiliary.record` 指向的能力实现，skill 仅按能力键存在性判断可用性。
## 步骤
1. 从 profile 读取运行参数与目录约定。
2. 执行本能力对应的栈相关操作，产出落盘到约定位置。
3. 输出可供下游阶段消费的结果。

## 录制实现（Playwright + Python）
1. 读 `run.base_url` 与 `run.viewport`；codegen 必须带 `--viewport-size <viewport>`，缺省禁止回落 1280×720。
2. 后处理：语法检查 / 引号转义 / POM 生成 / 自动复用已有登录方法（auth fixture > LoginPage > api_login，无需人工确认）/ 补充缺失操作。
3. `storage_state.json` 加入 `.gitignore`（含 token）。
4. 不执行 `--with-assertion` 段。
