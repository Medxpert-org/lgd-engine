"""Append-only JSONL event log for the five-seat review session.

Event types: POSTED, COMMENTED, HOLDED, VOTED, FINALIZED, DECISION_LOGGED.
Each event carries: type, author, timestamp (ISO), thread (session id), payload.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventLog:
    """Append-only JSONL event logger."""

    VALID_TYPES = {
        "POSTED", "COMMENTED", "HOLDED", "VOTED", "FINALIZED", "DECISION_LOGGED",
    }

    def __init__(self, path: str, session_id: str):
        self.path = path
        self.session_id = session_id
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    def log(self, event_type: str, author: str, payload: dict | None = None) -> dict:
        if event_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid event type: {event_type}")
        event = {
            "type": event_type,
            "author": author,
            "timestamp": _now_iso(),
            "thread": self.session_id,
            "payload": payload or {},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def read_all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out
