"""Self-tests for demo2. Pure assert, no pytest dependency.

Run: python test_demo2.py
Exit 0 = all PASS, exit 1 = any FAIL.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

# Ensure demo2 package is importable (parent dir contains the demo2 package)
_pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _pkg_parent)

from demo2.roles import Theorist, Gatekeeper, RedTeam, FinalReviewer, Executor
from demo2.events import EventLog
from demo2.db import DecisionStore
from demo2.session import ReviewSession


PASS = 0
FAIL = 0


def check(label: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}")


# ---------------------------------------------------------------------------
# 1. Five seats produce non-empty comments
# ---------------------------------------------------------------------------

def test_seats_comment_nonempty():
    print("\n[1] 五席评论非空")
    item = {"case": "测试案例", "verdict": "Pass", "reasons": ["理由A", "理由B"], "evidence": ["证据1"]}
    seats = [Theorist(), Gatekeeper(), RedTeam(), FinalReviewer(), Executor()]
    for s in seats:
        c = s.comment(item)
        check(f"{s.display_name} 评论非空", len(c.strip()) > 0)


# ---------------------------------------------------------------------------
# 2. Gatekeeper holds on critical sample
# ---------------------------------------------------------------------------

def test_gatekeeper_hold_on_critical():
    print("\n[2] 门禁官对 critical 样例行使 hold 权")
    critical_item = {
        "case": "紧急案例",
        "reasons": ["critical: 密封面漏液", "普通理由"],
    }
    normal_item = {
        "case": "普通案例",
        "reasons": ["公差可接受", "补稳定性数据"],
    }
    g = Gatekeeper()
    check("critical 样例 → hold=True", g.hold(critical_item) is True)
    check("普通样例 → hold=False", g.hold(normal_item) is False)


# ---------------------------------------------------------------------------
# 3. Decision record persisted to SQLite
# ---------------------------------------------------------------------------

def test_decision_persisted():
    print("\n[3] 决议落库成功")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = os.path.join(tmp, "test_decisions.db")
        store = DecisionStore(db_path)
        record = {
            "time": "2026-11-03T00:00:00+00:00",
            "initiator": "Muse",
            "subject": "测试案例",
            "decision": "PASS",
            "basis": "测试依据",
            "status": "executed",
            "evidence_refs": ["E1"],
        }
        rid = store.insert(record, session_id="test-sess")
        check("insert 返回 row_id > 0", rid > 0)
        all_records = store.list_all()
        check("list_all 有 1 条记录", len(all_records) == 1)
        check("subject 匹配", all_records[0]["subject"] == "测试案例")
        check("decision 字段完整", all_records[0]["decision"] == "PASS")
        check("status 字段完整", all_records[0]["status"] == "executed")


# ---------------------------------------------------------------------------
# 4. Event log completeness
# ---------------------------------------------------------------------------

def test_event_log_completeness():
    print("\n[4] 事件流留痕完整")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        log_path = os.path.join(tmp, "events.jsonl")
        log = EventLog(log_path, "test-thread")
        log.log("POSTED", "chair", {"case": "x"})
        log.log("COMMENTED", "theorist", {})
        log.log("COMMENTED", "gatekeeper", {})
        log.log("HOLDED", "gatekeeper", {})
        log.log("FINALIZED", "final", {})
        log.log("DECISION_LOGGED", "executor", {})
        events = log.read_all()
        check("6 条事件全部写入", len(events) == 6)
        types = [e["type"] for e in events]
        check("事件类型序列正确", types == ["POSTED", "COMMENTED", "COMMENTED", "HOLDED", "FINALIZED", "DECISION_LOGGED"])
        check("每条事件有 timestamp", all("timestamp" in e for e in events))
        check("每条事件有 thread", all(e["thread"] == "test-thread" for e in events))


# ---------------------------------------------------------------------------
# 5. Full session run (auto mode, critical case → HOLD)
# ---------------------------------------------------------------------------

def test_full_session_critical():
    print("\n[5] 全流程自动跑（critical 案例 → HOLD 决议）")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        case = {
            "case": "阀体工艺变更评审",
            "verdict": "Fail",
            "reasons": ["critical: 密封面漏液", "critical: 未完成细胞毒性复测"],
            "evidence": ["QC-001"],
        }
        events_path = os.path.join(tmp, "events.jsonl")
        db_path = os.path.join(tmp, "decisions.db")
        sess = ReviewSession(case, events_path=events_path, db_path=db_path)
        summary = sess.run(auto=True)
        check("gated=True", summary["gated"] is True)
        check("decision=HOLD", summary["decision"] == "HOLD")
        check("row_id > 0", summary["row_id"] > 0)

        events = sess.events.read_all()
        event_types = [e["type"] for e in events]
        check("事件含 POSTED", "POSTED" in event_types)
        check("事件含 COMMENTED ×5", event_types.count("COMMENTED") == 5)
        check("事件含 HOLDED", "HOLDED" in event_types)
        check("事件含 FINALIZED", "FINALIZED" in event_types)
        check("事件含 DECISION_LOGGED", "DECISION_LOGGED" in event_types)


# ---------------------------------------------------------------------------
# 6. Full session run (normal case → PASS / Conditional)
# ---------------------------------------------------------------------------

def test_full_session_normal():
    print("\n[6] 全流程自动跑（普通案例 → 非 HOLD）")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        case = {
            "case": "BOM 物料替换评审",
            "verdict": "Conditional Pass",
            "reasons": ["公差可接受，需补稳定性数据"],
            "evidence": ["FMEA-014", "SGS-007"],
        }
        events_path = os.path.join(tmp, "events.jsonl")
        db_path = os.path.join(tmp, "decisions.db")
        sess = ReviewSession(case, events_path=events_path, db_path=db_path)
        summary = sess.run(auto=True)
        check("gated=False", summary["gated"] is False)
        check("decision != HOLD", summary["decision"] != "HOLD")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Demo2 自测 — 五席医械门禁评审会")
    print("=" * 60)

    test_seats_comment_nonempty()
    test_gatekeeper_hold_on_critical()
    test_decision_persisted()
    test_event_log_completeness()
    test_full_session_critical()
    test_full_session_normal()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"结果：{PASS}/{total} PASS，{FAIL} FAIL")
    print("=" * 60)
    sys.exit(0 if FAIL == 0 else 1)
