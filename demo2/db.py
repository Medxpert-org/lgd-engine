"""SQLite storage for DecisionRecord.

Demo-only database (decisions_demo.db). Does NOT touch the real localmem DB.
Interface reserved for a future real-localmem adapter.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL,
    initiator TEXT NOT NULL,
    subject TEXT NOT NULL,
    decision TEXT NOT NULL,
    basis TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    evidence_refs TEXT NOT NULL DEFAULT '[]',
    session_id TEXT NOT NULL DEFAULT ''
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionStore:
    """SQLite-backed decision record store (demo DB only)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    def insert(self, record: dict[str, Any], session_id: str = "") -> int:
        """Insert a DecisionRecord. Returns row id."""
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO decisions (time, initiator, subject, decision, basis, status, evidence_refs, session_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.get("time", _now_iso()),
                    record.get("initiator", ""),
                    record.get("subject", ""),
                    record.get("decision", ""),
                    record.get("basis", ""),
                    record.get("status", "pending"),
                    json.dumps(record.get("evidence_refs", []), ensure_ascii=False),
                    session_id,
                ),
            )
            return cur.lastrowid

    def list_all(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM decisions ORDER BY id").fetchall()
            return [dict(r) for r in rows]

    def update_status(self, row_id: int, status: str) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE decisions SET status = ? WHERE id = ?", (status, row_id))
