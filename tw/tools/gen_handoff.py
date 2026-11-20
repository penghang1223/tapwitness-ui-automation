#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HANDOFF.md 阶段→命令映射段生成器。

标记区间替换：<!-- tw:start ... tw:end --> 之间的内容由本工具重建，标记外手写内容保留。
用法：
  python tw/tools/gen_handoff.py <项目根>            # 写入 <项目根>/HANDOFF.md
  python tw/tools/gen_handoff.py <项目根> --check    # 只比对
  python tw/tools/gen_handoff.py <项目根> --stdout   # 只打印生成内容
"""
import sys
import argparse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

START = "<!-- tw:start -->"
END = "<!-- tw:end -->"

BLOCK = """<!-- tw:start -->
## TW 工作流 · 阶段→命令映射

本项目已接入 TW 工作流框架。命令由 plugin 提供，宿主项目不复制框架逻辑。

### 8 阶段工作流（/tw:new-feature 入口）
| 阶段 | 命令 | 产出 |
|---|---|---|
| 1 业务知识召回 | /tw:business-context | stage1_business.md / stage1_cases.json |
| 2 数据准备 | /tw:ui-test-data | stage2_data.md |
| 3 断言设计 | /tw:ui-test-assertion | stage3_assertions.json |
| 4 用例开发 | /tw:ui-test-case | stage4_plan.md |
| 5 本地验证 | /tw:verify | stage5_verify.log |
| 6 端到端 | /tw:ui-test-e2e | stage6_e2e.md |
| 7 开发汇报 | /tw:report | stage7_report.md |
| 8 知识反哺 | /tw:wiki-feedback | stage8_kb_feedback.md |

元命令：/tw:workflow-status、/tw:workflow-next、/tw:workflow-bypass、/tw:auto、/tw:auto-full、/tw:continue。
辅助：/tw:project-scan、/tw:env-setup、/tw:feedback、/tw:dump-page、/tw:ui-test-diagnosis、/tw:setup-mcp、/tw:ui-test-extend。

### 录制驱动工作流（/tw:record-feature 入口）
| 阶段 | 命令 | 产出 |
|---|---|---|
| 1 录制 | /tw:record-capture | stage1_record.md |
| 2 生成用例 | /tw:record-casegen | stage2_cases.json |
| 3 开发用例 | /tw:record-dev | stage3_plan.md |
| 4 执行并修复 | /tw:record-run | stage4_run.log |
| 5 代码审核 | /tw:record-review | stage5_review.md |

元命令：/tw:record-auto、/tw:record-status；独立工具：/tw:record（不进状态机）。
<!-- tw:end -->"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project_root", help="宿主项目根目录")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    path = Path(args.project_root).expanduser().resolve() / "HANDOFF.md"

    if args.stdout:
        print(BLOCK)
        return 0
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if START in text and END in text:
            before = text.split(START, 1)[0]
            after = text.split(END, 1)[1]
            new_text = before + BLOCK + after
        else:
            new_text = text.rstrip() + "\n\n" + BLOCK + "\n"
    else:
        new_text = "# HANDOFF\n\n" + BLOCK + "\n"

    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != new_text:
            print("FAIL：HANDOFF.md 映射段缺失或漂移")
            return 1
        print("PASS：HANDOFF.md 映射段一致")
        return 0
    path.write_text(new_text, encoding="utf-8")
    print("已写入 " + str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
