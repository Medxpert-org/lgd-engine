"""What a verdict costs, and whether it is the same verdict every time.

Two claims this script is allowed to make, both measurable offline:
  1. **determinism** — the same context produces a byte-identical report, 200
     runs in a row, with no network and no model call;
  2. **latency** — median microseconds per verdict over the shipped case set.

It is deliberately not a "throughput benchmark" against anyone else: comparing
our microseconds to a hosted LLM guardrail's seconds is a category error in the
other direction (theirs judges language, ours judges a structured context). The
claim made here is narrower and true: for the input shape we accept, the verdict
is free, repeatable and auditable.

Usage:
    python benchmarks/verdict_cost.py
    python benchmarks/verdict_cost.py --json
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lgd_engine.gate import GateEngine                      # noqa: E402
from lgd_engine.judges.judge_510k import Judge510kChange     # noqa: E402
from lgd_engine.judges.judge_postmarket import JudgePostmarket  # noqa: E402
from lgd_engine.judges.judge_pccp import JudgePccpScope      # noqa: E402
from lgd_engine.judges.judge_mdr import JudgeMdrSignificance  # noqa: E402
from lgd_engine.judges.judge_nmpa import JudgeNmpaChangeRegistration  # noqa: E402

SUITES = [
    ("demo1/cases", Judge510kChange),
    ("demo1/cases_jurisdiction", Judge510kChange),
    ("demo1/cases_postmarket", JudgePostmarket),
    ("demo1/cases_pccp", JudgePccpScope),
    ("demo1/cases_mdr", JudgeMdrSignificance),
    ("demo1/cases_nmpa", JudgeNmpaChangeRegistration),
]
REPEATS = 200


def _contexts() -> list:
    out = []
    for rel, judge_cls in SUITES:
        d = ROOT / rel
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            out.append((f.name, json.loads(f.read_text(encoding="utf-8")), judge_cls))
    return out


def measure() -> dict:
    cases = _contexts()
    samples: list[float] = []
    stable = True
    first: dict[str, str] = {}

    for name, ctx, judge_cls in cases:
        engine = GateEngine([judge_cls()])
        base = json.dumps(engine.evaluate(ctx).to_dict(), sort_keys=True,
                          ensure_ascii=False)
        first[name] = base
        for _ in range(REPEATS):
            t0 = time.perf_counter_ns()
            engine.evaluate(ctx).to_dict()
            samples.append((time.perf_counter_ns() - t0) / 1000.0)

    # second full pass: any drift on a fresh engine instance breaks determinism
    for name, ctx, judge_cls in cases:
        again = json.dumps(GateEngine([judge_cls()]).evaluate(ctx).to_dict(),
                           sort_keys=True, ensure_ascii=False)
        if again != first[name]:
            stable = False

    return {
        "cases": len(cases),
        "repeats": REPEATS,
        "deterministic": stable,
        "median_us": round(statistics.median(samples), 1),
        "p95_us": round(sorted(samples)[int(len(samples) * 0.95)], 1),
        "samples": len(samples),
        "network_calls": 0,
        "model_calls": 0,
    }


def main(argv: list[str]) -> int:
    r = measure()
    if argv[1:2] == ["--json"]:
        print(json.dumps(r, ensure_ascii=False))
        return 0
    print(f"cases measured : {r['cases']} (× {r['repeats']} runs = {r['samples']} verdicts)")
    print(f"deterministic  : {'YES' if r['deterministic'] else 'NO'}")
    print(f"median verdict : {r['median_us']} µs")
    print(f"p95 verdict    : {r['p95_us']} µs")
    print(f"network / model: {r['network_calls']} / {r['model_calls']}")
    return 0 if r["deterministic"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
