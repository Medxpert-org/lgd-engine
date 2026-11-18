"""NMPA change-registration judge (China).

Domain: nmpa-change-registration

Question: *for a registered/filed device in China, does this change need a 变更注册
(licence-item change), only a 备案 (registration-item filing), or a fresh
registration?*

Public basis (citable, offline):
  - 《医疗器械注册与备案管理办法》(国家市场监督管理总局令第 47 号, 2021-10-01 施行).
    It splits post-market changes into 许可事项变更 (product name, model/specification,
    structure and composition, 适用范围, product technical requirements, and for
    imported devices the manufacturing site) and 登记事项变更 (registrant name /
    address, agent, textual corrections to the production address), with a 备案 for
    the latter. A change outside both categories may require re-registration.
  - 《医疗器械监督管理条例》(国务院令第 739 号) — 未依法注册/备案不得生产、进口、销售.

Verdict mapping:
  go     = no licence-item change; filing (if any) is the correct route
  hold   = the correct route exists but must be completed first (变更注册 or 备案)
  reject = the proposed route is not available at all (no certificate, or a licence
           item being filed as a registration item to skip review)

This judge speaks for NMPA only. Other jurisdictions produce a hold with an explicit
reason rather than a guess.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .base import DomainJudge, JudgeVerdict, Reason, Evidence

# 许可事项变更 — these force a 变更注册.
LICENCE_FIELDS = {
    "product_name", "model_specification", "structure_composition",
    "scope_of_application", "technical_requirements", "import_manufacturing_site",
}
# 登记事项变更 — these are filed (备案), not reviewed.
REGISTRATION_FIELDS = {
    "registrant_name", "registrant_address", "agent_name", "agent_address",
    "production_address_textual",
}
ALL_FIELDS = LICENCE_FIELDS | REGISTRATION_FIELDS

_CRITICAL_RULES = [
    {
        "rule": "N-CRIT-01-no-certificate",
        "detail": "No registration certificate / filing voucher in force while a "
                  "change is being made — 条例 739: unregistered devices may not be "
                  "produced, imported or sold. Veto.",
        "when": lambda c: (
            c.get("has_registration_certificate") is False
            and bool(c.get("change_fields"))
        ),
    },
    {
        "rule": "N-CRIT-02-licence-item-filed-as-registration",
        "detail": "A 许可事项变更 is being filed as a 登记事项备案 to skip technical "
                  "review — the route chosen is not available for this field. Veto.",
        "when": lambda c: (
            c.get("requested_path") == "filing"
            and bool(set(c.get("change_fields") or []) & LICENCE_FIELDS)
        ),
    },
    {
        "rule": "N-CRIT-03-level1-recall-open",
        "detail": "A 一级 recall is open while the change touches 适用范围 or "
                  "structure/composition — releasing it now compounds the harm. Veto.",
        "when": lambda c: (
            c.get("recall_level") == "level1"
            and bool(set(c.get("change_fields") or []) & {"scope_of_application",
                                                         "structure_composition"})
        ),
    },
]

_MAJOR_RULES = [
    {
        "rule": "N-MAJ-01-licence-item-change",
        "detail": "The change touches a 许可事项 field — 变更注册 must be approved "
                  "before the change takes effect.",
        "when": lambda c: bool(set(c.get("change_fields") or []) & LICENCE_FIELDS),
    },
    {
        "rule": "N-MAJ-02-registration-item-change",
        "detail": "The change is a 登记事项 change — 备案 must be completed (filing "
                  "is not optional just because it is not reviewed).",
        "when": lambda c: (
            bool(set(c.get("change_fields") or []) & REGISTRATION_FIELDS)
            and c.get("safety_effectiveness_assessed") is not True
        ),
    },
    {
        "rule": "N-MAJ-03-safety-effectiveness-unassessed",
        "detail": "Whether the change affects safety or effectiveness was not assessed "
                  "— 47 号令 routes every change through that judgement first.",
        "when": lambda c: c.get("safety_effectiveness_assessed") is not True,
    },
    {
        "rule": "N-MAJ-04-technical-docs-not-updated",
        "detail": "Product technical requirements / IFU have not been updated for the "
                  "change — the registered documents and the shipped device diverge.",
        "when": lambda c: c.get("technical_docs_updated") is False,
    },
    {
        "rule": "N-MAJ-05-evidence-insufficient",
        "detail": "Evidence package absent or incomplete — LGD L2 downgrades a go to "
                  "hold pending documented evidence.",
        "when": lambda c: c.get("evidence_sufficiency") in {"needs_supplement", "none"},
    },
    {
        "rule": "N-MAJ-06-level2-recall-open",
        "detail": "A 二级 recall is open — a corrective action is owed regardless of "
                  "which fields change; hold pending CAPA.",
        "when": lambda c: c.get("recall_level") == "level2",
    },
    {
        "rule": "N-MAJ-07-not-nmpa-jurisdiction",
        "detail": "This judge speaks for NMPA (China) only — another jurisdiction has "
                  "its own change route; hold pending that route.",
        "when": lambda c: (c.get("jurisdiction") or "NMPA").strip().upper() != "NMPA",
    },
]

_MINOR_RULES = [
    {
        "rule": "N-MIN-01-registration-textual-no-impact",
        "detail": "Textual 登记事项 correction with a documented no-impact assessment — "
                  "file only, no technical review required.",
        "when": lambda c: (
            bool(set(c.get("change_fields") or []) & REGISTRATION_FIELDS)
            and c.get("safety_effectiveness_assessed") is True
        ),
    },
]

KNOWN_REQUESTED_PATHS = {"licence_change", "filing", "new_registration", "none"}
KNOWN_EVIDENCE_SUFFICIENCY = {"sufficient", "needs_supplement", "none"}
KNOWN_RECALL_LEVELS = {"none", "level1", "level2", "level3"}


class JudgeNmpaChangeRegistration:
    """DomainJudge adapter for NMPA change registration."""

    domain = "nmpa-change-registration"

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        reasons: List[Reason] = []
        evidence: List[Evidence] = []

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
            for rule in _MAJOR_RULES:
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

        # Unknown is not a safe default: unmapped fields, unknown path values, and
        # unknown enums all land on hold rather than riding out as go.
        unknown = [f for f in (ctx.get("change_fields") or []) if f not in ALL_FIELDS]
        if unknown:
            reasons.append(Reason(
                rule="N-MAJ-08-unknown-change-field", level="major",
                detail=f"change field(s) {unknown} are not in the 47 号令 tables — "
                       f"cannot route a field this judge cannot classify."))
            if verdict == "go":
                verdict = "hold"
        if not ctx.get("change_fields"):
            reasons.append(Reason(
                rule="N-MAJ-09-no-change-fields", level="major",
                detail="No change field supplied — 有籍 requires the change be "
                       "classified before a verdict."))
            if verdict == "go":
                verdict = "hold"

        rp = ctx.get("requested_path")
        if rp is not None and rp not in KNOWN_REQUESTED_PATHS:
            reasons.append(Reason(
                rule="N-MAJ-10-unknown-requested-path", level="major",
                detail=f"requested_path {rp!r} is not a route this judge knows."))
            if verdict == "go":
                verdict = "hold"

        ev = ctx.get("evidence_sufficiency")
        if ev is not None and ev not in KNOWN_EVIDENCE_SUFFICIENCY:
            reasons.append(Reason(
                rule="N-MAJ-11-unknown-evidence-sufficiency", level="major",
                detail=f"evidence_sufficiency {ev!r} is not a value this judge can classify."))
            if verdict == "go":
                verdict = "hold"

        rl = ctx.get("recall_level")
        if rl is not None and rl not in KNOWN_RECALL_LEVELS:
            reasons.append(Reason(
                rule="N-MAJ-12-unknown-recall-level", level="major",
                detail=f"recall_level {rl!r} is not a level this judge can classify."))
            if verdict == "go":
                verdict = "hold"

        return JudgeVerdict(verdict=verdict, reasons=reasons, evidence=evidence).to_dict()


__all__ = ["JudgeNmpaChangeRegistration", "LICENCE_FIELDS", "REGISTRATION_FIELDS"]
