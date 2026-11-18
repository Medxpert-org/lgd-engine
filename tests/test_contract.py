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

    def test_broken_equivalence_closes_the_pccp_route(self):
        """§515C(b)(2) is two cumulative conditions: safe-and-effective AND remains
        substantially equivalent to the predicate. A well-written plan cannot cure
        the second one."""
        v = self._v(remains_se_to_predicate=False)
        self.assertEqual(v["verdict"], "reject")
        self.assertIn("P-CRIT-04", " ".join(r["rule"] for r in v["reasons"]))

    def test_modified_version_may_not_be_a_predicate(self):
        """§515C(c) bars comparing against a PCCP-modified version — a rule that
        belongs to nobody's device, which is exactly why nobody encodes it."""
        v = self._v(pccp_modified_version_used_as_predicate=True, change_type="predicate_use")
        self.assertEqual(v["verdict"], "reject")
        self.assertIn("P-CRIT-05", " ".join(r["rule"] for r in v["reasons"]))

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

    def test_intended_purpose_limitation_is_not_significant(self):
        """CAMD FAQ 17: narrowing the claim (removed patient group, added
        contraindication) is not a significant change. A table that blocks it would
        punish the manufacturer for shrinking its own indication."""
        v = self._v(change_category="intended_purpose", affects_intended_purpose=True,
                    intended_purpose_direction="limitation", declared_not_significant=True)
        self.assertEqual(v["verdict"], "go")
        self.assertIn("M-MIN-02", " ".join(r["rule"] for r in v["reasons"]))

    def test_expansion_of_intended_purpose_stays_significant(self):
        """The guard must not leak: the same field, opposite direction, is
        significant — the asymmetry is the point."""
        self.assertEqual(
            self._v(change_category="intended_purpose", affects_intended_purpose=True,
                    intended_purpose_direction="expansion")["verdict"], "hold")

    def test_accepted_corrective_action_keeps_its_route(self):
        """CAMD FAQ 17: a design change implementing a corrective action assessed and
        accepted by the competent authority is not significant. The open-FSCA veto and
        the significance criteria must not re-block what the authority accepted."""
        v = self._v(change_category="design_hardware", affects_safety_or_performance=True,
                    fsca_open=True, corrective_action_accepted_by_authority=True,
                    implements_accepted_corrective_action=True)
        self.assertEqual(v["verdict"], "go")
        self.assertIn("M-MIN-03", " ".join(r["rule"] for r in v["reasons"]))

    def test_acceptance_is_scoped_to_the_change_that_implements_it(self):
        """Red-team finding: the acceptance flag was a global bypass. An intended-
        purpose expansion, a safety change and a classification change all came back
        go just because *some* accepted corrective action existed. CAMD FAQ 17 exempts
        the implementing change, not the manufacturer's next idea."""
        for extra, label in (
            ({"change_category": "intended_purpose", "affects_intended_purpose": True,
              "intended_purpose_direction": "expansion"}, "expansion"),
            ({"change_category": "design_hardware",
              "affects_safety_or_performance": True}, "safety"),
            ({"change_category": "clinical_performance",
              "classification_changed": True}, "classification"),
        ):
            v = self._v(corrective_action_accepted_by_authority=True, **extra)
            self.assertEqual(v["verdict"], "hold", label)
            self.assertIn("M-MAJ-13", " ".join(r["rule"] for r in v["reasons"]), label)


class TestNmpaJudge(unittest.TestCase):
    """NMPA: the route (变更注册 vs 备案) is decided by the field, not by what the
    registrant finds convenient. Filing a licence item as a registration item is
    the specific abuse this table must refuse."""

    def setUp(self):
        from lgd_engine.judges.judge_nmpa import JudgeNmpaChangeRegistration
        self.judge = JudgeNmpaChangeRegistration()
        self.ok = {
            "has_registration_certificate": True,
            "change_fields": ["production_address_textual"],
            "requested_path": "filing",
            "safety_effectiveness_assessed": True,
            "technical_docs_updated": True,
            "evidence_sufficiency": "sufficient",
            "jurisdiction": "NMPA",
            "source_refs": [{"kind": "nmpa_registration", "ref": "注册证 2026xxxx"}],
        }

    def _v(self, **kw):
        ctx = dict(self.ok)
        ctx.update(kw)
        return self.judge.evaluate(ctx)

    def test_textual_registration_change_goes(self):
        self.assertEqual(self._v()["verdict"], "go")

    def test_licence_item_requires_change_registration(self):
        self.assertEqual(self._v(change_fields=["model_specification"],
                                 requested_path="licence_change")["verdict"], "hold")

    def test_licence_item_filed_as_registration_is_reject(self):
        """Filing 适用范围 as 备案 to skip technical review is not a slower route,
        it is an unavailable one."""
        self.assertEqual(self._v(change_fields=["scope_of_application"],
                                 requested_path="filing")["verdict"], "reject")

    def test_no_certificate_is_reject(self):
        self.assertEqual(self._v(has_registration_certificate=False)["verdict"], "reject")

    def test_unassessed_and_unknown_are_hold(self):
        self.assertEqual(self._v(safety_effectiveness_assessed=False)["verdict"], "hold")
        self.assertEqual(self._v(change_fields=["teleport_capability"])["verdict"], "hold")
        self.assertEqual(self._v(jurisdiction="FDA")["verdict"], "hold")
        self.assertEqual(self._v(recall_level="level1",
                                 change_fields=["structure_composition"])["verdict"],
                         "reject")

    def test_class1_licence_field_is_filed_not_registered(self):
        """Class I is 备案管理, so the same field change routes to 变更备案. Telling
        a Class I registrant to seek a 变更注册 asks for an instrument that does not
        exist for them; letting it read as an evasion of review is the mirror error."""
        v = self._v(device_class="I", change_fields=["technical_requirements"],
                    requested_path="filing")
        self.assertEqual(v["verdict"], "hold")
        self.assertIn("N-MAJ-13", " ".join(r["rule"] for r in v["reasons"]))

    def test_class1_cannot_be_sent_down_a_registration_route(self):
        """Red-team finding: the class guard was keyed on the changed FIELDS, so an
        administrative change sent as 变更注册 / 首次注册 came back go — the exact
        shape in which a route that does not exist for Class I survives review."""
        for path in ("licence_change", "new_registration"):
            v = self._v(device_class="I", change_fields=["registrant_name"],
                        requested_path=path)
            self.assertEqual(v["verdict"], "hold", path)
            self.assertIn("N-MAJ-15", " ".join(r["rule"] for r in v["reasons"]))

    def test_domestic_site_change_names_its_prerequisite(self):
        """47 号令 requires the 生产许可 change before the 备案 — filing alone skips
        a statutory precondition, so it must not read as a clean go."""
        v = self._v(change_fields=["domestic_manufacturing_site"],
                    requested_path="filing")
        self.assertEqual(v["verdict"], "hold")
        self.assertIn("N-MAJ-14", " ".join(r["rule"] for r in v["reasons"]))


class TestPostmarketJudge(unittest.TestCase):
    """Postmarket: the table used to ask only 'is there a recall?'."""

    def setUp(self):
        from lgd_engine.judges.judge_postmarket import JudgePostmarket
        self.judge = JudgePostmarket()
        self.ok = {"recall_class": "none", "fda_cause_type": "under_investigation",
                   "harm_severity": "no_harm", "distribution_scope": "limited_local",
                   "event_report_count": 1, "jurisdiction": "FDA",
                   "source_refs": [{"kind": "doc", "ref": "r"}]}

    def _v(self, **kw):
        ctx = dict(self.ok)
        ctx.update(kw)
        return self.judge.evaluate(ctx)

    def test_death_without_a_recall_is_still_reportable(self):
        """21 CFR 803.50 does not wait for a recall class. A death recorded against
        the device with recall_class=none used to return go with an empty chain."""
        for sev in ("death", "serious_injury"):
            v = self._v(harm_severity=sev)
            self.assertEqual(v["verdict"], "hold", sev)
            self.assertIn("PM-MAJ-04", " ".join(r["rule"] for r in v["reasons"]), sev)

    def test_a_recall_class_still_routes_as_before(self):
        self.assertEqual(self._v(recall_class="class1")["verdict"], "reject")
        self.assertEqual(self._v(recall_class="class2")["verdict"], "hold")
        self.assertEqual(self._v(recall_class="class3")["verdict"], "go")

    def test_even_a_go_names_the_rule_that_let_it_through(self):
        """Silence on the green path is indistinguishable from 'the table has
        nothing for this field'."""
        v = self._v()
        self.assertEqual(v["verdict"], "go")
        self.assertIn("PM-MIN-02", " ".join(r["rule"] for r in v["reasons"]))


class TestEnumCoverage(unittest.TestCase):
    """A vocabulary that is wider than the rule table is a silent-go generator.

    The unknown-value guards only fire for values the table does NOT know. A value
    the table DOES know but never places fell through with an empty reason chain and
    returned go — that is how `label_expansion` shipped a new indication down the
    label-correction path. This asserts every known change type is claimed by at
    least one rule, so a new vocabulary entry cannot arrive unplaced."""

    def setUp(self):
        from lgd_engine.judges.judge_510k import Judge510kChange, KNOWN_CHANGE_TYPES
        self.judge = Judge510kChange()
        self.types = KNOWN_CHANGE_TYPES
        self.ok = {
            "recall_class": "none", "safety_impact": "none",
            "evidence_sufficiency": "sufficient", "regulatory_path": "510k",
            "predicate_unchanged": True, "requires_submission": False,
            "jurisdiction": "FDA", "source_refs": [{"kind": "doc", "ref": "r"}],
        }

    def test_every_known_change_type_is_claimed_by_a_rule(self):
        unplaced = []
        for ct in sorted(self.types):
            ctx = dict(self.ok)
            ctx["change_type"] = ct
            v = self.judge.evaluate(ctx)
            if not v.get("reasons"):
                unplaced.append(ct)
        self.assertEqual(unplaced, [], f"known but unplaced change types: {unplaced}")


class TestDemoPage(unittest.TestCase):
    """The browser dossier must be a view of the engine, not a second source of
    truth. Both assertions below fail if someone edits the page by hand."""

    def test_page_is_in_sync_with_the_engine(self):
        p = subprocess.run([sys.executable, str(ROOT / "benchmarks" / "build_demo_page.py"),
                            "--check"], capture_output=True, text=True, timeout=180, cwd=ROOT)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("OK", p.stdout)

    def test_page_publishes_every_shipped_judge(self):
        html = (ROOT / "demo" / "judge-dossier.html").read_text(encoding="utf-8")
        for domain in ("510k", "postmarket", "pccp", "mdr", "nmpa"):
            self.assertIn(f'"domain": "{domain}"', html, f"demo page is missing {domain} cases")
        self.assertNotIn("__DATA__", html)


class TestClauseBasis(unittest.TestCase):
    """No rule may issue a verdict without naming the provision it encodes.

    Both directions are asserted: a shipped rule with no basis fails, and an
    authority entry naming no shipped rule fails too (dead authority is how
    citation tables rot while still looking complete)."""

    def setUp(self):
        # Same scan the clause matrix runs, imported rather than re-implemented:
        # a second copy of this AST walk drifted once and reported a shipped
        # guard rule as "dead authority".
        from lgd_engine.judges.basis import CLAUSE_BASIS, shipped_rules
        self.CLAUSE_BASIS = CLAUSE_BASIS
        self.rules = shipped_rules()

    def test_every_shipped_rule_names_a_basis(self):
        missing = sorted(r for r in self.rules if not self.CLAUSE_BASIS.get(r))
        self.assertEqual(missing, [], f"rules without a clause basis: {missing}")

    def test_no_authority_entry_is_dead(self):
        dead = sorted(r for r in self.CLAUSE_BASIS if r not in self.rules)
        self.assertEqual(dead, [], f"basis entries naming no shipped rule: {dead}")

    def test_basis_is_law_or_declared_doctrine(self):
        """A house rule must say it is a house rule; it may not pose as a clause."""
        bad = [r for r in self.rules
               if not self.CLAUSE_BASIS[r].startswith(("LAW ", "DOCTRINE "))]
        self.assertEqual(bad, [], f"basis not labelled LAW/DOCTRINE: {bad}")

    def test_doctrine_share_is_declared_and_small(self):
        """The point of the split is that doctrine stays visible and rare."""
        from lgd_engine.judges.basis import is_law
        doctrine = [r for r in self.rules if not is_law(self.CLAUSE_BASIS[r])]
        self.assertLessEqual(len(doctrine), 12,
                             f"doctrine share grew: {len(doctrine)} of {len(self.rules)}")
        self.assertEqual(len(self.rules), 66, "rule count moved — update the matrix doc")


class TestCoverageGaps(unittest.TestCase):
    """The boundary of the claim is a published artifact, not a footnote.

    A reviewer should be able to read what we do *not* encode, with a reason, and
    see the list fail the build when it is malformed — an undisclosed gap is
    indistinguishable from an oversight."""

    def setUp(self):
        import json
        self.doc = json.loads((ROOT / "docs" / "methods" / "coverage_gaps.json")
                              .read_text(encoding="utf-8"))
        self.gaps = self.doc["gaps"]

    def test_every_gap_is_complete_and_typed(self):
        allowed = {"out_of_scope", "deferred", "optional_by_law"}
        for g in self.gaps:
            for field in ("id", "jurisdiction", "provision", "status", "reason"):
                self.assertIn(field, g, f"{g.get('id')} missing {field}")
            self.assertIn(g["status"], allowed, f"{g['id']} has unknown status")
            self.assertGreater(len(g["reason"]), 40, f"{g['id']} reason is too thin")

    def test_gap_ids_are_unique(self):
        ids = [g["id"] for g in self.gaps]
        self.assertEqual(len(ids), len(set(ids)))

    def test_three_jurisdictions_are_all_represented(self):
        self.assertEqual({g["jurisdiction"] for g in self.gaps}, {"NMPA", "EU", "FDA"})


class TestVerdictCost(unittest.TestCase):
    """A verdict must be cheap and identical every time — that is the product."""

    def test_verdict_is_deterministic(self):
        import json as _json
        from lgd_engine.gate import GateEngine
        from lgd_engine.judges.judge_mdr import JudgeMdrSignificance
        ctx = _json.loads((ROOT / "demo1" / "cases_mdr"
                           / "mdr02_yellow_software_performance.json").read_text(encoding="utf-8"))
        outs = {_json.dumps(GateEngine([JudgeMdrSignificance()]).evaluate(ctx).to_dict(),
                            sort_keys=True) for _ in range(20)}
        self.assertEqual(len(outs), 1, "same context produced different reports")

    def test_verdict_latency_is_microseconds(self):
        import statistics, time
        from lgd_engine.gate import GateEngine
        from lgd_engine.judges.judge_pccp import JudgePccpScope
        ctx = {"pccp_authorized": True, "change_within_pccp_scope": True,
               "affects_intended_use": False, "change_class_described": True,
               "acceptance_criteria_met": True, "validation_documented": True,
               "labeling_version_history": True, "udi_updated": True,
               "remains_se_to_predicate": True,
               "change_type": "retrain_same_distribution",
               "evidence_sufficiency": "sufficient", "jurisdiction": "FDA",
               "source_refs": [{"kind": "fda_pccp", "ref": "authorized PCCP"}]}
        engine = GateEngine([JudgePccpScope()])
        samples = []
        for _ in range(300):
            t0 = time.perf_counter_ns()
            engine.evaluate(ctx)
            samples.append((time.perf_counter_ns() - t0) / 1000.0)
        median = statistics.median(samples)
        self.assertLess(median, 500, f"median verdict {median:.1f} µs — budget is 500 µs")


class TestEdgeClaims(unittest.TestCase):
    """A claim about a competitor without a provenance label is a sales line."""

    def setUp(self):
        import json as _json
        self.edges = _json.loads((ROOT / "docs" / "methods" / "competitive_edges.json")
                                 .read_text(encoding="utf-8"))["edges"]

    def test_every_claim_declares_its_provenance(self):
        for e in self.edges:
            self.assertIn(e["competitor_status"], {"observed", "inferred", "unverified"},
                          f"{e['id']} has an unlabelled competitor claim")

    def test_our_side_is_checkable(self):
        for e in self.edges:
            self.assertTrue((ROOT / e["our_proof"]).exists(),
                            f"{e['id']}: our_proof {e['our_proof']} does not exist")

    def test_observed_requires_a_source(self):
        for e in self.edges:
            if e["competitor_status"] == "observed":
                self.assertTrue(e.get("source"), f"{e['id']} claims observation without a source")

    def test_no_majority_claim_of_observation(self):
        """If most rows were 'observed' we would be asserting a survey we never ran."""
        observed = [e for e in self.edges if e["competitor_status"] == "observed"]
        self.assertLess(len(observed), len(self.edges) / 2,
                        "more than half the competitor claims are marked observed — "
                        "either run a real survey or label them inferred")


class TestMetadataConsistency(unittest.TestCase):
    """The citation file is the first thing a stranger reads; it must not lag.

    A stale version or a reference to a superseded document is the cheapest way to
    look unserious, and nothing else in the suite looked at these files."""

    def setUp(self):
        import re as _re
        self.cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.version = _re.search(r'^version\s*=\s*"([^"]+)"', pyproject, _re.M)
        self.cff_version = _re.search(r"^version:\s*([0-9.]+)\s*$", self.cff, _re.M)

    def test_citation_version_matches_the_package(self):
        self.assertIsNotNone(self.version, "pyproject.toml has no version")
        self.assertIsNotNone(self.cff_version, "CITATION.cff has no version")
        self.assertEqual(self.cff_version.group(1), self.version.group(1),
                         "CITATION.cff version disagrees with pyproject.toml")

    def test_citation_title_does_not_name_a_superseded_note(self):
        self.assertIn("Method Note v1.6", self.cff,
                      "CITATION.cff references an older method note")
        self.assertNotIn("Method Note v1.0", self.cff)


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
        self.assertIn("7/7", p.stdout)

    def test_mdr_domain_matches_expected(self):
        p = self._run("--all", str(ROOT / "demo1" / "cases_mdr"), "--domain", "mdr")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("9/9", p.stdout)

    def test_nmpa_domain_matches_expected(self):
        p = self._run("--all", str(ROOT / "demo1" / "cases_nmpa"), "--domain", "nmpa")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("9/9", p.stdout)

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
