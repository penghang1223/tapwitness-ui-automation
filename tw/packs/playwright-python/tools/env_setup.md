# env_setup（playwright-python）

本文件是域包 `auxiliary.env-setup` 指向的能力实现，skill 仅按能力键存在性判断可用性。
## 步骤
1. 从 profile 读取运行参数与目录约定。
2. 执行本能力对应的栈相关操作，产出落盘到约定位置。
3. 输出可供下游阶段消费的结果。

## 环境体检 E1–E8
E1 Python 版本 / E2 依赖安装 / E3 浏览器驱动 / E4 测试目录 / E5 配置 / E6 数据层 / E7 conftest 失败现场钩子 / E8 MCP。
补齐缺失项；失败现场目录取 `paths.screenshot_dir` 并加入 gitignore。禁止跨包借用。
