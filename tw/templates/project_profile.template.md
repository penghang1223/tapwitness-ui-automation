---
project_id: <仓库目录名>
project_name: <人类可读名>
pack: <默认域包>
core_version: 1.4.0
subsystems: {}
paths:
  test_root: <测试目录>
  page_objects: <页面对象目录>
  utils: <工具目录>
  data: <数据目录，可选>
  screenshot_dir: <失败现场目录>
run:
  base_url: "<被测系统入口>"
  test_command: "<跑单文件命令，{test_path} 占位>"
  suite_command: "<全量回归命令>"
  env_switch: "<环境切换方式>"
  device: "<浏览器/设备>"
  viewport: "<宽,高>"
data_layer:
  tiers: [<分层>]
  entrypoints: { <tier>: "<入口>" }
  db_assert_channel: "<封装类/MCP/直连/无>"
  db_config:
    location: "<配置位置>"
    password_scheme: "<加密方案>"
    required_env: "<环境变量名>"
kb:
  path: "<知识库根目录或 none>"
  writeback: auto
dashboard:
  path: .claude/workflows/dashboard.md
feedback_channel:
  issue_url: "<Issue 新建 URL>"
  issue_template: ".issue_templates/feedback.md"
  maintainer:
    email: "<可选>"
external_sync: []
---

# 仓库级说明（可选）
