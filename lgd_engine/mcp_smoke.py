#!/usr/bin/env python3
"""mcp_smoke.py — drive the stdio MCP server once.

Checks, in one run:
  1. initialize answers with a protocol version
  2. tools/list advertises 5 tools (3 judges + list + decision record)
  3. judge_change returns a verdict (read-only is allowed to judge)
  4. judge_pccp returns a verdict (the third judge is reachable over MCP)
  5. record_decision is DENIED for read-only (-32003)
  6. record_decision is ALLOWED for reviewer and returns the recorded verdict

Exit 0 only when all six hold. Run from the repo root:
    python lgd_engine/mcp_smoke.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

EXPECTED_TOOLS = 7
VERDICTS = ("go", "hold", "reject")

DECISION = {"case_id": "SMOKE-1", "verdict": "hold", "rationale": "smoke: V&V pending"}


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, str(HERE / "mcp_server.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=str(HERE.parent),
    )
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "judge_change", "role": "read-only",
            "arguments": {"change_type": "label_correction",
                           "safety_impact": "none",
                           "recall_class": "none",
                           "predicate_unchanged": True}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
            "name": "judge_pccp", "role": "read-only",
            "arguments": {"pccp_authorized": True, "change_within_pccp_scope": True,
                           "affects_intended_use": False, "acceptance_criteria_met": True,
                           "change_type": "retrain_same_distribution",
                           "evidence_sufficiency": "sufficient", "jurisdiction": "FDA",
                           "source_refs": [{"kind": "fda_pccp", "ref": "class 2"}]}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
            "name": "record_decision", "role": "read-only", "arguments": DECISION}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {
            "name": "record_decision", "role": "reviewer", "arguments": DECISION}},
    ]
    for req in requests:
        proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    proc.stdin.close()

    ok = True
    for i in range(len(requests)):
        line = proc.stdout.readline()
        resp = json.loads(line)
        print(f"--- req id={i+1} -> resp ---")
        print(json.dumps(resp, ensure_ascii=False)[:400])

        if i == 1 and len(resp.get("result", {}).get("tools", [])) != EXPECTED_TOOLS:
            ok = False
        if i in (2, 3):
            text = resp["result"]["content"][0]["text"]
            verdict = json.loads(text)["report"]["verdict"]
            print(f"    verdict = {verdict}")
            if verdict not in VERDICTS:
                ok = False
        if i == 4:
            # read-only must NOT be able to record a decision
            if resp.get("error", {}).get("code") != -32003:
                ok = False
        if i == 5:
            if "error" in resp:
                ok = False
            else:
                recorded = json.loads(resp["result"]["content"][0]["text"])["recorded"]
                if recorded["verdict"] != DECISION["verdict"]:
                    ok = False

    proc.wait(timeout=15)
    print("SMOKE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
