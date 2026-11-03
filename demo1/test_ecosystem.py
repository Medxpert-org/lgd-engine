"""Self-test for ecosystem layer (⑬ postmarket + ⑭ jurisdiction).

Run from mvp/ :
    python -m demo1.test_ecosystem
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_MVP = _HERE.parent
if str(_MVP) not in sys.path:
    sys.path.insert(0, str(_MVP))

from lgd_engine.gate import GateEngine                          # noqa: E402
from lgd_engine.judges.judge_510k import Judge510kChange        # noqa: E402
from lgd_engine.judges.judge_postmarket import JudgePostmarket  # noqa: E402


def _engine(judges):
    e = GateEngine()
    for j in judges:
        e.register(j)
    return e


def main() -> int:
    failures: list[str] = []
    n_pass = 0
    n_total = 0

    # ---- ⑬ postmarket -------------------------------------------------
    pm_dir = _HERE / "cases_postmarket"
    pm_cases = sorted(pm_dir.glob("*.json"))
    print(f"[postmarket] {len(pm_cases)} cases")
    for c in pm_cases:
        ctx = json.loads(c.read_text(encoding="utf-8"))
        exp = ctx.pop("expected_verdict")
        ctx.pop("_desensitized_from", None)
        rep = _engine([JudgePostmarket()]).evaluate(ctx)
        n_total += 1
        ok = rep.verdict == exp
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {c.name:38s} expected={exp:7s} got={rep.verdict:7s} "
              f"reasons={len(rep.reasons)}")
        if ok:
            n_pass += 1
        else:
            failures.append(f"{c.name}: expected {exp}, got {rep.verdict}")

    # ---- ⑭ jurisdiction FDA vs NMPA -----------------------------------
    jur_case = _HERE / "cases_jurisdiction" / "supplier_swap.json"
    ctx = json.loads(jur_case.read_text(encoding="utf-8"))
    exp_fda = ctx.pop("expected_fda_verdict")
    exp_nmpa = ctx.pop("expected_nmpa_verdict")
    ctx.pop("_desensitized_from", None)

    # FDA run
    ctx_fda = dict(ctx); ctx_fda["jurisdiction"] = "FDA"
    rep_fda = _engine([Judge510kChange()]).evaluate(ctx_fda)
    n_total += 1
    ok_fda = rep_fda.verdict == exp_fda
    print(f"  [{'PASS' if ok_fda else 'FAIL'}] supplier_swap FDA   expected={exp_fda:7s} got={rep_fda.verdict:7s}")
    if ok_fda:
        n_pass += 1
    else:
        failures.append(f"supplier_swap FDA: expected {exp_fda}, got {rep_fda.verdict}")

    # NMPA run
    ctx_nmpa = dict(ctx); ctx_nmpa["jurisdiction"] = "NMPA"
    rep_nmpa = _engine([Judge510kChange()]).evaluate(ctx_nmpa)
    n_total += 1
    ok_nmpa = rep_nmpa.verdict == exp_nmpa
    print(f"  [{'PASS' if ok_nmpa else 'FAIL'}] supplier_swap NMPA expected={exp_nmpa:7s} got={rep_nmpa.verdict:7s}")
    if ok_nmpa:
        n_pass += 1
    else:
        failures.append(f"supplier_swap NMPA: expected {exp_nmpa}, got {rep_nmpa.verdict}")

    # Cross-jurisdiction difference must hold
    n_total += 1
    if rep_fda.verdict != rep_nmpa.verdict:
        print(f"  [PASS] jurisdiction delta: FDA={rep_fda.verdict} vs NMPA={rep_nmpa.verdict} (expected difference)")
        n_pass += 1
    else:
        print(f"  [FAIL] jurisdiction delta: both={rep_fda.verdict} (expected a difference)")
        failures.append(f"jurisdiction delta missing: both {rep_fda.verdict}")

    print(f"\n[test_ecosystem] {n_pass}/{n_total} assertions PASS")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
