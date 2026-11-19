#!/usr/bin/env python3
"""Absence sweep -- does deleting a required field ever turn a case into a `go`?

Five red-team rounds found the same shape in five domains: a rule waits on an
intermediate artefact, so the artefact's *absence* reads as permission. One probe
per domain only proves the instances we thought to look for. This states the
invariant once, over every shipped case:

    delete a field the input contract requires -> the answer must not be `go`.

It is deliberately narrow. Deleting a *fact* the case asserts (a death, a recall
class) legitimately removes the hazard, and `go` is then correct. What may never
happen is deleting an input the judge cannot work without -- that is not a case
with fewer facts, it is a record that cannot be judged, and the only honest
verdicts are `hold` or a tool error.

Exit 1 on any violation. No network, no model, no fixtures to maintain.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))

from build_demo_page import SUITES  # noqa: E402  (single source of truth for suites)
from lgd_engine.gate import GateEngine  # noqa: E402

RANK = {"go": 0, "hold": 1, "reject": 2}


def verdict_of(judge_cls, ctx: dict) -> str:
    try:
        return GateEngine([judge_cls()]).evaluate(ctx).to_dict()["verdict"]
    except Exception:  # a crash is stricter than any verdict
        return "error"


def sweep() -> list[dict]:
    findings = []
    for rel, domain, judge_cls, _label, _juris in SUITES:
        required = sorted(getattr(judge_cls, "REQUIRED_FIELDS", ()))
        d = ROOT / rel
        if not required or not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            ctx = json.loads(f.read_text(encoding="utf-8"))
            for key in required:
                if key not in ctx:
                    continue
                trimmed = {k: v for k, v in ctx.items() if k != key}
                after = verdict_of(judge_cls, trimmed)
                if after == "go":
                    findings.append({"case": f"{rel}/{f.name}",
                                     "case_id": ctx.get("case_id") or f.stem,
                                     "domain": domain, "field": key})
    return findings


def main() -> int:
    findings = sweep()
    if not findings:
        print("no required field can be deleted into a go across every shipped case")
        return 0
    print(f"{len(findings)} required field(s) deleted into a go:\n")
    for x in findings:
        print(f"  {x['case_id']:24s} {x['domain']:10s} drop {x['field']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
