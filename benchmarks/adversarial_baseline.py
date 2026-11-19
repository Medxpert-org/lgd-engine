"""adversarial_baseline.py — measure the gate against a naive classifier.

Why this exists
---------------
"Deterministic gate" is a claim. The cheapest way to test a claim is to put a
naive alternative on the same inputs and count. This script defines 12 probes
whose expected verdict is fixed by the judge's own documented semantics, runs
each probe through (a) the real GateEngine judges and (b) a keyword classifier
of the kind a hurried integration would ship, and prints both scores.

The naive baseline is deliberately the *plausible* shortcut, not a strawman:
  - any mention of class1 / severe / life_threatening  -> reject
  - requires_submission true, or 'intended_use' appears -> hold
  - otherwise                                         -> go
That is roughly what "we can just grep the JSON" produces, and it is what a
model asked to "judge" without a rule table tends to converge on.

Run:
    python benchmarks/adversarial_baseline.py
Exit code 0 when the gate matches every probe (the probes ARE the contract).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lgd_engine.gate.engine import GateEngine                 # noqa: E402
from lgd_engine.judges.judge_510k import Judge510kChange      # noqa: E402
from lgd_engine.judges.judge_pccp import JudgePccpScope       # noqa: E402

GREEN_510K = {
    "change_type": "label_correction", "safety_impact": "none",
    "recall_class": "none", "predicate_unchanged": True,
    "requires_submission": False, "evidence_sufficiency": "sufficient",
    "jurisdiction": "FDA",
    "source_refs": [{"kind": "internal", "ref": "label diff v2"}],
}

GREEN_PCCP = {
    "pccp_authorized": True, "change_within_pccp_scope": True,
    "affects_intended_use": False, "change_class_described": True,
    "acceptance_criteria_met": True, "remains_se_to_predicate": True,
    "validation_documented": True,
    "labeling_version_history": True, "udi_updated": True,
    "change_type": "retrain_same_distribution",
    "evidence_sufficiency": "sufficient", "jurisdiction": "FDA",
    "source_refs": [{"kind": "fda_pccp", "ref": "class 2"}],
}


def _probes():
    def m(base, **kw):
        c = json.loads(json.dumps(base))
        c.update(kw)
        return c

    return [
        # --- 510(k) domain ------------------------------------------------
        ("k-green", "510k", GREEN_510K, "go"),
        ("k-blank-evidence", "510k", m(GREEN_510K, source_refs=[{"kind": "", "ref": "  "}]), "hold"),
        ("k-unknown-change", "510k", m(GREEN_510K, change_type="label_tweak_v2"), "hold"),
        ("k-unknown-safety", "510k", m(GREEN_510K, safety_impact="catastrophic"), "hold"),
        ("k-class1", "510k", m(GREEN_510K, recall_class="class1"), "reject"),
        ("k-string-yes", "510k", m(GREEN_510K, change_type="supplier_substitution",
                                     equivalence_declared="yes"), "hold"),
        # --- PCCP domain --------------------------------------------------
        ("p-green", "pccp", GREEN_PCCP, "go"),
        ("p-blank-evidence", "pccp", m(GREEN_PCCP, source_refs=[]), "hold"),
        ("p-criteria-fail", "pccp", m(GREEN_PCCP, acceptance_criteria_met=False), "reject"),
        ("p-nmpa", "pccp", m(GREEN_PCCP, jurisdiction="NMPA"), "hold"),
        ("p-no-plan", "pccp", m(GREEN_PCCP, pccp_authorized=False), "reject"),
        ("p-unknown-change", "pccp", m(GREEN_PCCP, change_type="vibes_based_update"), "hold"),
    ]


def naive(ctx: dict) -> str:
    """The plausible shortcut: grep the JSON, decide."""
    blob = json.dumps(ctx, ensure_ascii=False).lower()
    if any(k in blob for k in ("class1", "class 1", "severe", "life_threatening")):
        return "reject"
    if ctx.get("requires_submission") or "intended_use" in blob:
        return "hold"
    return "go"


JUDGES = {"510k": Judge510kChange, "pccp": JudgePccpScope}


def main() -> int:
    rows = []
    gate_ok = naive_ok = 0
    for pid, domain, ctx, expect in _probes():
        report = GateEngine([JUDGES[domain]()]).evaluate(ctx)
        got_gate = report.verdict
        got_naive = naive(ctx)
        gate_ok += got_gate == expect
        naive_ok += got_naive == expect
        rows.append((pid, domain, expect, got_gate, got_naive))

    print(f"{'probe':<20}{'domain':<8}{'expect':<9}{'gate':<9}{'naive':<9}")
    for pid, domain, expect, got_gate, got_naive in rows:
        mark_n = "" if got_naive == expect else "  <- naive misses"
        print(f"{pid:<20}{domain:<8}{expect:<9}{got_gate:<9}{got_naive:<9}{mark_n}")

    n = len(rows)
    print(f"\ngate  : {gate_ok}/{n} match expected")
    print(f"naive : {naive_ok}/{n} match expected")
    print(f"delta : {gate_ok - naive_ok} probes the shortcut gets wrong")
    return 0 if gate_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
