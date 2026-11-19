#!/usr/bin/env python3
"""Absence taxonomy -- every field a rule reads, and what its absence means.

`absence_sweep.py` proves one property: a *required* field cannot be deleted into a
green light. That is a claim about the fields we chose to require, and a reviewer is
entitled to ask what it says about the rest.

So the rest is written down. Every field that any judge reads is classified:

    required      in REQUIRED_FIELDS -- absent or blank returns `hold` (enforced)
    claim         the case asserts something; removing the assertion may legitimately
                  change the answer, so `go` is allowed
    weak_evidence proof-shaped, but some shipped case does not supply it, so it cannot
                  be required without silently flipping that case. Published as a gap.

`weak_evidence` is the honest residue: fields that look like evidence and are not yet
enforced. The count is capped in the test suite, so it can shrink and not quietly grow.

    python benchmarks/absence_taxonomy.py            # check, exit 1 on drift
    python benchmarks/absence_taxonomy.py --write    # regenerate the table
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "methods" / "absence_taxonomy.json"

JUDGES = {
    "510k": "judge_510k.py",
    "postmarket": "judge_postmarket.py",
    "pccp": "judge_pccp.py",
    "mdr": "judge_mdr.py",
    "nmpa": "judge_nmpa.py",
}

# Proof-shaped fields that some shipped case omits -> cannot be required yet.
# The reason must name the case(s): a "weak" field is a fact about the corpus, not a
# mood. `build()` fills `absent_in` by scanning the corpus, so the claim cannot go stale.
WEAK = {
    ("pccp", "validation_documented"): "the red-team case exists to test its absence; "
                                       "requiring it would replace a specific rule with "
                                       "a generic one",
    ("pccp", "labeling_version_history"): "same case: absence is the probe",
    ("pccp", "udi_updated"): "same case: absence is the probe",
}

# Fields that identify a case or carry citations rather than a claim about the change.
BOOKKEEPING = {"source_refs", "case_id", "device_description", "jurisdiction",
               "change_type", "change_category", "device_class", "change_fields"}


def referenced_fields(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r'(?:ctx|c)\.get\("([a-z_]+)"', text))


def build() -> dict:
    sys.path.insert(0, str(ROOT))
    from lgd_engine.judges.judge_510k import Judge510kChange
    from lgd_engine.judges.judge_postmarket import JudgePostmarket
    from lgd_engine.judges.judge_pccp import JudgePccpScope
    from lgd_engine.judges.judge_mdr import JudgeMdrSignificance
    from lgd_engine.judges.judge_nmpa import JudgeNmpaChangeRegistration

    classes = {
        "510k": Judge510kChange, "postmarket": JudgePostmarket, "pccp": JudgePccpScope,
        "mdr": JudgeMdrSignificance, "nmpa": JudgeNmpaChangeRegistration,
    }
    sys.path.insert(0, str(ROOT / "benchmarks"))
    from build_demo_page import SUITES

    corpus: dict[str, list] = {}
    for rel, domain, _cls, _lang, _judges in SUITES:
        corpus[domain] = [p for p in sorted((ROOT / rel).glob("*.json"))]

    def omitting(domain: str, key: str) -> list:
        missing = []
        for path in corpus.get(domain, []):
            ctx = json.loads(path.read_text(encoding="utf-8"))
            if key not in ctx:
                missing.append(path.name)
        return missing

    domains: dict[str, dict] = {}
    for domain, module in JUDGES.items():
        cls = classes[domain]
        required = dict(cls.REQUIRED_FIELDS)
        fields = {}
        for key in sorted(referenced_fields(ROOT / "lgd_engine" / "judges" / module)):
            if key in required:
                kind = "required"
            elif (domain, key) in WEAK:
                kind = "weak_evidence"
            elif key in BOOKKEEPING:
                kind = "bookkeeping"
            else:
                kind = "claim"
            entry = {"kind": kind}
            if key in required:
                entry["type"] = required[key].__name__
            if (domain, key) in WEAK:
                entry["why"] = WEAK[(domain, key)]
            absent = omitting(domain, key)
            if absent:
                entry["absent_in"] = absent
            fields[key] = entry
        domains[domain] = fields

    counts = {"required": 0, "weak_evidence": 0, "claim": 0, "bookkeeping": 0}
    for fields in domains.values():
        for entry in fields.values():
            counts[entry["kind"]] += 1
    return {"_generated_by": "benchmarks/absence_taxonomy.py --write",
            "_fields": len(counts) and sum(counts.values()),
            "_counts": counts,
            "domains": domains}


def render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    data = build()
    text = render(data)
    if argv[1:2] == ["--write"]:
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)} · {data['_fields']} fields · {data['_counts']}")
        return 0
    if not OUT.exists():
        print("missing docs/methods/absence_taxonomy.json — run with --write")
        return 1
    if OUT.read_text(encoding="utf-8") != text:
        print("absence_taxonomy.json is stale — run with --write")
        return 1
    print(f"taxonomy current · {data['_fields']} fields · {data['_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
