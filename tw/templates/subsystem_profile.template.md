---
subsystem: <子系统名>
pack: <默认域包>
stack: <规范栈标识>
platforms: [web]
pack_by_platform: {}
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
  issue_repo: "penghang1223/tapwitness-ui-automation"
  issue_url: "https://github.com/penghang1223/tapwitness-ui-automation/issues/new?template=tw-feedback.yml"
  issue_template: ".github/ISSUE_TEMPLATE/tw-feedback.yml"
  auto_submit: true
  maintainer:
    email: "<可选>"
---

# 项目约定（阶段 4 生成代码时必须遵循）

# 项目坑点表
| 日期 | 阶段 | 现象 | 根因 | 对策 |
|------|------|------|------|------|

# 业务术语速查（可选）
