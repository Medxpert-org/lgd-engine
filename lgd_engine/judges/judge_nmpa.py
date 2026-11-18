"""NMPA change-registration judge (China).

Domain: nmpa-change-registration

Question: *for a registered/filed device in China, does this change need a 变更注册
(licence-item change), only a 备案 (registration-item filing), or a fresh
registration?*

Public basis (citable, offline) — article text verified 2026-11-18 against the
consolidated statute database (see docs/methods/Legal_Check_20261118.md):
  - 《医疗器械注册与备案管理办法》(国家市场监督管理总局令第 47 号, 2021-08-26 公布,
    2021-10-01 施行), 第七十九条: a substantive change (design, raw material, process,
    适用范围, method of use) that may affect safety or effectiveness requires 变更注册;
    other changes require 备案 within 30 days. The same article enumerates the
    registration-certificate fields: 产品名称、型号、规格、结构及组成、适用范围、
    产品技术要求、进口医疗器械的生产地址 → 变更注册; 注册人名称和住所、代理人名称和
    住所 → 备案; 境内医疗器械生产地址变更 → 生产许可变更后办理备案.
  - 《医疗器械监督管理条例》(国务院令第 797 号, 2024 修订; 前身为 739 号) 第二十一条
    (same split), 第八十一条(一) (生产、经营未取得注册证的第二类、第三类医疗器械 →
    没收并罚款), 第五十五条 (不得经营、使用未依法注册或备案的器械).
  - 第一类医疗器械实行备案管理（条例第二十一条参照 47 号令第八十八条：已备案产品的
    备案信息表内容及产品技术要求变化 → 变更备案），因此一类产品的同类变更走备案，
    不走变更注册。

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

# 许可事项变更 — these force a 变更注册 (第二类/第三类).
LICENCE_FIELDS = {
    "product_name", "model_specification", "structure_composition",
    "scope_of_application", "technical_requirements", "import_manufacturing_site",
}
# 登记事项变更 — filed (备案), not technically reviewed.
REGISTRATION_FIELDS = {
    "registrant_name", "registrant_address", "agent_name", "agent_address",
}
# 境内生产地址变更 — 47 号令 requires 生产许可变更 first, then 备案. Kept separate so
# the reason text can name the prerequisite instead of silently filing it.
DOMESTIC_SITE_FIELDS = {"domestic_manufacturing_site"}
# A textual correction to an address already on the certificate is not an address
# change; it needs the no-impact assessment, not the 生产许可 round.
TEXTUAL_FIELDS = {"production_address_textual"}
ALL_FIELDS = LICENCE_FIELDS | REGISTRATION_FIELDS | DOMESTIC_SITE_FIELDS | TEXTUAL_FIELDS

_CRITICAL_RULES = [
    {
        "rule": "N-CRIT-01-no-certificate",
        "detail": "No registration certificate / filing voucher in force while a "
                  "change is being made — 条例 797 第八十一条(一): producing or trading "
                  "a Class II/III device without a registration certificate is "
                  "confiscated and fined; 第五十五条 bars trading or using it. Veto.",
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
            # For Class I the filing route is the correct instrument, so it must not
            # be read as an evasion of technical review.
            and str(c.get("device_class") or "").strip().upper() not in {"I", "1", "一类"}
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
                  "before the change takes effect (Class II/III devices).",
        # Class I is filed (备案管理), so its licence-field change is 变更备案, not
        # 变更注册 — routed by N-MAJ-13 instead of being labelled with the wrong
        # instrument. Without this guard a Class I change would be told to seek a
        # 变更注册 that does not exist for it.
        "when": lambda c: (
            bool(set(c.get("change_fields") or []) & LICENCE_FIELDS)
            and str(c.get("device_class") or "").strip().upper() not in {"I", "1", "一类"}
        ),
    },
    {
        "rule": "N-MAJ-13-class1-filed-not-registered",
        "detail": "Class I devices are 备案管理 — the equivalent change is 变更备案, "
                  "not 变更注册. The obligation is real; the instrument is different.",
        "when": lambda c: (
            bool(set(c.get("change_fields") or []) & LICENCE_FIELDS)
            and str(c.get("device_class") or "").strip().upper() in {"I", "1", "一类"}
        ),
    },
    {
        "rule": "N-MAJ-14-domestic-site-change-prerequisite",
        "detail": "47 号令 第七十九条: a domestic production-site change requires the "
                  "生产许可 change first and the 备案 after it — filing alone skips "
                  "a precondition that exists in the statute.",
        "when": lambda c: bool(set(c.get("change_fields") or []) & DOMESTIC_SITE_FIELDS),
    },
    {
        "rule": "N-MAJ-15-class1-no-registration-route",
        "detail": "Class I devices are 备案管理 — 47 号令 has no 变更注册 and no 首次注册 "
                  "for them. The requested route does not exist for this class, so the "
                  "answer cannot be go however clean the change looks; the instrument "
                  "has to be 备案 (变更备案 / 首次备案).",
        # Keyed on the ROUTE, not on the fields: the field-based rule above misses the
        # case where an administrative change is sent down a registration route, which
        # is exactly how a route that does not exist survives review.
        "when": lambda c: (
            str(c.get("device_class") or "").strip().upper() in {"I", "1", "一类"}
            and str(c.get("requested_path") or "").strip()
            in {"licence_change", "new_registration"}
        ),
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
            bool(set(c.get("change_fields") or []) & (REGISTRATION_FIELDS | TEXTUAL_FIELDS))
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


__all__ = ["JudgeNmpaChangeRegistration", "LICENCE_FIELDS", "REGISTRATION_FIELDS",
           "DOMESTIC_SITE_FIELDS", "TEXTUAL_FIELDS"]
