"""lgd_engine.templates — a fillable skeleton, derived from the shipped cases.

A first-time caller could already get a verdict, but only after guessing which
keys the judge needs and which values it can classify: `change_type 'supplier'`
returns `hold / R-MAJ-06-unknown-change-type`, which is correct behaviour and a
useless answer to "what may I write here?". Two read-only commands fix that
without guessing anything:

    lgd-gate --template --domain 510k     # a JSON record with every required key
    lgd-gate --fields   --domain 510k     # the values the shipped cases actually use

Both are *derived* from `demo1/cases*`, the same corpus
`benchmarks/input_contracts.py` reads, so the vocabulary cannot drift away from
the cases that pin it. When the corpus is not present (an installed package),
the template still lists the keys the judges declare, and says so, rather than
inventing values that would be classified as unknown.
"""
from __future__ import annotations

import json
from pathlib import Path

# domain -> corpus directory, relative to the repository root
SUITES = {
    "510k": "demo1/cases",
    "postmarket": "demo1/cases_postmarket",
    "pccp": "demo1/cases_pccp",
    "mdr": "demo1/cases_mdr",
    "nmpa": "demo1/cases_nmpa",
}

_BOOL_KEYS = {"predicate_unchanged", "requires_submission", "pccp_authorized",
              "change_within_pccp_scope", "acceptance_criteria_met",
              "remains_se_to_predicate", "declared_not_significant",
              "verification_documented", "affects_clinical_benefit",
              "affects_intended_purpose", "affects_safety_or_performance",
              "fsca_open", "new_clinical_data_required", "has_registration_certificate",
              "safety_effectiveness_assessed", "technical_docs_updated",
              "affects_intended_use", "pccp_modified_version_used_as_predicate"}
_MAX_VALUES = 12


def corpus_cases(domain: str, root: Path | str = ".") -> list[dict]:
    """Every case of that domain that ships in the corpus, in file order."""
    rel = SUITES.get(domain)
    if not rel:
        return []
    d = Path(root) / rel
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def observed(domain: str, root: Path | str = ".") -> dict:
    """key -> {required, values} over the cases of this domain (describe, not decide)."""
    cases = corpus_cases(domain, root)
    if not cases:
        return {}
    keys: dict[str, dict] = {}
    for k in cases[0]:
        if k.startswith("_") or k.startswith("expected"):
            continue
        keys[k] = {"present": 0, "values": []}
        for c in cases:
            if k not in c:
                continue
            keys[k]["present"] += 1
            v = c[k]
            if isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False, sort_keys=True)[:120]
            if v not in keys[k]["values"]:
                keys[k]["values"].append(v)
    out = {}
    for k, v in keys.items():
        vals = sorted(v["values"], key=lambda x: (str(type(x)), str(x)))[:_MAX_VALUES]
        out[k] = {"required": v["present"] == len(cases), "values": vals}
    return out


def template(domain: str, root: Path | str = ".", required_only: bool = True) -> dict:
    """A record with the keys that domain's judge demands, values left for the caller.

    Values are deliberately left empty: an example value copied into a template
    reads like a finding, and the engine would classify it as though someone had
    asserted it. `--fields` supplies the vocabulary instead.
    """
    obs = observed(domain, root)
    if not obs:
        return {}
    keys = [k for k, v in obs.items() if v["required"]] if required_only else list(obs)
    rec = {"case_id": "<your-case-id>", "jurisdiction": "<FDA|NMPA|EU|CN>"}
    for k in keys:
        rec.setdefault(k, False if k in _BOOL_KEYS else None)
    return rec


def blank_template(domain: str, required: dict | None = None) -> dict:
    """Without a corpus: the declared required keys, typed but unfilled.

    No values are invented -- a fabricated `change_type` classifies as unknown and
    returns hold, which would look like a judgment instead of a missing input.
    """
    rec = {"case_id": "<your-case-id>", "jurisdiction": "<FDA|NMPA|EU|CN>"}
    for k in sorted(required or {}):
        rec[k] = False if k in _BOOL_KEYS else None
    return rec


def render_fields(domain: str, root: Path | str = ".") -> str:
    obs = observed(domain, root)
    if not obs:
        return (f"no corpus for domain={domain} under {root}/{SUITES.get(domain)}; "
                f"run this from the repository root, or use `--template` for the key list")
    lines = [f"Values observed in the shipped {domain} cases "
             f"({SUITES[domain]}) — derived, not hand-written.", ""]
    for k in sorted(obs):
        mark = "required" if obs[k]["required"] else "optional"
        vals = ", ".join(repr(v) for v in obs[k]["values"]) or "(no literal values)"
        lines.append(f"  {k:<28} {mark:<9} {vals}")
    lines += ["", "A value outside this list is not wrong — it is unclassified:",
              "the judge returns hold under R-MAJ-06 rather than guess."]
    return "\n".join(lines)
