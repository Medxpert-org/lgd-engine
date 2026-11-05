"""Self-test for Demo1. Pure asserts; exits 0 only when all cases pass.

Run from mvp/ :
    python -m demo1.test_demo1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_MVP = _HERE.parent
if str(_MVP) not in sys.path:
    sys.path.insert(0, str(_MVP))

from lgd_engine.gate import GateEngine                       # noqa: E402
from lgd_engine.judges.judge_510k import Judge510kChange      # noqa: E402


def _engine() -> GateEngine:
    e = GateEngine()
    e.register(Judge510kChange())
    return e


def main() -> int:
    eng = _engine()
    case_dir = _HERE / "cases"
    cases = sorted(case_dir.glob("*.json"))
    assert cases, f"no case JSON under {case_dir}"

    n_pass = 0
    failures: list[str] = []
    for c in cases:
        ctx = json.loads(c.read_text(encoding="utf-8"))
        expected = ctx.pop("expected_verdict")
        ctx.pop("_desensitized_from", None)
        rep = eng.evaluate(ctx)
        ok = rep.verdict == expected
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {c.name:42s} expected={expected:7s} got={rep.verdict:7s} "
              f"reasons={len(rep.reasons)} evidence={len(rep.evidence)}")
        if ok:
            n_pass += 1
        else:
            failures.append(f"{c.name}: expected {expected}, got {rep.verdict}")

    # structural sanity: every verdict must carry a non-empty reasons list
    for c in cases:
        ctx = json.loads(c.read_text(encoding="utf-8"))
        ctx.pop("expected_verdict", None)
        ctx.pop("_desensitized_from", None)
        rep = eng.evaluate(ctx)
        assert rep.reasons, f"{c.name}: verdict has empty reasons"
        assert rep.verdict in ("go", "hold", "reject"), f"{c.name}: bad verdict"

    # ---- adversarial invariants (red team S7, 2026-11-04) ---------------
    # Each of these failed at least once. They live here so a future edit
    # cannot bring the failure back without turning this test red.
    def _inv(name: str, ctx: dict, ok_fn, why: str) -> bool:
        rep = eng.evaluate(ctx)
        ok = ok_fn(rep)
        print(f"  [{'PASS' if ok else 'FAIL'}] INV {name:28s} verdict={rep.verdict:7s} "
              f"reasons={len(rep.reasons)}")
        if not ok:
            failures.append(f"INV {name}: {why} (got {rep.verdict})")
        return ok

    inv_results = [
        _inv("unknown-change-type", {"change_type": "xyz_unknown_change"},
             lambda r: r.verdict != "go" and bool(r.reasons),
             "an unclassifiable change type must not return go"),
        _inv("blank-evidence", {"change_type": "label_correction",
                                "source_refs": [{"kind": "", "ref": ""}]},
             lambda r: r.verdict != "go",
             "a blank evidence ref is not evidence (L2)"),
        _inv("no-change-type", {"regulatory_path": "510k"},
             lambda r: r.verdict != "go",
             "law 1: no classified change, no verdict"),
        _inv("unknown-jurisdiction", {"change_type": "label_correction",
                                      "jurisdiction": "EU-MDR",
                                      "source_refs": [{"kind": "doc", "ref": "R-1"}]},
             lambda r: r.verdict != "go",
             "an unrouted jurisdiction must not silently pass"),
    ]

    # A veto must never be reported as a hold by the judge that fired it: the
    # Class 1 rule rejects, R-MAJ-05 used to overwrite that with hold.
    veto_ctx = {"recall_class": "class1", "change_type": "supplier_substitution",
                "equivalence_declared": "yes",
                "source_refs": [{"kind": "fda_recall", "ref": "Z-0000-2026"}]}
    veto_rep = eng.evaluate(veto_ctx)
    veto_pv = {v["verdict"] for v in veto_rep.per_judge.values()}
    veto_ok = veto_rep.verdict == "reject" and veto_pv == {"reject"}
    print(f"  [{'PASS' if veto_ok else 'FAIL'}] INV {'veto-not-softened':28s} "
          f"aggregate={veto_rep.verdict} per_judge={veto_pv}")
    if not veto_ok:
        failures.append("INV veto-not-softened: a critical veto must not read as hold")
    inv_results.append(veto_ok)

    print(f"\n[test_demo1] {n_pass}/{len(cases)} cases PASS; "
          f"{sum(inv_results)}/{len(inv_results)} invariants PASS")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
