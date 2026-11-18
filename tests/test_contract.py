# -*- coding: utf-8 -*-
"""Contract tests for lgd-engine: the three laws, the CLI contract, and the RBAC table.

Run:  python -m unittest discover -s tests -v
No third-party dependency. A failure here is a behavioural change, not a formatting nit.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lgd_engine.gate.engine import GateEngine          # noqa: E402
from lgd_engine.memory.localmem_min import LocalMemory  # noqa: E402
from lgd_engine import mcp_server                     # noqa: E402

CASES = ROOT / "demo1" / "cases"


class _Stub:
    """A judge that returns a canned verdict."""

    def __init__(self, domain, verdict, reasons=None, evidence=None):
        self.domain = domain
        self._v = {"verdict": verdict, "reasons": reasons or [], "evidence": evidence or []}

    def evaluate(self, ctx):
        return self._v


class _Boom:
    domain = "boom"

    def evaluate(self, ctx):
        raise RuntimeError("judge exploded")


class TestThreeLaws(unittest.TestCase):
    def test_no_judges_is_hold(self):
        """Empty engine must not answer GO by default."""
        self.assertEqual(GateEngine().evaluate({}).verdict, "hold")

    def test_l3_critical_forces_reject(self):
        """L3-GATED: one critical reason vetoes everything."""
        j = _Stub("d", "go", reasons=[{"rule": "R-X", "level": "critical", "detail": "x"}])
        r = GateEngine([j]).evaluate({})
        self.assertEqual(r.verdict, "reject")
        self.assertTrue(any("L3-GATED" in s for s in r.law_enforcements))

    def test_l2_go_without_evidence_is_hold(self):
        """L2-EVIDENCED: GO with zero evidence is downgraded to HOLD."""
        r = GateEngine([_Stub("d", "go")]).evaluate({})
        self.assertEqual(r.verdict, "hold")
        self.assertTrue(any("L2-EVIDENCED" in s for s in r.law_enforcements))

    def test_go_with_evidence_stays_go(self):
        j = _Stub("d", "go", evidence=[{"kind": "doc", "ref": "K123"}])
        self.assertEqual(GateEngine([j]).evaluate({}).verdict, "go")

    def test_crashing_judge_is_reject_and_flagged(self):
        """A crash must never read as a clean verdict: verdict=reject AND errors non-empty."""
        r = GateEngine([_Boom()]).evaluate({})
        self.assertEqual(r.verdict, "reject")
        self.assertTrue(r.errors, "a crashing judge must leave an error trail")
        self.assertIn("boom", r.per_judge)


class TestCliContract(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, "-m", "lgd_engine.cli", *args],
                              cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")

    def test_usage_error_is_64_not_2(self):
        """2 means REJECT; a usage error must not impersonate a verdict."""
        p = self._run()
        self.assertEqual(p.returncode, 64, p.stderr)

    def test_all_cases_match_expected(self):
        p = self._run("--all", str(CASES))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("[summary]", p.stdout)

    def test_single_case_is_deterministic(self):
        case = sorted(CASES.glob("*.json"))[0]
        a = self._run("--case", str(case))
        b = self._run("--case", str(case))
        self.assertEqual(a.returncode, b.returncode)
        self.assertEqual(a.stdout, b.stdout)

    def test_verdict_maps_to_exit_code(self):
        p = self._run("--case", str(sorted(CASES.glob("*.json"))[0]))
        badge = "GO" if "GO" in p.stdout.split("GATE VERDICT:")[1][:12] else None
        self.assertIn(p.returncode, (0, 1, 2))
        self.assertEqual(p.returncode == 0, badge == "GO")


class TestRbac(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        self.audit = LocalMemory(self._tmp.name)

    def _call(self, name, role=None, args=None):
        params = {"name": name, "arguments": args or {"change_type": "label"}}
        if role is not None:
            params["role"] = role
        return mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                  "params": params}, self.audit)

    def test_undeclared_role_denied(self):
        r = self._call("list_judges", role="god")
        self.assertEqual(r["error"]["code"], -32003)

    def test_unknown_tool_denied(self):
        r = self._call("merge_decision")
        self.assertEqual(r["error"]["code"], -32003)

    def test_readonly_judge_change_allowed(self):
        r = self._call("judge_change", role="read-only")
        self.assertIn("result", r)
        body = json.loads(r["result"]["content"][0]["text"])
        self.assertIn(body["report"]["verdict"], ("go", "hold", "reject"))

    def test_role_table_gap_is_pinned(self):
        """KNOWN LIMITATION, pinned on purpose: 'reviewer' reaches exactly the same
        tools as 'read-only', so the table provides no privilege separation yet.
        If this assertion starts failing, someone added a real privileged role -
        update the architecture doc instead of reverting the code."""
        self.assertEqual(mcp_server.ROLE_TOOLS["reviewer"], mcp_server.ROLE_TOOLS["read-only"])


if __name__ == "__main__":
    unittest.main()
