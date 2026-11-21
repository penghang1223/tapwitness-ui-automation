"""工作流状态、隔离和产物验收。"""

import copy
import json
import shutil
import tempfile
from pathlib import Path

from .common import (
    GEN8, GENR, KEYS8, KEYSR, NOW, PACKS, ROOT, SKILLS, TOOLS, VAL8, VALR,
    base8_statuses, baseR_statuses, clean, expect_fail, expect_ok, fresh_8,
    fresh_rec, has_issue, py, read, v8, vr, write_8, write_rec,
)


def c_fixture8():
    with tempfile.TemporaryDirectory(prefix="twf8-") as tmp:
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1)
        rc, out = v8(wf, strict=True)
        return expect_ok(rc, out, strict=True)


def c_fixtureR():
    with tempfile.TemporaryDirectory(prefix="twfr-") as tmp:
        feat = fresh_rec(tmp)
        wf = write_rec(feat, baseR_statuses(1), 1)
        rc, out = vr(wf, strict=True)
        return expect_ok(rc, out, strict=True)


def c_default_path():
    with tempfile.TemporaryDirectory(prefix="twdef-") as tmp:
        root = Path(tmp)
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1)
        # 显式
        rc1, out1 = py(VAL8, "--workflows-dir", str(wf), "--strict")
        # 默认（CWD = 宿主项目根）
        rc2, out2 = py(VAL8, "--strict", cwd=str(root))
        # 相对路径
        rc3, out3 = py(VAL8, "--workflows-dir", ".claude/workflows", "--strict", cwd=str(root))
        ok = rc1 == rc2 == rc3 == 0 and all(not has_issue(o) for o in (out1, out2, out3))
        return ok, ("PASS / 默认 CWD 路径 == 显式路径 == 相对路径") if ok else \
            "FAIL / rc=%s,%s,%s | %s" % (rc1, rc2, rc3, (out1 + out2 + out3)[:150])


def c_missing_dir_error():
    with tempfile.TemporaryDirectory(prefix="twempty-") as tmp:
        rc, out = py(VAL8, cwd=tmp)
        return expect_fail(rc, out, "工作流目录不存在")


def c_isolation():
    with tempfile.TemporaryDirectory(prefix="twiso-") as tmp:
        root = Path(tmp)
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1)
        # 旁挂一份故意损坏的录制状态树，8 阶段校验器必须完全忽略
        rwf = root / ".claude" / "record-workflows"
        bad = rwf / "broken"
        bad.mkdir(parents=True)
        (rwf / ".current").write_text("broken\n", encoding="utf-8")
        (bad / "record_state.json").write_text('{"broken": true}', encoding="utf-8")
        rc, out = py(VAL8, "--strict", cwd=str(root))
        return expect_ok(rc, out, strict=True)


def c_dashboard_missing():
    with tempfile.TemporaryDirectory(prefix="twdash-") as tmp:
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1, dashboard=False)
        rc, out = v8(wf, strict=False)
        return expect_fail(rc, out, "dashboard.md 不存在")


def negative8(mutator, keyword=None, strict=True):
    with tempfile.TemporaryDirectory(prefix="twneg8-") as tmp:
        feat = fresh_8(tmp)
        wf = write_8(feat, base8_statuses(1), 1)
        state = json.loads(read(feat / "state.json"))
        mutator(state, feat)
        (feat / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
        rc, out = v8(wf, strict=strict)
        return expect_fail(rc, out, keyword)


def c_neg_stage_drift():
    def m(s, f):
        s["current_stage"] = 3
    return negative8(m, "不自洽")


def c_neg_string_hi():
    def m(s, f):
        s["stages"]["1_business"]["human_intervention"] = "true"
    return negative8(m, "字符串")


def c_neg_skipped_no_bypass():
    def m(s, f):
        e = s["stages"]["2_data"]
        e["status"] = "skipped"
        e["human_intervention"] = False
    return negative8(m, "bypasses")


def c_neg_short_reason():
    def m(s, f):
        e = s["stages"]["2_data"]
        e["status"] = "skipped"
        e["human_intervention"] = False
        s["bypasses"] = [{"stage": 2, "reason": "no", "timestamp": NOW}]
    return negative8(m, "5 字符")


def c_neg_verify_failed():
    bad = []
    with tempfile.TemporaryDirectory(prefix="twfail-") as tmp:
        feat = fresh_8(tmp)
        st = ["done"] * 4 + ["failed"] + ["pending"] * 3
        for mode, expected in (("manual", 4), ("semi-auto", 4), ("full-auto", 5)):
            for current_stage in (4, 5):
                wf = write_8(feat, st, current_stage, mode=mode)
                rc, out = v8(wf)
                if current_stage == expected:
                    ok, detail = expect_ok(rc, out, strict=True)
                else:
                    ok = rc == 1 and "不自洽（应为 %s）" % expected in out
                    detail = out
                if not ok:
                    bad.append("%s/%s: %s" % (mode, current_stage, detail))
        inconsistent = ["in_progress"] + ["pending"] * 3 + ["failed"] + ["pending"] * 3
        wf = write_8(feat, inconsistent, 4, mode="manual")
        rc, out = v8(wf, strict=True)
        if rc != 1 or "不自洽（应为 1）" not in out:
            bad.append("前置阶段未完成时不能回拨至 4: %s" % out)
    return not bad, "PASS / manual、semi-auto 回拨 4，full-auto 停 5" if not bad else bad[0]


def c_neg_malformed_state():
    fixtures = [
        (fresh_8, write_8, v8, "state.json", base8_statuses(1), KEYS8[0]),
        (fresh_rec, write_rec, vr, "record_state.json", baseR_statuses(1), KEYSR[0]),
    ]
    for feature, writer, validate, name, statuses, stage in fixtures:
        with tempfile.TemporaryDirectory(prefix="twmalformed-") as tmp:
            feat = feature(tmp)
            wf = writer(feat, statuses, 1)
            path = feat / name
            original = json.loads(read(path))
            mutations = [
                ("顶层不是对象", []),
                ("stages 不是对象", dict(original, stages=[])),
                ("%s 不是对象" % stage, dict(original, stages={**original["stages"], stage: None})),
                ("mode 非法", dict(original, mode=[])),
            ]
            for field, value, keyword in (
                ("status", {}, "status 非法"),
                ("human_intervention", 0, "必须为布尔或 null"),
                ("review_needed", "true", "review_needed 必须是布尔"),
            ):
                state = copy.deepcopy(original)
                state["stages"][stage][field] = value
                mutations.append((keyword, state))
            state = copy.deepcopy(original)
            state.update(current_stage=2, bypasses=[{"stage": True, "reason": "人工跳过阶段一", "timestamp": NOW}])
            state["stages"][stage].update(status="skipped", human_intervention=False)
            mutations.append(("bypass.stage 非法", state))
            cases = [("无法解析", "{")] + [(keyword, json.dumps(state)) for keyword, state in mutations]
            for keyword, data in cases:
                path.write_text(data, encoding="utf-8")
                rc, out = validate(wf, strict=False)
                if rc != 1 or keyword not in out or "FAIL：" not in out or "Traceback" in out:
                    return False, "%s / %s / %s" % (name, keyword, out[:220])
    return True, "PASS / 两套状态机均给出 ERROR 和汇总"


def c_structured_artifacts():
    tool = TOOLS / "validate_artifacts.py"
    for protocol, update in ((ROOT / "tw/protocols/gate-protocol.md", "3. **更新状态**"),
                             (ROOT / "tw/workflows/record-driven/protocols/gate-protocol.md", "3. 更新状态")):
        text = read(protocol)
        if ("validate_artifacts.py" not in text or "非零退出码即停止" not in text
                or update not in text or text.index("validate_artifacts.py") > text.index(update)):
            return False, "%s 未在状态更新前要求产物校验" % protocol
    with tempfile.TemporaryDirectory(prefix="twartifacts-") as tmp:
        feat = Path(tmp) / "demo"
        feat.mkdir()
        plan = {"precondition_data": "待确认", "data_source": "待确认", "setup": [],
                "cleanup": [], "isolation_key": "demo", "verified": False}
        case = {"id": "TC01", "category": "正向", "evidence_level": "confirmed",
                "evidence": "用户确认", "data_plan": plan}
        cases = {"feature": "demo", "workflow": "8-stage", "expansion_mode": "full",
                 "evidence": {"degraded": False}, "cases": [case]}
        assertion = {"id": "A-001", "case_id": "TC01", "route": ["UI"],
                     "severity": "A", "assertion_type": "hard"}
        assertions = {"feature": "demo", "assertions": [assertion]}
        first = feat / "stage1_cases.json"
        third = feat / "stage3_assertions.json"
        record = feat / "stage2_cases.json"
        def save(path, data):
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        def validate(workflow, stage):
            return py(tool, "--workflow", workflow, "--feature-dir", feat, "--stage", stage)
        save(first, cases)
        save(third, assertions)
        recorded = copy.deepcopy(cases)
        recorded.update(workflow="record-driven", expansion_mode="single")
        save(record, recorded)
        for workflow, stage in (("8-stage", 1), ("8-stage", 3), ("record-driven", 2)):
            rc, out = validate(workflow, stage)
            if rc != 0:
                return False, "合法产出被拒绝 %s/%s: %s" % (workflow, stage, out)
        cases["cases"][0]["evidence_level"] = "assumed"
        save(first, cases)
        rc, out = validate("8-stage", 1)
        if rc != 1 or "evidence_level" not in out:
            return False, "未拦截无依据用例: %s" % out
        cases["cases"][0].update(evidence_level="inferred", category="负面", evidence="")
        cases["evidence"]["degraded"] = True
        save(first, cases)
        rc, out = validate("8-stage", 1)
        if rc != 1 or "降级时只允许正向" not in out or "缺少 evidence" not in out:
            return False, "未拦截降级或缺少依据: %s" % out
        recorded["cases"].append(copy.deepcopy(recorded["cases"][0]))
        save(record, recorded)
        rc, out = validate("record-driven", 2)
        if rc != 1 or "恰有一条" not in out or "id 重复" not in out:
            return False, "未拦截 single 多用例或重复 ID: %s" % out
        assertion["case_id"] = "TC99"
        assertion["route"] = "UI"
        save(third, assertions)
        rc, out = validate("8-stage", 3)
        if rc != 1 or "不存在的用例" not in out or "route" not in out:
            return False, "未拦截断言引用或类型错误: %s" % out
        third.write_text("{", encoding="utf-8")
        rc, out = validate("8-stage", 3)
        if rc != 1 or "无法解析" not in out or "Traceback" in out:
            return False, "损坏 JSON 未返回诊断: %s" % out
        first.unlink()
        assertion.update(case_id="TC01", route=["UI"])
        save(third, assertions)
        rc, out = validate("8-stage", 3)
        if rc != 0 or "无法对账" not in out:
            return False, "缺少历史用例清单时应告警: %s" % out
    return True, "PASS / 三阶段产物、跨文件引用与兼容告警"


def c_neg_record_drift_and_rework():
    results = []
    with tempfile.TemporaryDirectory(prefix="twnegr-") as tmp:
        feat = fresh_rec(tmp)
        wf = write_rec(feat, baseR_statuses(1), 1)
        state = json.loads(read(feat / "record_state.json"))
        # 1) 自洽漂移 → ERROR
        state["current_stage"] = 3
        (feat / "record_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
        rc, out = vr(wf, strict=False)
        results.append(expect_fail(rc, out, "不自洽"))
        # 2) rework_round=3 → WARNING（非 strict 放行，strict 拦下）
        state["current_stage"] = 1
        state["stages"]["3_case"]["rework_round"] = 3
        (feat / "record_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
        rc2, out2 = vr(wf, strict=False)
        rc3, out3 = vr(wf, strict=True)
        ok2 = rc2 == 0 and clean(out2)[1] > 0 and rc3 == 1
        results.append((ok2, "PASS / rework_round=3 非 strict 放行、strict 升级失败") if ok2
                       else "FAIL / rc=%d,%d %s" % (rc2, rc3, (out2 + out3)[:120]))
    ok = all(r[0] for r in results)
    return ok, ("PASS / 录制漂移 ERROR + rework WARNING 分级") if ok else \
        "FAIL / " + " ; ".join(r[1] for r in results)


def c_neg_dispatcher_drift():
    with tempfile.TemporaryDirectory(prefix="twdispatcher-") as tmp:
        plugin = isolated_plugin(tmp)
        target = plugin / "skills/business-context/SKILL.md"
        target.write_text(read(target) + "\nDRIFT\n", encoding="utf-8")
        rc, out = py(plugin / Path(GEN8).relative_to(ROOT), "--check")
        return expect_fail(rc, out, "漂移")


def c_neg_undeclared_pack_file():
    with tempfile.TemporaryDirectory(prefix="twpack-") as tmp:
        pack = Path(tmp) / "playwright-python"
        shutil.copytree(PACKS / pack.name, pack)
        (pack / "references/undeclared.md").write_text("# 未声明\n", encoding="utf-8")
        rc, out = py(VAL8, "--check-pack", pack, "--strict")
        return expect_fail(rc, out, "未声明")


def isolated_plugin(tmp):
    plugin = Path(tmp) / "plugin"
    shutil.copytree(SKILLS, plugin / "skills")
    shutil.copytree(ROOT / "tw", plugin / "tw")
    return plugin


def c_neg_rogue_dispatchers():
    with tempfile.TemporaryDirectory(prefix="twrogue-") as tmp:
        plugin = isolated_plugin(tmp)
        rogue = plugin / "skills/rogue"
        rogue.mkdir()
        for generator, marker in ((GEN8, "TW 阶段"), (GENR, "TW 录制阶段")):
            for stage in (1, 9):
                (rogue / "SKILL.md").write_text(
                    "---\nname: rogue\ndescription: '[%s%s]'\n---\n" % (marker, stage), encoding="utf-8")
                rc, out = py(plugin / Path(generator).relative_to(ROOT), "--check")
                if rc != 1 or "覆盖护栏失败：rogue" not in out:
                    return False, "%s%s / %s" % (marker, stage, out)
    return True, "PASS / 两套生成器均拦截冒用有效阶段号与越界阶段号"


def c_neg_manifest_drift():
    import yaml

    with tempfile.TemporaryDirectory(prefix="twmanifest-") as tmp:
        plugin = isolated_plugin(tmp)
        pack = plugin / "tw/packs/playwright-python"
        pack_yaml = pack / "pack.yaml"
        cfg = yaml.safe_load(read(pack_yaml))
        cfg["artifacts"]["1"].append("extra-evidence.json")
        pack_yaml.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
        rc, out = py(VAL8, "--check-pack", pack, "--strict")
        if rc != 0:
            return False, "域包扩展产出未被接受 / %s" % out
        cfg["artifacts"]["1"] = ["renamed.md"]
        cfg["stages"]["1"]["file"] = "stages"
        cfg["stages"]["4"]["references"] = "references/page_object_guide.md"
        cfg["kb"]["recall_protocol"] = "../../protocols/gate-protocol.md"
        pack_yaml.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
        rc, out = py(VAL8, "--check-pack", pack)
        required = ("artifacts.1", "槽位 1 file", "references 必须是路径数组", "kb.recall_protocol")
        if rc != 1 or not all(key in out for key in required):
            return False, "pack.yaml / %s" % out

        workflow_yaml = plugin / "tw/workflows/record-driven/workflow.yaml"
        cfg = yaml.safe_load(read(workflow_yaml))
        cfg["artifacts"]["4"].append("extra-evidence.json")
        workflow_yaml.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
        rc, out = py(plugin / Path(VALR).relative_to(ROOT), "--check-workflow", "--strict")
        if rc != 0:
            return False, "录制工作流扩展产出未被接受 / %s" % out
        cfg["artifacts"]["4"] = ["renamed.log"]
        cfg["stages"]["2"]["references"] = ["../../protocols/missing.md"]
        cfg["stages"]["5"]["references"] = ["references/missing.md"]
        cfg["applies_to_packs"].append("ios-appium")
        workflow_yaml.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
        rc, out = py(plugin / Path(VALR).relative_to(ROOT), "--check-workflow")
        required = ("artifacts.4", "不是有效共用协议", "playwright-python 槽位 5 references",
                    "ios-appium 槽位 1 pack_path")
        if rc != 1 or not all(key in out for key in required):
            return False, "workflow.yaml / %s" % out
    return True, "PASS / 允许扩展产出，拦截必需产出、引用与逐域包实现漂移"


def c_e2e_8_stages():
    failures = []
    with tempfile.TemporaryDirectory(prefix="twe2e8-") as tmp:
        feat = fresh_8(tmp)
        for cur in range(1, 10):
            statuses = base8_statuses(9) if cur == 9 else base8_statuses(cur)
            wf = write_8(feat, statuses, cur)
            rc, out = v8(wf, strict=True)
            if rc != 0 or has_issue(out):
                failures.append("cur=%d rc=%d %s" % (cur, rc, out.replace("\n", " / ")[:100]))
    return (not failures), ("PASS / 8 阶段 1→9 逐步推进 9/9 快照全绿（含产出物与看板对账）") \
        if not failures else "FAIL / " + "; ".join(failures[:3])


def c_e2e_bypass():
    with tempfile.TemporaryDirectory(prefix="twbyp-") as tmp:
        feat = fresh_8(tmp)
        st = ["done", "skipped", "in_progress"] + ["pending"] * 5
        bypass = [{"stage": 2, "reason": "冒烟跳过阶段2", "timestamp": NOW}]
        wf = write_8(feat, st, 3, bypasses=bypass)
        rc, out = v8(wf, strict=True)
        state = json.loads(read(feat / "state.json"))
        ok = rc == 0 and state["stages"]["2_data"]["status"] == "skipped" \
             and state["current_stage"] == 3 and len(state["bypasses"]) == 1
        return ok, ("PASS / bypass 3 只跳过阶段 2（target_stage-1）并留 reason") if ok else \
            "FAIL / rc=%d %s" % (rc, out.replace("\n", " / ")[:150])


def c_e2e_tristate():
    """§4.3 审查门三值模型：批准 / edit / exit / full-auto 四种回写均合法。"""
    combos = [
        ("批准", False, False, False),
        ("edit/skip/accept", True, False, False),
        ("exit", None, True, False),
        ("full-auto", False, True, True),
    ]
    bad = []
    with tempfile.TemporaryDirectory(prefix="twtri-") as tmp:
        feat = fresh_8(tmp)
        for label, hi, review, is_full in combos:
            entry = {"status": "in_progress", "human_intervention": hi,
                     "intervention_note": ("人工编辑用例" if hi is True else None),
                     "review_needed": review}
            wf = write_8(feat, base8_statuses(1), 1,
                         mode="full-auto" if is_full else "manual",
                         stage_extra={"1_business": entry})
            rc, out = v8(wf, strict=True)
            if rc != 0 or has_issue(out):
                bad.append("%s: %s" % (label, out.replace("\n", " / ")[:100]))
        wf = write_8(feat, base8_statuses(2), 2, mode="semi-auto",
                     stage_extra={"1_business": {"review_needed": True}})
        rc, out = v8(wf, strict=True)
        if rc != 0 or has_issue(out):
            bad.append("8 阶段审查门退出: %s" % out.replace("\n", " / ")[:100])
        record_feat = fresh_rec(tmp)
        rwf = write_rec(record_feat, baseR_statuses(3), 3, mode="semi-auto",
                        stage_extra={"2_casegen": {"review_needed": True}})
        rc, out = vr(rwf, strict=True)
        if rc != 0 or has_issue(out):
            bad.append("录制审查门退出: %s" % out.replace("\n", " / ")[:100])
    return (not bad), ("PASS / 三值模型 4 种回写全部合法") if not bad else "FAIL / " + "; ".join(bad[:2])


def c_e2e_record_stages():
    failures = []
    with tempfile.TemporaryDirectory(prefix="twe2er-") as tmp:
        feat = fresh_rec(tmp)
        for cur in range(1, 7):
            statuses = baseR_statuses(6) if cur == 6 else baseR_statuses(cur)
            wf = write_rec(feat, statuses, cur)
            rc, out = vr(wf, strict=True)
            if rc != 0 or has_issue(out):
                failures.append("cur=%d rc=%d %s" % (cur, rc, out.replace("\n", " / ")[:100]))
    return (not failures), ("PASS / 录制 1→6 逐步推进 6/6 快照全绿") if not failures \
        else "FAIL / " + "; ".join(failures[:3])


def c_e2e_record_rollback():
    with tempfile.TemporaryDirectory(prefix="twroll-") as tmp:
        feat = fresh_rec(tmp)
        st = ["done", "done", "done", "failed", "pending"]
        wf = write_rec(feat, st, 4,
                       stage_extra={"3_case": {"rework_round": 1}})
        rc, out = vr(wf, strict=True)
        ok = rc == 0 and not has_issue(out)
        return ok, ("PASS / 4_run failed 停在 4、rework_round=1 合法") if ok else \
            "FAIL / rc=%d %s" % (rc, out.replace("\n", " / ")[:150])
