"""Postmarket-surveillance judge.

Domain: postmarket-surveillance

Takes a reported adverse-event / recall event and returns an action-level
verdict (reject=Class 1 style immediate field safety notice; hold=Class 2
field correction; go=Class 3 / record-and-continue).

Rules grounded in VERIFIED recall records:
  - P2-CASE-MAJ-01..04  (FDA Class 1 recalls: process/material/design)
  - B1-C02 Dexcom CGM App (Class 1 missed sensor-failed alert)
  - B1-C08 Baxter Spectrum IQ (Class 1 software design, infusion safety)
  - B1-C05 Blue Ortho Predict+ (Class 2, no marketing application)
  - B1-C07 Butterfly iQ Auto EF (Class 2, no marketing application, AI feature)
  - B1-C09 Change Healthcare Hemo (Class 2, software autosave defect)
  - B1-C12 Siemens NAEOTOM AI (Class 2, AI feature removed from deployed devices)
  - B1-C14 Hologic Genius (Class 2, user tampered validated config)
  - B1-C04 Philips Pinnacle3 (NMPA Class 3, SPR calculation error)
  - B1-C11 Elekta MOSAIQ (NMPA Class 3, image offset calc)

Input ctx schema:
{
  "recall_class":        "none" | "class1" | "class2" | "class3",
  "fda_cause_type":      "software_design" | "process_change_control" |
                         "nonconforming_material" | "device_design" |
                         "no_marketing_application" | "user_config_tampering" |
                         "under_investigation" | "other",
  "harm_severity":       "no_harm" | "temporary_reversible" |
                         "serious_injury" | "death",
  "distribution_scope":  "limited_local" | "us_national" | "global",
  "event_report_count":  int,
  "marketing_without_license": bool,
  "source_refs": [{"kind": str, "ref": str}],
}
"""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Reason, Evidence


_CRITICAL = [
    {
        "rule": "PM-CRIT-01-class1-recall",
        "detail": "FDA/NMPA Class 1 recall: reasonable probability of serious "
                  "injury or death. Mandatory urgent field safety notice; "
                  "quarantine affected lots.",
        "when": lambda c: c.get("recall_class") == "class1",
    },
    {
        "rule": "PM-CRIT-02-unlicensed-on-market",
        "detail": "Product/feature on US/EU market without premarket clearance "
                  "or PMA (No Marketing Application). Immediate removal from "
                  "distribution; cannot operate until gate passes.",
        "when": lambda c: bool(c.get("marketing_without_license")),
    },
    {
        "rule": "PM-CRIT-03-death-or-serious-causal",
        "detail": "Death or serious injury reported and plausibly caused by "
                  "device software/design/material root cause — opens root-cause "
                  "CAPA and regulator notification.",
        "when": lambda c: (
            c.get("harm_severity") in {"serious_injury", "death"}
            and c.get("fda_cause_type") in {
                "software_design", "device_design", "nonconforming_material",
                "process_change_control",
            }
        ),
    },
]

_MAJOR = [
    {
        "rule": "PM-MAJ-01-class2-recall",
        "detail": "Class 2 / NMPA 二级 recall: temporary or medically reversible "
                  "health consequence. Field correction + enhanced monitoring + "
                  "CAPA within agreed timeline.",
        "when": lambda c: c.get("recall_class") == "class2",
    },
    {
        "rule": "PM-MAJ-02-user-config-deviation",
        "detail": "Deployed unit found operating outside its FDA-validated "
                  "configuration (user tampering). Re-seat to validated config "
                  "and audit access controls.",
        "when": lambda c: c.get("fda_cause_type") == "user_config_tampering",
    },
    {
        "rule": "PM-MAJ-03-high-report-volume",
        "detail": "Adverse-event report volume exceeds the watch threshold for "
                  "this device code — open trending review even if no recall yet.",
        "when": lambda c: int(c.get("event_report_count", 0) or 0) >= 25,
    },
]

_MINOR = [
    {
        "rule": "PM-MIN-01-class3-record",
        "detail": "Class 3 / NMPA 三级 recall: unlikely adverse health "
                  "consequence. Log, communicate, no product return.",
        "when": lambda c: c.get("recall_class") == "class3",
    },
]

# Unknown is not a safe default — the same class of hole as the 510(k) judge's
# R-MAJ-06. A postmarket event with recall_class="class9" matched no rule and
# returned go (probe C4, 2026-11-04).
KNOWN_RECALL_CLASS = {"none", "class1", "class2", "class3"}
KNOWN_CAUSE_TYPE = {
    "software_design", "process_change_control", "nonconforming_material",
    "device_design", "no_marketing_application", "user_config_tampering",
    "under_investigation", "other",
}
KNOWN_HARM_SEVERITY = {"no_harm", "temporary_reversible", "serious_injury", "death"}
KNOWN_DISTRIBUTION_SCOPE = {"limited_local", "us_national", "global"}

_ENUM_AXES = (
    ("recall_class", KNOWN_RECALL_CLASS),
    ("fda_cause_type", KNOWN_CAUSE_TYPE),
    ("harm_severity", KNOWN_HARM_SEVERITY),
    ("distribution_scope", KNOWN_DISTRIBUTION_SCOPE),
)


class JudgePostmarket:
    domain = "postmarket-surveillance"

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        reasons: List[Reason] = []
        evidence: List[Evidence] = []
        # A blank ref is not evidence (class fix, 2026-11-04): {"kind": "",
        # "ref": ""} used to satisfy the law-2 count here exactly as it did in
        # the 510(k) judge before probe B3 closed it there.
        for e in ctx.get("source_refs", []) or []:
            ref = (e.get("ref") or "").strip()
            if not ref:
                continue
            evidence.append(Evidence(
                kind=(e.get("kind") or "unspecified").strip() or "unspecified",
                ref=ref))

        def _run(rules, level):
            """Run a rule table. Returns (fired, errored).

            A predicate that raises is a hold signal, not a silent pass:
            swallowing it would fail open (probe C5).
            """
            fired = errored = False
            for rule in rules:
                try:
                    if rule["when"](ctx):
                        reasons.append(Reason(rule=rule["rule"], level=level,
                                              detail=rule["detail"]))
                        fired = True
                except Exception as exc:
                    reasons.append(Reason(
                        rule=rule["rule"], level=level,
                        detail=f"rule predicate raised ({type(exc).__name__}) — "
                               f"unclassifiable input cannot be a go",
                    ))
                    fired = errored = True
            return fired, errored

        crit, _crit_err = _run(_CRITICAL, "critical")

        if crit:
            verdict = "reject"
        else:
            maj, _maj_err = _run(_MAJOR, "major")
            if maj:
                verdict = "hold"
            else:
                _mino, min_err = _run(_MINOR, "minor")
                verdict = "hold" if min_err else "go"

        # Unknown enumerated values cannot be classified.
        for field, known in _ENUM_AXES:
            val = ctx.get(field)
            if val is None or val in known:
                continue
            reasons.append(Reason(
                rule=f"PM-MAJ-06-unknown-{field}", level="major",
                detail=f"{field} {val!r} is not a value this judge can classify — "
                       f"hold pending classification.",
            ))
            if verdict == "go":
                verdict = "hold"

        # L1/L2: a go needs a recorded evidence package. This branch used to be
        # unreachable — the line above it already turned a zero-evidence go into
        # a hold, so L2-EVIDENCED never fired and the downgrade was invisible in
        # the reason chain (probe C2, dead code confirmed by coverage).
        if verdict == "go" and not evidence:
            reasons.append(Reason(
                rule="L2-EVIDENCED", level="major",
                detail="go verdict with zero evidence refs — LGD L2 law downgrades "
                       "to hold pending documented evidence.",
            ))
            verdict = "hold"

        return {
            "verdict": verdict,
            "reasons": [{"rule": r.rule, "level": r.level, "detail": r.detail}
                        for r in reasons],
            "evidence": [{"kind": e.kind, "ref": e.ref} for e in evidence],
        }


__all__ = ["JudgePostmarket"]
