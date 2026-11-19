"""PCCP change-scope judge.

Domain: pccp-change-scope

Question this judge answers: *may this change be implemented under an FDA-authorized
Predetermined Change Control Plan, or does it need its own marketing submission?*

Public basis (all citable, all offline) — text checked 2026-11-19 against the statute
and the CFR (see docs/methods/Legal_Check_20261118.md):
  - FD&C Act §515C, added by §3308 of FDORA (Pub. L. 117-328, 29 Dec 2022), codified at
    21 U.S.C. 360e-4:
      (a) PMA: no supplement needed for a change consistent with an approved PCCP;
      (b) 510(k): no new notification needed for a change consistent with a cleared
          PCCP, **provided (A) the device remains safe and effective without the change
          and (B) it would remain substantially equivalent to the predicate**;
      (c) predicate devices: **a version implemented under a PCCP may not be used as a
          predicate** — only the version cleared/approved before those changes;
      (a)(3)/(b)(3) scope: FDA may require labeling, a notification requirement when the
          device does not function as intended, and performance requirements.
  - 21 CFR 892.2055 (radiological ML-based quantitative imaging software with a PCCP;
    in force as of 2026-11-19): special controls require documented planned
    modifications and methodology, risk analysis, labeling **including a version
    history**, and objective performance evidence on an independent test set.
  - FDA final guidance,"Marketing Submission Recommendations for a PCCP for AI-Enabled
    Device Software Functions" (issued 4 Dec 2024): a PCCP describes the Description of
    Modifications, the Modification Protocol and the Impact Assessment; changes that
    alter intended use remain outside PCCP coverage.

This is a deterministic classifier over the facts supplied in `ctx`. It is not legal
advice and it does not read guidance PDFs at runtime. Every rule below cites the
provision it encodes, so a regulatory lead can disagree with a specific rule instead
of with "the AI".

Input ctx (all fields optional; missing facts are treated as unproven, never as pass):
{
  "pccp_authorized":          true | false,   # FDA has authorized a PCCP for this device
  "change_within_pccp_scope": true | false,   # change matches a described modification
  "affects_intended_use":     true | false,   # intended use / fundamental claims move
  "change_class_described":   true | false,   # the modification class is in the PCCP text
  "acceptance_criteria_met":  true | false,   # quantitative criteria satisfied
  "validation_documented":    true | false,   # V&V for this update on file
  "labeling_version_history": true | false,   # version history in labeling (892.2055)
  "remains_se_to_predicate":  true | false,   # §515C(b)(2)(B): still SE to its predicate
  "pccp_modified_version_used_as_predicate": true | false,  # §515C(c) prohibition
  "udi_updated":              true | false,   # new UDI issued for the new version
  "change_type":              <enum, see KNOWN_CHANGE_TYPES>,
  "evidence_sufficiency":     "sufficient" | "needs_supplement" | "none",
  "jurisdiction":             "FDA" | other,
  "device_description":       str,
  "source_refs":              [{"kind": str, "ref": str}],
}
"""
from __future__ import annotations

from typing import Any, Dict, List

from .base import DomainJudge, JudgeVerdict, Reason, Evidence, is_unusable


# ---- critical rules: one vote → reject ------------------------------------
_CRITICAL_RULES = [
    {
        "rule": "P-CRIT-01-claimed-coverage-without-pccp",
        "detail": "Change implemented as PCCP-covered but no authorized PCCP exists — "
                  "§515C shields only changes consistent with an *authorized* plan; "
                  "without one this is an unapproved modification. Veto.",
        "when": lambda c: (
            c.get("pccp_authorized") is False
            and c.get("change_within_pccp_scope") is True
        ),
    },
    {
        "rule": "P-CRIT-02-intended-use-change",
        "detail": "Change alters intended use or a fundamental claim — excluded from "
                  "PCCP coverage by the final guidance regardless of what the plan "
                  "says; a new submission is required. Veto.",
        "when": lambda c: c.get("affects_intended_use") is True,
    },
    {
        "rule": "P-CRIT-03-acceptance-criteria-not-met",
        "detail": "Quantitative acceptance criteria were not met — 892.2055 special "
                  "controls make those criteria binding, so a non-conforming update "
                  "cannot ride the plan. Veto.",
        "when": lambda c: c.get("acceptance_criteria_met") is False,
    },
    {
        "rule": "P-CRIT-04-se-to-predicate-broken",
        "detail": "§515C(b)(2) has two cumulative conditions for the 510(k) route: the "
                  "device remains safe and effective, AND it would remain substantially "
                  "equivalent to its predicate. A change that breaks substantial "
                  "equivalence cannot be cleared under a PCCP however well the plan is "
                  "written. Veto.",
        "when": lambda c: c.get("remains_se_to_predicate") is False,
    },
    {
        "rule": "P-CRIT-05-modified-version-used-as-predicate",
        "detail": "§515C(c) forbids comparing a device to a PCCP-modified version when "
                  "deciding substantial equivalence — only the version cleared or "
                  "approved before those changes may serve as a predicate. Using the "
                  "modified version as a predicate is not a documented shortcut, it is "
                  "a prohibited comparison. Veto.",
        "when": lambda c: c.get("pccp_modified_version_used_as_predicate") is True,
    },
]

# ---- major rules: escalate → hold when nothing critical fired --------------
_MAJOR_RULES = [
    {
        "rule": "P-MAJ-01-outside-pccp-scope",
        "detail": "Change falls outside the authorized PCCP scope — §515C gives no "
                  "cover; hold pending a new 510(k) / PMA supplement.",
        "when": lambda c: c.get("change_within_pccp_scope") is False,
    },
    {
        "rule": "P-MAJ-02-modification-class-not-described",
        "detail": "The modification class is not described in the PCCP text — an "
                  "undescribed class is not a covered class; hold pending submission.",
        "when": lambda c: (
            c.get("change_within_pccp_scope") is not False
            and c.get("change_class_described") is not True
        ),
    },
    {
        "rule": "P-MAJ-03-validation-not-documented",
        "detail": "Design verification / validation for this update is not on file — "
                  "892.2055 requires the methodology be documented as part of V&V.",
        "when": lambda c: (
            c.get("change_within_pccp_scope") is not False
            and c.get("validation_documented") is not True
        ),
    },
    {
        "rule": "P-MAJ-04-acceptance-criteria-unproven",
        "detail": "Acceptance criteria were not evaluated (absent, not failed) — "
                  "unproven is not met; hold until the measurement exists.",
        "when": lambda c: (
            c.get("acceptance_criteria_met") is None
            and c.get("change_within_pccp_scope") is not False
        ),
    },
    {
        "rule": "P-MAJ-05-labeling-version-history-missing",
        "detail": "Labeling carries no version history — 892.2055 lists version "
                  "history among the special controls every update must carry.",
        "when": lambda c: (
            c.get("change_within_pccp_scope") is not False
            and c.get("labeling_version_history") is not True
        ),
    },
    {
        "rule": "P-MAJ-06-udi-not-regenerated",
        "detail": "Version changed without a new UDI — the final guidance expects "
                  "devices with UDIs to generate new ones on version change, so the "
                  "version is not traceable to the shipped unit.",
        "when": lambda c: (
            c.get("change_within_pccp_scope") is not False
            and c.get("udi_updated") is not True
        ),
    },
    {
        "rule": "P-MAJ-07-evidence-insufficient",
        "detail": "Evidence package absent or incomplete — LGD L2 requires documented "
                  "evidence before a go, and a PCCP update is an evidence-producing act.",
        "when": lambda c: c.get("evidence_sufficiency") in {"needs_supplement", "none"},
    },
    {
        "rule": "P-MAJ-08-pccp-status-unknown",
        "detail": "Whether an authorized PCCP exists was not stated — the shield is "
                  "the whole question, so an unstated shield is an unproven one.",
        "when": lambda c: c.get("pccp_authorized") is None,
    },
    {
        "rule": "P-MAJ-09-not-fda-jurisdiction",
        "detail": "PCCP is a US FDA mechanism (§515C / 21 CFR 892.2055). This judge "
                  "cannot speak for EU MDR, NMPA or others — hold pending the "
                  "jurisdiction's own change-control route.",
        "when": lambda c: (c.get("jurisdiction") or "FDA").strip().upper() != "FDA",
    },
]

_MINOR_RULES = [
    {
        "rule": "P-MIN-01-covered-retrain",
        "detail": "Covered change with criteria met, V&V on file, version history and "
                  "UDI updated — record-and-go under the authorized plan.",
        "when": lambda c: (
            c.get("pccp_authorized") is True
            and c.get("change_within_pccp_scope") is True
            and c.get("affects_intended_use") is not True
            and c.get("acceptance_criteria_met") is True
        ),
    },
]

# Unknown change type is not a safe default (same doctrine as the 510k judge:
# before it existed, 87.5% of unknown change types rode out as GO with no reasons).
KNOWN_CHANGE_TYPES = {
    "retrain_same_distribution", "expand_training_data", "add_new_modality",
    "threshold_change", "architecture_change", "labeling_change",
    "cybersecurity_patch", "supplier_swap", "intended_use_change",
}

KNOWN_EVIDENCE_SUFFICIENCY = {"sufficient", "needs_supplement", "none"}


REQUIRED_FIELDS = {"pccp_authorized": bool, "change_within_pccp_scope": bool, "acceptance_criteria_met": bool, "evidence_sufficiency": str}

# PCCP: whether a plan exists and whether this change sits inside it.
_CONTRACT = {
    "rule": "REQ-01-input-contract",
    "when": lambda c: bool(is_unusable(c, REQUIRED_FIELDS)),
    "guard": True,
}


class JudgePccpScope:

    """DomainJudge adapter for PCCP change-scope."""

    CONTRACT_RULE = _CONTRACT["rule"]
    REQUIRED_FIELDS = REQUIRED_FIELDS

    domain = "pccp-change-scope"

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        reasons: List[Reason] = []
        evidence: List[Evidence] = []
        missing = is_unusable(ctx, REQUIRED_FIELDS)
        if missing:
            # An incomplete record is not a compliant record. Judging one reads
            # "nobody supplied this" as "nobody objected to this" -- the exact
            # shape behind five red-team defects (docs/methods/RedTeam_Probes.md).
            return {"verdict": "hold",
                    "reasons": [{"rule": _CONTRACT["rule"], "level": "major",
                                 "detail": "required input absent: "
                                           + ", ".join(missing)}],
                    "evidence": []}

        # A blank ref is not evidence (same filter as the 510k judge: an empty
        # {"kind": "", "ref": ""} once satisfied the L2 count).
        for e in ctx.get("source_refs", []) or []:
            ref = (e.get("ref") or "").strip()
            if not ref:
                continue
            evidence.append(Evidence(
                kind=(e.get("kind") or "unspecified").strip() or "unspecified", ref=ref))

        crit_fired = False
        for rule in _CRITICAL_RULES:
            try:
                if rule["when"](ctx):
                    crit_fired = True
                    reasons.append(Reason(rule=rule["rule"], level="critical",
                                          detail=rule["detail"]))
            except Exception:
                reasons.append(Reason(rule=rule["rule"], level="major",
                                      detail=f"rule predicate raised on ctx keys: {list(ctx.keys())}"))

        verdict = "reject" if crit_fired else "go"

        if not crit_fired:
            maj_fired = False
            for rule in _MAJOR_RULES:
                try:
                    if rule["when"](ctx):
                        maj_fired = True
                        reasons.append(Reason(rule=rule["rule"], level="major",
                                              detail=rule["detail"]))
                except Exception as exc:  # pragma: no cover - defensive
                    reasons.append(Reason(rule=rule["rule"], level="minor",
                                          detail=f"predicate error: {exc}"))
            if maj_fired:
                verdict = "hold"
            else:
                for rule in _MINOR_RULES:
                    try:
                        if rule["when"](ctx):
                            reasons.append(Reason(rule=rule["rule"], level="minor",
                                                  detail=rule["detail"]))
                    except Exception:
                        pass

        # L2-EVIDENCED: a go with no evidence is a hold, never a reject.
        if verdict == "go" and not evidence:
            reasons.append(Reason(
                rule="L2-EVIDENCED", level="major",
                detail="go verdict with zero evidence refs — LGD L2 downgrades to "
                       "hold pending documented evidence."))
            verdict = "hold"

        # Unknown is not safe by default — for the change type and the evidence axis.
        ct = ctx.get("change_type")
        if ct is None or ct not in KNOWN_CHANGE_TYPES:
            reasons.append(Reason(
                rule="P-MAJ-10-unknown-change-type", level="major",
                detail=(f"change_type {ct!r} is not a class this judge can place inside "
                        f"or outside a PCCP — unknown is not a safe default.")))
            if verdict == "go":
                verdict = "hold"

        ev = ctx.get("evidence_sufficiency")
        if ev is not None and ev not in KNOWN_EVIDENCE_SUFFICIENCY:
            reasons.append(Reason(
                rule="P-MAJ-11-unknown-evidence-sufficiency", level="major",
                detail=f"evidence_sufficiency {ev!r} is not a value this judge can "
                       f"classify — hold pending classification."))
            if verdict == "go":
                verdict = "hold"

        return JudgeVerdict(verdict=verdict, reasons=reasons, evidence=evidence).to_dict()


__all__ = ["JudgePccpScope", "KNOWN_CHANGE_TYPES"]
