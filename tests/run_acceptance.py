#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TW 工作流框架验收入口，支持 --quick 和 --official。"""
import argparse
import sys

from acceptance import contracts, feedback, official, workflow
from acceptance.common import ROOT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


STATIC = [
    ("Phase 0", "manifest JSON 与 license", contracts.c_manifests),
    ("Phase 2", "31 个 SKILL.md frontmatter 与目录名一致", contracts.c_skill_frontmatter),
    ("Phase 8", "README 命令数/域包表与实际一致", contracts.c_readme_consistency),
    ("Phase 1", "§15.1 关键文件清单齐全", contracts.c_required_files),
    ("Phase 1", "JSON 模板与反馈注册表可解析", contracts.c_json_assets),
    ("Phase 2", "8 阶段分发器生成器 --check", contracts.c_gen8_check),
    ("Phase 5", "录制分发器生成器 --check", contracts.c_genr_check),
    ("Phase 7", "--check-pack --strict（4 域包 C1/C2/C5/C2R）", contracts.c_check_pack_strict),
    ("Phase 6", "--check-pack 单包 playwright-python", contracts.c_check_pack_single),
    ("Phase 4", "--check-profile-contract", contracts.c_profile_contract),
    ("Phase 4", "--check-dump-contract", contracts.c_dump_contract),
    ("Phase 5", "--check-workflow（录制定义 W3R/W8）", contracts.c_record_workflow_def),
    ("§13", "8+5 分发器零耦合静态扫描", contracts.c_zero_coupling),
    ("§13", "能力键门控（无硬编码 pack 白名单）", contracts.c_capability_gating),
    ("§13", "两个校验器互不 import", contracts.c_no_cross_import),
    ("§13", "工具 UTF-8 重配置 + __file__ 路径", contracts.c_tool_hygiene),
    ("§13", "yaml.safe_load 有 dict 守卫", contracts.c_yaml_guard),
    ("§13", ".gitignore 覆盖运行时产物", contracts.c_gitignore),
    ("§13", "阶段指令六段结构 + Exit Gate 收束", contracts.c_six_sections),
    ("§13", "4 域包/坑点库；录制子树仅 playwright-python", contracts.c_packs_and_subtree),
    ("Phase 3", "gen_handoff 保留手写/双标记/幂等/--check", contracts.c_handoff),
]

FIXTURE = [
    ("Phase 4", "8 阶段 fixture 0 ERROR / 0 WARNING", workflow.c_fixture8),
    ("Phase 5", "录制 fixture 0 ERROR", workflow.c_fixtureR),
    ("Phase 5", "默认 CWD 路径 == 显式 == 相对路径", workflow.c_default_path),
    ("§10.3", "无 CWD 工作流目录 → ERROR（禁止回落）", workflow.c_missing_dir_error),
    ("§13", "两套工作流隔离（忽略损坏的录制状态树）", workflow.c_isolation),
    ("Phase 4", "dashboard 缺失 → ERROR", workflow.c_dashboard_missing),
]

NEGATIVE = [
    ("反向", "current_stage 自洽漂移 → 拦截", workflow.c_neg_stage_drift),
    ("反向", "human_intervention 字符串 → 拦截", workflow.c_neg_string_hi),
    ("反向", "skipped 无 bypass → 拦截", workflow.c_neg_skipped_no_bypass),
    ("反向", "bypass.reason < 5 字符 → 拦截", workflow.c_neg_short_reason),
    ("反向", "5_verify=failed 按模式停在 4 或 5", workflow.c_neg_verify_failed),
    ("反向", "损坏状态与非法类型输出诊断", workflow.c_neg_malformed_state),
    ("反向", "结构化产物与用例引用校验", workflow.c_structured_artifacts),
    ("反向", "录制漂移 ERROR + rework WARNING 分级", workflow.c_neg_record_drift_and_rework),
    ("反向", "分发器被篡改 → 生成器 --check 拦截", workflow.c_neg_dispatcher_drift),
    ("反向", "域包未声明 md → --check-pack --strict 拦截", workflow.c_neg_undeclared_pack_file),
    ("反向", "手写分发器冒用阶段标记 → 覆盖护栏拦截", workflow.c_neg_rogue_dispatchers),
    ("反向", "清单产出与引用漂移 → 拦截", workflow.c_neg_manifest_drift),
]

E2E = [
    ("Phase 9*", "8 阶段 1→9 全流转 9/9 快照全绿", workflow.c_e2e_8_stages),
    ("Phase 9*", "bypass 3 只跳过阶段 2（target_stage-1）", workflow.c_e2e_bypass),
    ("Phase 9*", "审查门三值模型 4 种回写均合法", workflow.c_e2e_tristate),
    ("Phase 9*", "录制 1→6 全流转 6/6 快照全绿", workflow.c_e2e_record_stages),
    ("Phase 9*", "录制 4_run failed 回拨停在 4 合法", workflow.c_e2e_record_rollback),
]

CLAUSES = [
    ("§13", "§4.3 四套 mode 失败分支 6 行齐全", contracts.c_clause_gate_modes),
    ("§13", "§4.4 两类暂停门与 [skip] 语义", contracts.c_clause_pause_types),
    ("§13", "阶段 1 三道门顺序（协议 + 4 域包）", contracts.c_clause_three_gates_order),
    ("§13", "阶段 4 分级采集 / DOM 冲突对照", contracts.c_clause_stage4_discipline),
    ("§13", "阶段 5/6 探查修复与 flaky 四步", contracts.c_clause_stage5_6_discipline),
    ("§13", "证据纪律 7 条引用关系", contracts.c_clause_evidence_refs),
    ("§13", "--full 3 类必停 + 2 类确定性处理", contracts.c_clause_full_safety),
    ("§14", "域包正文不写状态文件（人工评审兜底）", contracts.c_clause_pack_no_state_write),
    ("§14", "域包只引用协议章节号", contracts.c_clause_section_refs),
    ("§13", "发布版本一致性（git tag 静态代理）", contracts.c_release_version_contract),
]

OFFICIAL = [
    ("官方", "claude plugin validate 识别 31 skills", official.c_official_validate),
    ("官方", "validate --profile directory 通过", official.c_official_directory_profile),
    ("官方", "隔离 marketplace add + install（不污染用户配置）", official.c_official_isolated_install),
    ("官方", "真实 -p 会话可见 31 个命令", official.c_official_session_visibility),
    ("官方", "真实会话执行 /tw:new-feature 并落盘校验", official.c_official_session_new_feature),
]

FEEDBACK = [
    ("反馈", "两份 profile 指向真实仓库且契约通过", feedback.c_fb_profile_points_to_repo),
    ("反馈", "GitHub Issue Form 字段/标签/标题前缀齐全", feedback.c_fb_issue_form),
    ("反馈", "/tw:feedback 调用提交脚本并含降级与脱敏", feedback.c_fb_skill_calls_submitter),
    ("反馈", "提交脚本零第三方依赖且含全部安全开关", feedback.c_fb_script_static),
    ("反馈", "dry-run 实跑：脱敏生效且零外部写", feedback.c_fb_dry_run_sanitizes),
    ("反馈", "auto_submit=false 强制只预览", feedback.c_fb_no_submit_when_disabled),
    ("反馈", "提交结果不明和队列恢复", feedback.c_fb_submit_recovery),
    ("反馈", "4 份 stage8 指向自动提交通道", feedback.c_fb_pack_stage8_refs),
]

GROUPS = [
    ("静态契约", STATIC),
    ("§13/§14 条款守护", CLAUSES),
    ("状态机 fixture 与隔离", FIXTURE),
    ("反向破坏（校验器真的会拦）", NEGATIVE),
    ("端到端状态流转模拟", E2E),
    ("反馈提交 Issue", FEEDBACK),
    ("Claude Code 官方 CLI 冒烟", OFFICIAL),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="只跑静态契约组")
    ap.add_argument("--official", action="store_true", help="追加官方 CLI 冒烟组")
    args = ap.parse_args()

    print("TW 工作流框架 · 可复现验收套件")
    print("仓库: %s" % ROOT)
    print("模式: %s" % ("quick" if args.quick else
                       ("full+official" if args.official else "full")))
    print("=" * 78)

    groups = [GROUPS[0]] if args.quick else \
             GROUPS if args.official else GROUPS[:-1]

    passed = failed = skipped = 0
    failures = []
    for gname, cases in groups:
        print("\n[%s]  (%d 项)" % (gname, len(cases)))
        for phase, name, fn in cases:
            try:
                result = fn()
                if isinstance(result, tuple):
                    ok, detail = result
                else:
                    ok, detail = bool(result), ""
            except Exception as exc:
                ok, detail = False, "用例异常 %s: %s" % (type(exc).__name__, exc)
            if ok is None:
                skipped += 1
                tag = "SKIP"
            elif ok:
                passed += 1
                tag = "PASS"
            else:
                failed += 1
                tag = "FAIL"
                failures.append("[%s] %s → %s" % (gname, name, detail))
            print("  %-4s  %-9s %-52s %s" % (tag, phase, name, detail[:105]))

    print("\n" + "=" * 78)
    print("汇总: %d PASS / %d FAIL / %d SKIP" % (passed, failed, skipped))
    if failures:
        print("\n失败明细:")
        for f in failures:
            print("  - " + f)
    print("FINAL: %s" % ("ALL PASS" if failed == 0 else "HAS FAILURES"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
