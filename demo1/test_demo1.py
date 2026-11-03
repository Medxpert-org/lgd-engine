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

    print(f"\n[test_demo1] {n_pass}/{len(cases)} cases PASS")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
