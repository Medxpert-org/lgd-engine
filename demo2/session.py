"""Main session flow for the five-seat gate review meeting.

Usage:
    python -m demo2.session --case case_gate_report.json          # interactive
    python -m demo2.session --case case_gate_report.json --auto  # fully automatic
    python -m demo2.session --case case_gate_report.json --parallel  # parallel seat comments

Outputs:
    - events.jsonl in the demo2 directory
    - decisions_demo.db (SQLite) in the demo2 directory
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .events import EventLog
from .roles import (
    Theorist, Gatekeeper, RedTeam, FinalReviewer, Executor,
)
from .db import DecisionStore


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEMO_DIR = Path(__file__).resolve().parent
EVENTS_PATH = DEMO_DIR / "events.jsonl"
DB_PATH = DEMO_DIR / "decisions_demo.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_case(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class ReviewSession:
    def __init__(self, case: dict, session_id: str | None = None,
                 events_path: str | None = None, db_path: str | None = None):
        self.case = case
        self.session_id = session_id or f"sess-{int(time.time())}"
        self.events = EventLog(events_path or str(EVENTS_PATH), self.session_id)
        self.store = DecisionStore(db_path or str(DB_PATH))

        # Seats
        self.theorist = Theorist()
        self.gatekeeper = Gatekeeper()
        self.redteam = RedTeam()
        self.final = FinalReviewer()
        self.executor = Executor()

        self.comments: dict[str, str] = {}
        self.gated = False
        self.decision_str = ""
        self.decision_record: dict | None = None

    # -- steps ---------------------------------------------------------------

    def post_item(self) -> None:
        """POSTED event: the review item enters the room."""
        case_name = self.case.get("case", "未知案例")
        self.events.log("POSTED", "chair", {
            "case": case_name,
            "verdict": self.case.get("verdict", ""),
            "reasons_count": len(self.case.get("reasons", [])),
            "evidence_count": len(self.case.get("evidence", [])),
        })
        print(f"📋 评审对象已入席：{case_name}")
        print(f"   原裁决：{self.case.get('verdict', '?')} ｜ 理由 {len(self.case.get('reasons', []))} 条 ｜ 证据 {len(self.case.get('evidence', []))} 条")

    def seat_comments(self, parallel: bool = False) -> None:
        """Five seats comment. Parallel flag just changes the log label."""
        seats = [
            ("theorist", self.theorist),
            ("gatekeeper", self.gatekeeper),
            ("redteam", self.redteam),
            ("final", self.final),
            ("executor", self.executor),
        ]
        mode = "parallel" if parallel else "sequential"
        for seat_key, seat in seats:
            c = seat.comment(self.case)
            self.comments[seat_key] = c
            self.events.log("COMMENTED", seat.name, {"seat": seat.display_name, "mode": mode})
            print()
            print(c)

    def gatekeeper_hold_check(self) -> None:
        """Gatekeeper exercises hold power."""
        self.gated = self.gatekeeper.hold(self.case)
        if self.gated:
            self.events.log("HOLDED", "gatekeeper", {
                "reason": "critical-level reason detected",
                "reasons": self.case.get("reasons", []),
            })
            print("\n🚫 门禁官已行使一票 hold 权，会议挂起。")
        else:
            self.events.log("VOTED", "gatekeeper", {"result": "pass"})
            print("\n✓ 门禁官放行，无阻断项。")

    def final_decision(self) -> None:
        """Final reviewer produces the decision."""
        self.decision_str = self.final.final(self.comments, self.case, self.gated)
        self.events.log("FINALIZED", "final", {"decision": self.decision_str.split("\n")[0]})
        print()
        print(self.decision_str)

    def build_decision_record(self) -> dict:
        """Build the DecisionRecord envelope."""
        # Extract decision keyword
        first_line = self.decision_str.split("\n")[0]
        if "PASS" in first_line:
            decision = "PASS"
        elif "HOLD" in first_line:
            decision = "HOLD"
        elif "REJECT" in first_line:
            decision = "REJECT"
        else:
            decision = "CONDITIONAL_PASS"

        status = "executed"
        if decision == "HOLD":
            status = "pending"

        record = {
            "time": _now_iso(),
            "initiator": "Muse",
            "subject": self.case.get("case", "未知案例"),
            "decision": decision,
            "basis": self.decision_str.split("依据：")[-1] if "依据：" in self.decision_str else "",
            "status": status,
            "evidence_refs": self.case.get("evidence", []),
        }
        self.decision_record = record
        return record

    def log_decision(self) -> int:
        """Persist DecisionRecord to SQLite and log event."""
        record = self.build_decision_record()
        row_id = self.store.insert(record, session_id=self.session_id)
        self.events.log("DECISION_LOGGED", "executor", {
            "row_id": row_id,
            "decision": record["decision"],
            "subject": record["subject"],
            "status": record["status"],
        })
        exec_note = self.executor.execute(self.decision_str, self.case)
        print()
        print(exec_note)
        print(f"💾 决议已落库 (row_id={row_id}, table=decisions, db=decisions_demo.db)")
        return row_id

    # -- run all -------------------------------------------------------------

    def run(self, auto: bool = False, parallel: bool = False) -> dict:
        """Run the full pipeline. Returns summary dict."""
        self.post_item()
        if not auto:
            input("\n⏎ 继续五席发言…")
        self.seat_comments(parallel=parallel)
        if not auto:
            input("\n⏎ 门禁官 hold 判定…")
        self.gatekeeper_hold_check()
        if not auto:
            input("\n⏎ 终审裁决…")
        self.final_decision()
        if not auto:
            input("\n⏎ 决议落库…")
        row_id = self.log_decision()

        summary = {
            "session_id": self.session_id,
            "case": self.case.get("case", ""),
            "gated": self.gated,
            "decision": self.decision_record["decision"] if self.decision_record else "?",
            "row_id": row_id,
        }
        print("\n" + "=" * 60)
        print(f"✅ 会议结束 ｜ session={self.session_id} ｜ decision={summary['decision']} ｜ row_id={row_id}")
        print("=" * 60)
        return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="五席医械门禁评审会 — 多 AI 群聊协作原型")
    parser.add_argument("--case", required=True, help="GateReport JSON 文件路径")
    parser.add_argument("--auto", action="store_true", help="全流程自动跑（不交互）")
    parser.add_argument("--parallel", action="store_true", help="标记为并行发言模式（仅日志标签）")
    args = parser.parse_args(argv)

    if not os.path.exists(args.case):
        print(f"错误：找不到案例文件 {args.case}", file=sys.stderr)
        return 1

    case = _load_case(args.case)
    session = ReviewSession(case)
    session.run(auto=args.auto, parallel=args.parallel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
