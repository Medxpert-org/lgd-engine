#!/usr/bin/env python3
"""baseline_scorecard.py -- how much better, counted instead of asserted.

Every safety-tool README says "more reliable". This one publishes a scorecard,
because a delta is only a claim until someone else can recompute it.

Four shortcuts are put on the same inputs as the gate:

  always_go           approve unless something explodes; models the approval-biased
                      integration ("if there were a problem, the reviewer would say so")
  keyword             grep the JSON for class1 / severe / death -> reject,
                      requires_submission / intended_use -> hold, else go
  presence_checklist  the same keyword logic, plus "is every contract key present?"
                      -- what a schema validator with a keyword tail looks like
  single_rule         one if-statement: reject iff a severity word appears

None of these is a product. They are the shapes a hurried integration converges on,
and they are stated here so the comparison can be rejected or reproduced.

Two corpora:
  shipped    the 37 cases with a declared `expected_verdict`
  absence    each shipped case × each required field × [delete, null, "", [], {}, 0]

Metrics: exact agreement on `shipped`, and false greens on `absence` -- a `go` where
the shipped record was not `go`. The second metric is the one that matters: it is
the answer to "would this tool wave through a record it never actually read?"

    python benchmarks/baseline_scorecard.py            # check, exit 1 on drift
    python benchmarks/baseline_scorecard.py --write    # regenerate the scorecard
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))

OUT_MD = ROOT / "docs" / "methods" / "Baseline_Scorecard.md"
OUT_JSON = ROOT / "docs" / "methods" / "baseline_scorecard.json"

SEVERE = {"class1", "class2", "class3", "death", "life_threatening", "severe",
          "serious", "fatal", "high"}
BLANKS = [("delete", "DROP"), ("null", None), ("empty-string", ""),
          ("empty-list", []), ("empty-object", {}), ("zero", 0)]


def _values(ctx):
    for value in ctx.values():
        if isinstance(value, str):
            yield value.strip().lower()
        elif isinstance(value, bool):
            yield "true" if value else "false"
        elif isinstance(value, (int, float)):
            yield str(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, str):
                            yield v.strip().lower()


def always_go(_domain, _ctx, _required):
    return "go"


def keyword(_domain, _ctx, _required):
    words = set(_values(_ctx))
    if words & SEVERE:
        return "reject"
    if _ctx.get("requires_submission") is True or "intended_use" in words:
        return "hold"
    return "go"


def presence_checklist(_domain, ctx, required):
    missing = [k for k in required if k not in ctx]
    if missing:
        return "hold"
    return keyword(_domain, ctx, required)


def single_rule(_domain, _ctx, _required):
    return "reject" if any(v in SEVERE for v in _values(_ctx)) else "go"


BASELINES = {
    "always_go": always_go,
    "keyword": keyword,
    "presence_checklist": presence_checklist,
    "single_rule": single_rule,
}


def _corpora():
    from build_demo_page import SUITES
    from lgd_engine.gate.engine import GateEngine

    shipped, absence = [], []
    for rel, domain, cls, _lang, _judges in SUITES:
        required = list(getattr(cls, "REQUIRED_FIELDS", {}))
        for path in sorted((ROOT / rel).glob("*.json")):
            ctx = json.loads(path.read_text(encoding="utf-8"))
            # Same resolution as build_demo_page.py: some fixtures declare
            # per-jurisdiction expectations (same material, different regulator).
            expected = ctx.get("expected_verdict")
            if not expected:
                nmpa = ctx.get("expected_nmpa_verdict")
                fda = ctx.get("expected_fda_verdict")
                expected = (nmpa or fda) if str(ctx.get("jurisdiction", "")).upper() == "NMPA" \
                    else (fda or nmpa)
            if not expected:
                continue
            case_id = ctx.get("case_id") or path.stem
            gate = GateEngine([cls()])
            shipped.append({"case": case_id, "domain": domain, "ctx": ctx,
                            "expected": expected, "required": required,
                            "gate": gate.evaluate(ctx).to_dict()["verdict"]})
            for field in required:
                if field not in ctx:
                    continue
                for label, value in BLANKS:
                    variant = dict(ctx)
                    if value == "DROP":
                        variant.pop(field)
                    else:
                        variant[field] = value
                    absence.append({"case": case_id, "domain": domain, "ctx": variant,
                                    "expected": expected, "required": required,
                                    "gate": gate.evaluate(variant).to_dict()["verdict"],
                                    "variant": f"{field} {label}"})
    return shipped, absence


def build() -> dict:
    shipped, absence = _corpora()
    rows = []
    engines = {"gate": lambda c: c["gate"]}
    engines.update({name: (lambda fn: lambda c: fn(c["domain"], c["ctx"], c["required"]))(fn)
                    for name, fn in BASELINES.items()})
    for name, score in engines.items():
        agree = sum(1 for c in shipped if score(c) == c["expected"])
        greens = 0
        stable = 0
        for c in absence:
            verdict = score(c)
            if verdict == "go" and c["expected"] != "go":
                greens += 1
            if verdict == c["gate"]:
                stable += 1
        rows.append({
            "engine": name,
            "shipped_agreement": agree,
            "shipped_total": len(shipped),
            "absence_false_greens": greens,
            "absence_total": len(absence),
            "absence_same_as_gate": stable,
        })
    return {
        "_generated_by": "benchmarks/baseline_scorecard.py --write",
        "corpora": {"shipped": len(shipped), "absence": len(absence),
                    "absence_variants": [b[0] for b in BLANKS]},
        "rows": rows,
    }


def render(data: dict) -> tuple[str, str]:
    js = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    shipped = data["corpora"]["shipped"]
    absence = data["corpora"]["absence"]
    head = [
        "# Baseline scorecard",
        "",
        "Generated by `benchmarks/baseline_scorecard.py --write`. Regenerate, do not edit.",
        "",
        f"* **shipped** — {shipped} cases that declare their `expected_verdict`.",
        f"* **absence** — each shipped case × each contract field × "
        f"{{ delete, null, \"\", [], {{}}, 0 }} = **{absence}** records.",
        "* **false greens** — the record answered `go` although the shipped record "
        "was not `go`. This is the metric that separates *reading a record* from "
        "*grading its paperwork*.",
        "",
        "| engine | shipped agreement | false greens | same as gate |",
        "|---|---|---|---|",
    ]
    for row in data["rows"]:
        agree = f"{row['shipped_agreement']}/{row['shipped_total']}"
        greens = f"{row['absence_false_greens']}/{row['absence_total']}"
        same = f"{row['absence_same_as_gate']}/{row['absence_total']}"
        head.append(f"| `{row['engine']}` | {agree} | {greens} | {same} |")
    head += [
        "",
        "## What these baselines are, and are not",
        "",
        "They are **stand-ins for the shortcuts a hurried integration converges on** —",
        "an approval-biased default, a keyword grep, a schema check with a keyword tail,",
        "and a single severity rule. They are not products, and no vendor's behaviour is",
        "being claimed. Anyone who thinks a real tool does better can put it on the same",
        "two corpora: the cases, the mutations and the metric are all in this repository.",
        "",
        "The honest reading of the table: on the shipped corpus a keyword shortcut is",
        "already close, because the cases were written to be legible. The separation",
        "appears on the second corpus, where the record is still well-formed JSON and",
        "the shortcut cannot tell *absent* from *not objected*.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "python benchmarks/baseline_scorecard.py --write   # regenerate",
        "python benchmarks/baseline_scorecard.py           # check (exit 1 on drift)",
        "```",
        "",
    ]
    return js, "\n".join(head)


def main(argv: list[str]) -> int:
    data = build()
    js, md = render(data)
    if argv[1:2] == ["--write"]:
        OUT_JSON.write_text(js, encoding="utf-8")
        OUT_MD.write_text(md, encoding="utf-8")
        print(f"wrote {OUT_MD.relative_to(ROOT)} · {len(data['rows'])} engines · "
              f"shipped {data['corpora']['shipped']} · absence {data['corpora']['absence']}")
        for row in data["rows"]:
            print(f"  {row['engine']:>20s}  {row['shipped_agreement']}/{row['shipped_total']}  "
                  f"false-greens {row['absence_false_greens']}/{row['absence_total']}")
        return 0
    stale = []
    if not OUT_JSON.exists() or OUT_JSON.read_text(encoding="utf-8") != js:
        stale.append(OUT_JSON.name)
    if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != md:
        stale.append(OUT_MD.name)
    if stale:
        print("scorecard is stale: " + ", ".join(stale) + " — run with --write")
        return 1
    print("scorecard current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
