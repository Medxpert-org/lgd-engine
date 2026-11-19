"""EU MDR significant-change judge.

Domain: mdr-significant-change

Question: *is this change to a CE-marked device "significant" in the sense that it
needs a notified-body assessment, or may it be implemented under the manufacturer's
own change control?*

Public basis (citable, offline):
  - Regulation (EU) 2017/745 (MDR), Art. 120 transitional provisions and Annex IX
    assessment routes — a significant change to a device's design, intended purpose
    or performance invalidates the existing assessment basis.
  - MDCG 2020-3 rev.1, "Guidance on significant changes regarding the transitional
    provision" — article text checked 2026-11-18 (see docs/methods/Legal_Check_20261118.md):
    a significant change needs BOTH elements — a change in design or intended purpose
    AND significance (rev.1 §4.1). Significant: intended purpose expansion, clinical
    benefit, design/software affecting safety or performance, patient-contacting
    materials, sterilization, packaging/shelf life affecting sterility, new clinical
    data, classification change. NOT significant: administrative changes (§4.2),
    manufacturing-site relocation or supplier swap with unchanged specifications
    (§4.2), **limitation/restriction of the intended purpose**, and design changes
    implementing a corrective action assessed and accepted by the competent authority
    (CAMD FAQ 17).
  - Regulation (EU) 2023/607 moved the transition end to 31 Dec 2027 (Class III and
    IIb implantables) and 31 Dec 2028 (others).

The verdict mapping this judge uses:
  go     = not significant; proceed under the manufacturer's change control
  hold   = significant; a notified-body / conformity assessment step is required first
  reject = the change must not proceed at all (safety corrective action open, or a
           significant change being declared non-significant to avoid assessment)

Deliberately NOT covered: FDA 510(k)/PCCP routes (separate judges). Passing
`jurisdiction` other than "EU" produces a hold with an explicit reason rather than a
guess.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .base import DomainJudge, JudgeVerdict, Reason, Evidence


_CRITICAL_RULES = [
    {
        "rule": "M-CRIT-01-change-during-open-fsca",
        "detail": "A field safety corrective action is open and this change touches "
                  "safety or performance — implementing it while the corrective action "
                  "is unresolved compounds the nonconformity. Veto.",
        "when": lambda c: (
            c.get("fsca_open") is True
            and c.get("affects_safety_or_performance") is True
            # CAMD FAQ 17 and MDCG 2020-3: a design change tied to a corrective action
            # that the competent authority has assessed and accepted is not a
            # significant change — the veto must not swallow that route. Scoped to the
            # change that implements the action (see M-MAJ-13): an acceptance flag
            # alone must not disarm the veto for unrelated changes.
            and not (c.get("corrective_action_accepted_by_authority") is True
                     and c.get("implements_accepted_corrective_action") is True)
        ),
    },
    {
        "rule": "M-CRIT-02-significant-declared-non-significant",
        "detail": "The change meets an MDCG 2020-3 significance criterion yet is "
                  "declared non-significant in order to skip assessment — that is the "
                  "assessment being evaded, not avoided. Veto.",
        "when": lambda c: (
            c.get("declared_not_significant") is True
            and (c.get("affects_clinical_benefit") is True
                 or c.get("new_clinical_data_required") is True
                 or (c.get("affects_intended_purpose") is True
                     # A limitation/restriction of intended purpose is expressly NOT
                     # significant (CAMD FAQ 17), so declaring it non-significant is
                     # the correct answer, not an evasion.
                     and str(c.get("intended_purpose_direction") or "").strip().lower()
                     != "limitation"))
        ),
    },
]

_MAJOR_RULES = [
    {
        "rule": "M-MAJ-01-intended-purpose",
        "detail": "MDCG 2020-3: a change to intended purpose / indications / target "
                  "population is significant — notified-body assessment first.",
        "when": lambda c: (
            c.get("affects_intended_purpose") is True
            and str(c.get("intended_purpose_direction") or "").strip().lower()
            != "limitation"
        ),
    },
    {
        "rule": "M-MAJ-02-clinical-benefit",
        "detail": "MDCG 2020-3: a change affecting the clinical benefit-risk ratio is "
                  "significant.",
        "when": lambda c: c.get("affects_clinical_benefit") is True,
    },
    {
        "rule": "M-MAJ-03-safety-or-performance",
        "detail": "MDCG 2020-3: a design / software / manufacturing change that may "
                  "affect safety or performance is significant.",
        "when": lambda c: c.get("affects_safety_or_performance") is True,
    },
    {
        "rule": "M-MAJ-04-new-clinical-data",
        "detail": "MDCG 2020-3: a change requiring new clinical data is significant by "
                  "definition — the evidence base moves.",
        "when": lambda c: c.get("new_clinical_data_required") is True,
    },
    {
        "rule": "M-MAJ-05-patient-contacting-material",
        "detail": "MDCG 2020-3: a change of patient-contacting material is significant "
                  "(biocompatibility basis changes).",
        "when": lambda c: c.get("patient_contacting_material_change") is True,
    },
    {
        "rule": "M-MAJ-06-sterilization-or-shelf-life",
        "detail": "MDCG 2020-3: sterilization change, or a packaging / shelf-life change "
                  "affecting sterility, is significant.",
        "when": lambda c: (
            c.get("sterilization_change") is True
            or c.get("sterility_affected") is True
        ),
    },
    {
        "rule": "M-MAJ-07-classification-change",
        "detail": "MDCG 2020-3: a change in risk classification is significant — the "
                  "applicable conformity-assessment route changes with it.",
        "when": lambda c: c.get("classification_changed") is True,
    },
    {
        "rule": "M-MAJ-08-verification-not-documented",
        "detail": "No verification documented for the change — a non-significant "
                  "conclusion is only defensible with evidence, not with intent.",
        "when": lambda c: (
            c.get("affects_safety_or_performance") is not True
            and c.get("verification_documented") is False
        ),
    },
    {
        "rule": "M-MAJ-09-evidence-insufficient",
        "detail": "Evidence package absent or incomplete — LGD L2 downgrades a go to "
                  "hold pending documented evidence.",
        "when": lambda c: c.get("evidence_sufficiency") in {"needs_supplement", "none"},
    },
    {
        "rule": "M-MAJ-13-acceptance-not-scoped-to-this-change",
        "detail": "A corrective action has been accepted by the authority, but this "
                  "change is not declared as implementing it. CAMD FAQ 17 exempts the "
                  "change that implements the accepted action, not everything the same "
                  "manufacturer does afterwards — an acceptance flag that exempts any "
                  "change would let an intended-purpose expansion ride a sealing fix.",
        "when": lambda c: (
            c.get("corrective_action_accepted_by_authority") is True
            and c.get("implements_accepted_corrective_action") is not True
        ),
    },
    {
        "rule": "M-MAJ-10-not-eu-jurisdiction",
        "detail": "This judge speaks only for MDR (EU). Another jurisdiction has its "
                  "own significance test — hold pending that route.",
        "when": lambda c: (c.get("jurisdiction") or "EU").strip().upper() != "EU",
    },
]

_MINOR_RULES = [
    {
        "rule": "M-MIN-01-administrative",
        "detail": "Administrative change or labelling clarification that touches no "
                  "claim or performance attribute — not significant per MDCG 2020-3 "
                  "§4.2.",
        "when": lambda c: c.get("change_category") in {
            "administrative", "labeling_clarification"},
    },
    {
        "rule": "M-MIN-02-intended-purpose-limitation",
        "detail": "A limitation or restriction of the intended purpose (narrower "
                  "indication, added contraindication, removed patient group) is not a "
                  "significant change — CAMD FAQ 17 and MDCG 2020-3 rev.1 §4.1. Legacy "
                  "status survives; the narrower claim is still a claim to document.",
        "when": lambda c: (
            c.get("affects_intended_purpose") is True
            and str(c.get("intended_purpose_direction") or "").strip().lower()
            == "limitation"
        ),
    },
    {
        "rule": "M-MIN-03-corrective-action-accepted",
        "detail": "A design change implementing a corrective action the competent "
                  "authority has assessed and accepted is not significant — CAMD FAQ 17.",
        "when": lambda c: (
            c.get("corrective_action_accepted_by_authority") is True
            and c.get("implements_accepted_corrective_action") is True
        ),
    },
]

KNOWN_CATEGORIES = {
    "intended_purpose", "clinical_performance", "software_algorithm",
    "design_hardware", "patient_contact_material", "sterilization",
    "packaging_shelf_life", "manufacturing_process", "labeling_clarification",
    "administrative", "supplier_swap",
}

KNOWN_EVIDENCE_SUFFICIENCY = {"sufficient", "needs_supplement", "none"}


REQUIRED_FIELDS = {"change_category"}

# MDR: the category the change is claimed to fall in.
_CONTRACT = {
    "rule": "REQ-01-input-contract",
    "when": lambda c: any(k not in c for k in REQUIRED_FIELDS),
    "guard": True,
}


class JudgeMdrSignificance:

    """DomainJudge adapter for EU MDR significant-change."""

    CONTRACT_RULE = _CONTRACT["rule"]
    REQUIRED_FIELDS = REQUIRED_FIELDS

    domain = "mdr-significant-change"

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        reasons: List[Reason] = []
        evidence: List[Evidence] = []
        missing = [k for k in REQUIRED_FIELDS if k not in ctx]
        if missing:
            # An incomplete record is not a compliant record. Judging one reads
            # "nobody supplied this" as "nobody objected to this" -- the exact
            # shape behind five red-team defects (docs/methods/RedTeam_Probes.md).
            return {"verdict": "hold",
                    "reasons": [{"rule": _CONTRACT["rule"], "level": "major",
                                 "detail": "required input absent: "
                                           + ", ".join(missing)}],
                    "evidence": []}

        for e in ctx.get("source_refs", []) or []:
            ref = (e.get("ref") or "").strip()
            if not ref:
                continue
            evidence.append(Evidence(
                kind=(e.get("kind") or "unspecified").strip() or "unspecified", ref=ref))

        crit = False
        for rule in _CRITICAL_RULES:
            try:
                if rule["when"](ctx):
                    crit = True
                    reasons.append(Reason(rule=rule["rule"], level="critical",
                                          detail=rule["detail"]))
            except Exception:
                reasons.append(Reason(rule=rule["rule"], level="major",
                                      detail=f"rule predicate raised on ctx keys: {list(ctx.keys())}"))

        verdict = "reject" if crit else "go"

        if not crit:
            maj = False
            # CAMD FAQ 17: a design change implementing a corrective action the
            # competent authority assessed and accepted is not a significant change.
            # Significance criteria are therefore not applied to it — otherwise every
            # criterion (safety/performance above all) would re-block the very change
            # the authority just accepted.
            #
            # The exemption is deliberately SCOPED to the change that implements the
            # accepted action. Keyed on the acceptance flag alone it became a global
            # bypass: red-teaming showed an intended-purpose expansion, a safety
            # change and even a classification change all returned go by asserting
            # that some accepted corrective action existed somewhere.
            accepted_corrective = (
                ctx.get("corrective_action_accepted_by_authority") is True
                and ctx.get("implements_accepted_corrective_action") is True
            )
            for rule in ([] if accepted_corrective else _MAJOR_RULES):
                try:
                    if rule["when"](ctx):
                        maj = True
                        reasons.append(Reason(rule=rule["rule"], level="major",
                                              detail=rule["detail"]))
                except Exception as exc:  # pragma: no cover - defensive
                    reasons.append(Reason(rule=rule["rule"], level="minor",
                                          detail=f"predicate error: {exc}"))
            if maj:
                verdict = "hold"
            else:
                for rule in _MINOR_RULES:
                    try:
                        if rule["when"](ctx):
                            reasons.append(Reason(rule=rule["rule"], level="minor",
                                                  detail=rule["detail"]))
                    except Exception:
                        pass

        if verdict == "go" and not evidence:
            reasons.append(Reason(
                rule="L2-EVIDENCED", level="major",
                detail="go verdict with zero evidence refs — LGD L2 downgrades to "
                       "hold pending documented evidence."))
            verdict = "hold"

        cat = ctx.get("change_category")
        if cat is None or cat not in KNOWN_CATEGORIES:
            reasons.append(Reason(
                rule="M-MAJ-11-unknown-category", level="major",
                detail=(f"change_category {cat!r} is not a category this judge can "
                        f"place on either side of the MDCG 2020-3 test.")))
            if verdict == "go":
                verdict = "hold"

        ev = ctx.get("evidence_sufficiency")
        if ev is not None and ev not in KNOWN_EVIDENCE_SUFFICIENCY:
            reasons.append(Reason(
                rule="M-MAJ-12-unknown-evidence-sufficiency", level="major",
                detail=f"evidence_sufficiency {ev!r} is not a value this judge can classify."))
            if verdict == "go":
                verdict = "hold"

        return JudgeVerdict(verdict=verdict, reasons=reasons, evidence=evidence).to_dict()


__all__ = ["JudgeMdrSignificance", "KNOWN_CATEGORIES"]
