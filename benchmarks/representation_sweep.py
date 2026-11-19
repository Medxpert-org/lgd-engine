#!/usr/bin/env python3
"""representation_sweep.py -- does the same fact, spelled differently, decide differently?

Absence was the first attack surface (delete or blank a field). This is the second:
every field stays, every value stays, only the *spelling* changes -- casing, padding,
internal spacing, or a boolean written as a string. A human reading the record sees
the same record.

Two families, two different promises:

* **lexical** -- the same token, written differently ("class1" vs "CLASS1" vs
  "  class1  "). The verdict must be *identical*, in both directions. A tool that
  answers differently has decided on the spelling.
* **type** -- a boolean written as `"true"` or `1`. This is not a spelling of the
  same fact, it is a fact the record failed to state in a usable form, so the two
  acceptable outcomes are *same* or *more cautious* (`hold`). It must never become
  `go` (that would mean the string was read as a permission), and it must never
  become `reject` (that would mean the string was read as a veto).

    python benchmarks/representation_sweep.py          # exit 1 on any broken promise
    python benchmarks/representation_sweep.py --report # per-case detail
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))


def _variants(value):
    """(family, label, alternative) for one scalar that carries the same fact."""
    if isinstance(value, bool):
        return [("type", "bool-as-string-lower", "true" if value else "false"),
                ("type", "bool-as-string-title", "True" if value else "False"),
                ("type", "bool-as-int", 1 if value else 0)]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [("type", "number-as-string", str(value))]
    if isinstance(value, str) and value.strip():
        return [("lexical", "upper", value.upper()),
                ("lexical", "title", value.title()),
                ("lexical", "padded", "  " + value + "  "),
                ("lexical", "double-space", value.replace(" ", "  "))]
    return []


def _cases():
    from build_demo_page import SUITES
    from lgd_engine.gate.engine import GateEngine
    out = []
    for rel, domain, cls, _lang, _judges in SUITES:
        for path in sorted((ROOT / rel).glob("*.json")):
            ctx = json.loads(path.read_text(encoding="utf-8"))
            base = GateEngine([cls()]).evaluate(ctx).to_dict()["verdict"]
            out.append((cls, ctx, base, path.name))
    return out


def measure() -> dict:
    from lgd_engine.gate.engine import GateEngine
    cases = _cases()
    buckets = {"lexical_flips": [], "type_to_go": [], "type_to_reject": [],
               "type_to_hold": [], "type_same": []}
    total = 0
    for cls, ctx, base, name in cases:
        for key, value in list(ctx.items()):
            for family, label, variant in _variants(value):
                mutated = dict(ctx)
                mutated[key] = variant
                verdict = GateEngine([cls()]).evaluate(mutated).to_dict()["verdict"]
                total += 1
                entry = (name, key, label, base, verdict)
                if family == "lexical":
                    if verdict != base:
                        buckets["lexical_flips"].append(entry)
                elif verdict == "go" and base != "go":
                    buckets["type_to_go"].append(entry)
                elif verdict == "reject" and base != "reject":
                    buckets["type_to_reject"].append(entry)
                elif verdict == base:
                    buckets["type_same"].append(entry)
                else:
                    buckets["type_to_hold"].append(entry)
    return {"cases": len(cases), "variants": total, **buckets}


def main(argv):
    r = measure()
    print(f"{r['cases']} cases · {r['variants']} representation variants")
    print(f"lexical flips (same token, different casing/space): {len(r['lexical_flips'])}")
    print(f"type-as-go   (boolean written as a string read as permission): {len(r['type_to_go'])}")
    print(f"type-as-reject (boolean written as a string read as a veto): {len(r['type_to_reject'])}")
    print(f"type-same {len(r['type_same'])} · type-hold {len(r['type_to_hold'])} "
          f"(hold is the intended conservative answer)")
    if argv[1:2] == ["--report"]:
        for bucket in ("lexical_flips", "type_to_go", "type_to_reject"):
            for e in r[bucket]:
                print("  ", bucket, *e)
    return 1 if (r["lexical_flips"] or r["type_to_go"] or r["type_to_reject"]) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
