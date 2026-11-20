---
name: setup-mcp
description: >
  配置移动端设备 MCP。触发：MCP、setup mcp、设备连接。
---

# /tw:setup-mcp — 移动端 MCP 配置

## 职责
按域包 `auxiliary.setup-mcp` 指向的实现配置移动端 MCP。

## 步骤
1. 检查 pack 是否声明 `auxiliary.setup-mcp`；未声明 → 停止并提示非移动端无需配置。
2. 读 `file` 指向的实现，按其步骤连接设备/模拟器并验证。
3. 输出可用设备清单与连接状态。
