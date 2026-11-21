"""验收套件共用路径、命令执行和状态 fixture。"""

import datetime
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
PACKS = ROOT / "tw" / "packs"
TOOLS = ROOT / "tw" / "tools"
REC_TOOLS = ROOT / "tw" / "workflows" / "record-driven" / "tools"
VAL8 = str(TOOLS / "validate_workflow.py")
VALR = str(REC_TOOLS / "validate_record_workflow.py")
GEN8 = str(TOOLS / "gen_dispatchers.py")
GENR = str(REC_TOOLS / "gen_record_dispatchers.py")
HANDOFF = str(TOOLS / "gen_handoff.py")

KEYS8 = ["1_business", "2_data", "3_assertion", "4_case",
         "5_verify", "6_e2e", "7_report", "8_kb_feedback"]
KEYSR = ["1_capture", "2_casegen", "3_case", "4_run", "5_review"]
ART8 = {
    "1_business": ["stage1_business.md", "stage1_cases.md", "stage1_cases.json"],
    "2_data": ["stage2_data.md"],
    "3_assertion": ["stage3_assertions.md", "stage3_assertions.json"],
    "4_case": ["stage4_plan.md", "stage4_files.md"],
    "5_verify": ["stage5_verify.log"],
    "6_e2e": ["stage6_e2e.md"],
    "7_report": ["stage7_report.md"],
    "8_kb_feedback": ["stage8_kb_feedback.md"],
}
ARTR = {
    "1_capture": ["stage1_record.md"],
    "2_casegen": ["stage2_cases.md", "stage2_cases.json"],
    "3_case": ["stage3_plan.md", "stage3_files.md"],
    "4_run": ["stage4_run.log"],
    "5_review": ["stage5_review.md"],
}
NOW = datetime.datetime.now().isoformat()


# --------------------------------------------------------------------------
# 基础设施
# --------------------------------------------------------------------------
def py(*args, cwd=None, env=None, timeout=60):
    """运行 python 脚本，返回 (rc, 合并输出)。"""
    try:
        r = subprocess.run([sys.executable, *map(str, args)], cwd=cwd,
                           env=env, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def cli(*args, cwd=None, env=None, timeout=120):
    """运行外部命令，返回 (rc, 合并输出)。"""
    try:
        r = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, "command not found: %s" % args[0]
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def clean(out):
    """从校验器输出里提取 ERROR / WARNING 数量。

    注意：校验器成功时也会打印 'PASS：0 ERROR / 0 WARNING'，因此不能用
    子串计数，只认行首的 ERROR / WARNING 行（真实诊断行的格式）。
    """
    return (len(re.findall(r"(?m)^\s*ERROR\b", out)),
            len(re.findall(r"(?m)^\s*WARNING\b", out)))


def has_issue(out):
    e, w = clean(out)
    return bool(e or w)


def expect_ok(rc, out, strict=False):
    if rc != 0:
        return False, "rc=%d | %s" % (rc, out.replace("\n", " / ")[:170])
    e, w = clean(out)
    if e or (strict and w):
        return False, "ERROR=%d WARNING=%d | %s" % (e, w, out.replace("\n", " / ")[:150])
    return True, "PASS / 0 ERROR / %d WARNING" % w


def expect_fail(rc, out, keyword=None):
    if rc == 0:
        return False, "期望失败但 rc=0 | %s" % out.replace("\n", " / ")[:150]
    if keyword and keyword not in out:
        return False, "rc=%d 但缺关键字 %r | %s" % (rc, keyword, out.replace("\n", " / ")[:150])
    return True, "按预期拦截 rc=%d%s" % (rc, (" / " + keyword) if keyword else "")


def skill_dirs():
    return sorted([p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").exists()])


def skill_names():
    return [p.name for p in skill_dirs()]


def read(path):
    return Path(path).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# fixture 构造器（严格贴合两个校验器的字段规则）
# --------------------------------------------------------------------------
def write_8(feat, statuses, cur, mode="manual", bypasses=None, stage_extra=None,
            dashboard=True, artifacts=True):
    """写一个 8 阶段 state.json + dashboard + 产出文件；返回 wf_dir。"""
    wf = feat.parent
    wf.mkdir(parents=True, exist_ok=True)
    feat.mkdir(parents=True, exist_ok=True)
    stages = {}
    for i, (key, status) in enumerate(zip(KEYS8, statuses), start=1):
        hi = False if status in {"done", "skipped"} else None
        entry = {"status": status, "human_intervention": hi,
                 "intervention_note": None}
        if status == "in_progress":
            entry["started_at"] = NOW
        if status == "done":
            entry["done_at"] = NOW
        if stage_extra and key in stage_extra:
            entry.update(stage_extra[key])
        stages[key] = entry
        if artifacts and status == "done":
            for art in ART8[key]:
                (feat / art).write_text("# fixture 产出\n", encoding="utf-8")
    state = {"feature": feat.name, "created": NOW, "mode": mode,
             "current_stage": cur, "stages": stages,
             "bypasses": bypasses or []}
    (feat / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    (wf / ".current").write_text(feat.name + "\n", encoding="utf-8")
    if dashboard:
        done = all(s in {"done", "skipped"} for s in statuses)
        header = "**1 / 1 完成** | **0 进行中** | **0 未启动**" if done else \
                 "**0 / 1 完成** | **1 进行中** | **0 未启动**"
        (wf / "dashboard.md").write_text(
            "# %s 看板\n\n%s\n\n## 进行中\n| feature |\n|---|\n| %s |\n"
            % (feat.name, header, feat.name), encoding="utf-8")
    return wf


def write_rec(feat, statuses, cur, mode="manual", bypasses=None, stage_extra=None,
              dashboard=True, artifacts=True):
    """写一个录制 record_state.json + dashboard + 产出文件；返回 rwf_dir。"""
    wf = feat.parent
    wf.mkdir(parents=True, exist_ok=True)
    feat.mkdir(parents=True, exist_ok=True)
    stages = {}
    for key, status in zip(KEYSR, statuses):
        hi = False if status in {"done", "skipped"} else None
        entry = {"status": status, "human_intervention": hi,
                 "intervention_note": None}
        if status == "in_progress":
            entry["started_at"] = NOW
        if stage_extra and key in stage_extra:
            entry.update(stage_extra[key])
        stages[key] = entry
        if artifacts and status == "done":
            for art in ARTR[key]:
                (feat / art).write_text("# fixture 产出\n", encoding="utf-8")
    state = {"feature": feat.name, "workflow": "record-driven", "created": NOW,
             "mode": mode, "current_stage": cur, "stages": stages,
             "bypasses": bypasses or []}
    (feat / "record_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    (wf / ".current").write_text(feat.name + "\n", encoding="utf-8")
    if dashboard:
        done = all(s in {"done", "skipped"} for s in statuses)
        header = "**1 / 1 完成** | **0 进行中** | **0 未启动**" if done else \
                 "**0 / 1 完成** | **1 进行中** | **0 未启动**"
        (wf / "dashboard.md").write_text(
            "# %s 录制看板\n\n%s\n\n## 进行中\n| feature |\n|---|\n| %s |\n"
            % (feat.name, header, feat.name), encoding="utf-8")
    return wf


def fresh_8(tmp, feature="demo"):
    feat = Path(tmp) / ".claude" / "workflows" / feature
    return feat


def fresh_rec(tmp, feature="demo"):
    feat = Path(tmp) / ".claude" / "record-workflows" / feature
    return feat


def base8_statuses(cur):
    """阶段 1..cur-1 done，cur in_progress，其余 pending。"""
    out = []
    for i in range(1, 9):
        out.append("done" if i < cur else ("in_progress" if i == cur else "pending"))
    return out


def baseR_statuses(cur):
    out = []
    for i in range(1, 6):
        out.append("done" if i < cur else ("in_progress" if i == cur else "pending"))
    return out


def v8(wf, strict=True):
    args = [VAL8, "--workflows-dir", str(wf)]
    if strict:
        args.append("--strict")
    return py(*args)


def vr(wf, strict=True):
    args = [VALR, "--workflows-dir", str(wf)]
    if strict:
        args.append("--strict")
    return py(*args)
