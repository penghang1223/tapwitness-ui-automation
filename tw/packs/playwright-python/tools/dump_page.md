# dump_page（playwright-python）

本文件是域包 `auxiliary.dump-page` 指向的能力实现，skill 仅按能力键存在性判断可用性。
本实现遵循 `dump-artifact-protocol.md` 的位置、目录、manifest 与消费顺序约定。

## 步骤
1. 从 profile 读取运行参数与目录约定。
2. 执行本能力对应的栈相关操作，产出落盘到约定位置。
3. 输出可供下游阶段消费的结果。
