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


class TestPccpJudge(unittest.TestCase):
    """The third judge must obey the same doctrine as the first two: unproven is not
    pass, unknown is not pass, and a critical never softens into a hold."""

    def setUp(self):
        from lgd_engine.judges.judge_pccp import JudgePccpScope
        self.ev = [{"kind": "fda_pccp", "ref": "authorized PCCP, class 2"}]
        self.ok = {
            "pccp_authorized": True, "change_within_pccp_scope": True,
            "affects_intended_use": False, "change_class_described": True,
            "acceptance_criteria_met": True, "validation_documented": True,
            "labeling_version_history": True, "udi_updated": True,
            "change_type": "retrain_same_distribution",
            "evidence_sufficiency": "sufficient", "jurisdiction": "FDA",
            "source_refs": self.ev,
        }
        self.judge = JudgePccpScope()

    def _v(self, **kw):
        ctx = dict(self.ok)
        ctx.update(kw)
        return self.judge.evaluate(ctx)

    def test_covered_change_goes(self):
        self.assertEqual(self._v()["verdict"], "go")

    def test_intended_use_change_is_reject_not_hold(self):
        """Guidance excludes intended-use changes from PCCP coverage outright; a hold
        would invite 'resubmit the plan' as a workaround."""
        self.assertEqual(self._v(affects_intended_use=True)["verdict"], "reject")

    def test_failed_criteria_is_reject(self):
        self.assertEqual(self._v(acceptance_criteria_met=False)["verdict"], "reject")

    def test_claimed_coverage_without_pccp_is_reject(self):
        self.assertEqual(
            self._v(pccp_authorized=False, change_within_pccp_scope=True)["verdict"], "reject")

    def test_absent_facts_are_hold_never_go(self):
        """Unproven must not pass: missing PCCP status, unevaluated criteria, unknown
        change type, and a non-FDA jurisdiction all land on hold."""
        self.assertEqual(self._v(pccp_authorized=None)["verdict"], "hold")
        self.assertEqual(self._v(acceptance_criteria_met=None)["verdict"], "hold")
        self.assertEqual(self._v(change_type="vibes_based_update")["verdict"], "hold")
        self.assertEqual(self._v(jurisdiction="NMPA")["verdict"], "hold")

    def test_blank_ref_is_not_evidence(self):
        """An empty ref must not satisfy L2 and let a go through."""
        self.assertEqual(self._v(source_refs=[{"kind": "", "ref": "   "}])["verdict"], "hold")


class TestMdrJudge(unittest.TestCase):
    """EU MDR: significance is a property of the change, not of what the change
    note claims. The judge must refuse to let a declaration settle it."""

    def setUp(self):
        from lgd_engine.judges.judge_mdr import JudgeMdrSignificance
        self.judge = JudgeMdrSignificance()
        self.ok = {
            "change_category": "labeling_clarification",
            "affects_intended_purpose": False, "affects_clinical_benefit": False,
            "affects_safety_or_performance": False, "new_clinical_data_required": False,
            "verification_documented": True, "fsca_open": False,
            "declared_not_significant": False, "evidence_sufficiency": "sufficient",
            "jurisdiction": "EU",
            "source_refs": [{"kind": "internal_verification", "ref": "labelling diff"}],
        }

    def _v(self, **kw):
        ctx = dict(self.ok)
        ctx.update(kw)
        return self.judge.evaluate(ctx)

    def test_administrative_change_goes(self):
        self.assertEqual(self._v()["verdict"], "go")

    def test_performance_change_is_significant(self):
        self.assertEqual(
            self._v(change_category="software_algorithm",
                    affects_safety_or_performance=True)["verdict"], "hold")

    def test_declaring_it_non_significant_does_not_make_it_so(self):
        self.assertEqual(
            self._v(affects_intended_purpose=True, declared_not_significant=True)["verdict"],
            "reject")

    def test_change_during_open_fsca_is_reject(self):
        self.assertEqual(
            self._v(fsca_open=True, affects_safety_or_performance=True)["verdict"], "reject")

    def test_unproven_and_unknown_are_hold(self):
        self.assertEqual(self._v(change_category="cosmetic_vibes")["verdict"], "hold")
        self.assertEqual(self._v(jurisdiction="FDA")["verdict"], "hold")
        self.assertEqual(self._v(source_refs=[])["verdict"], "hold")


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

    def test_pccp_domain_matches_expected(self):
        """The PCCP case set ships with the package, so a stranger can run it too."""
        p = self._run("--all", str(ROOT / "demo1" / "cases_pccp"), "--domain", "pccp")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("5/5", p.stdout)

    def test_mdr_domain_matches_expected(self):
        p = self._run("--all", str(ROOT / "demo1" / "cases_mdr"), "--domain", "mdr")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("5/5", p.stdout)

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

    def test_role_table_provides_real_separation(self):
        """'reviewer' must reach strictly more than 'read-only', and the difference
        must be a real capability (the append-only decision write), not a label.
        Until 2026-11-18 the two sets were identical — this test replaces the
        assertion that used to pin that gap."""
        ro, rv = mcp_server.ROLE_TOOLS["read-only"], mcp_server.ROLE_TOOLS["reviewer"]
        self.assertTrue(ro < rv, "reviewer must be a strict superset of read-only")
        self.assertEqual(rv - ro, {"record_decision"})

    def test_readonly_cannot_record_decision(self):
        r = self._call("record_decision", role="read-only",
                       args={"case_id": "C-1", "verdict": "go", "rationale": "looks fine"})
        self.assertEqual(r["error"]["code"], -32003)

    def test_reviewer_can_record_decision(self):
        r = self._call("record_decision", role="reviewer",
                       args={"case_id": "C-1", "verdict": "hold", "rationale": "V&V missing"})
        body = json.loads(r["result"]["content"][0]["text"])
        self.assertEqual(body["recorded"]["verdict"], "hold")

    def test_recording_without_a_verdict_is_rejected(self):
        """An unsigned decision must not enter the audit trail."""
        r = self._call("record_decision", role="reviewer",
                       args={"case_id": "C-2", "verdict": "maybe", "rationale": "unsure"})
        self.assertEqual(r["error"]["code"], -32602)

    def test_pccp_judge_is_reachable_over_mcp(self):
        r = self._call("judge_pccp", role="read-only",
                       args={"pccp_authorized": True, "change_within_pccp_scope": True,
                             "affects_intended_use": False, "acceptance_criteria_met": True,
                             "change_type": "retrain_same_distribution",
                             "evidence_sufficiency": "sufficient", "jurisdiction": "FDA",
                             "source_refs": [{"kind": "fda_pccp", "ref": "plan class 2"}]})
        body = json.loads(r["result"]["content"][0]["text"])
        self.assertEqual(body["report"]["verdict"], "go")


if __name__ == "__main__":
    unittest.main()
