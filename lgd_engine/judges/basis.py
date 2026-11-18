"""Clause basis for every rule in the five shipped judges.

Doctrine this file enforces: **no rule may issue a verdict without naming the
provision it encodes.** A regulatory lead should be able to read one line and
either agree with the clause or disagree with it — never argue with "the AI".

Two kinds of basis, both allowed, never mixed silently:
  LAW      — a provision whose text we have read (statute, regulation, MDCG/CAMD
             notice, or FDA guidance). The string names the provision, not a
             secondary summary of it.
  DOCTRINE — a house rule that is not itself a legal obligation: the L2 evidence
             bar, or the fact that a judge only speaks for one jurisdiction.
             Declared as doctrine precisely so nobody mistakes it for law.

Checked against the source texts in docs/methods/Legal_Check_20261118.md
(NMPA 47号令 §79–§88 + 条例797; MDCG 2020-3 rev.1 + CAMD FAQ 17; FD&C §515C
+ 21 CFR 892.2055). `benchmarks/clause_matrix.py` fails the build if a rule is
missing here, or if an entry here names no rule that exists.
"""
from __future__ import annotations

CLAUSE_BASIS: dict[str, str] = {
    # --- 510(k) / postmarket route (judge_510k.py) ---------------------------
    "R-CRIT-01-class1-recall":
        "LAW 21 CFR 7.3(m)(1) — Class I: reasonable probability of serious adverse "
        "health consequences or death",
    "R-CRIT-02-pma-process-uncontrolled":
        "LAW FD&C Act §515(d)(6) + 21 CFR 814.39(a) — a PMA supplement is required "
        "for a change affecting safety or effectiveness",
    "R-CRIT-03-severe-harm-rootcause":
        "LAW 21 CFR 820.30(g) — design validation must demonstrate the device meets "
        "requirements; a root-cause failure voids that demonstration",
    "R-MAJ-01-needs-submission":
        "LAW 21 CFR 807.81(a)(3) — a new 510(k) is required for a change that "
        "significantly affects safety or effectiveness",
    "R-MAJ-02-nmpa-class2-maintenance":
        "LAW 条例797 第八十四条 — 二类召回/较轻罚则档（分级见《医疗器械召回管理办法》）",
    "R-MAJ-03-evidence-incomplete":
        "DOCTRINE L2 — an unevidenced go is downgraded to hold; the bar is ours, "
        "not the regulator's",
    "R-MAJ-07-class2-recall-field-correction":
        "LAW 21 CFR 7.3(m)(2) — Class II recall definition; field correction is owed",
    "R-MAJ-04-config-change-same-platform":
        "LAW 21 CFR 820.70(b) — production and process changes require validation "
        "before implementation",
    "R-MAJ-08-predicate-changed":
        "LAW 21 CFR 807.81(a)(3) — changed predicate basis means the SE comparison "
        "no longer stands",
    "R-MIN-01-label-only-no-harm":
        "LAW 21 CFR 7.3(m)(3) — Class III: unlikely adverse health consequences; "
        "label correction with no safety impact is recordable only",

    # --- EU MDR (judge_mdr.py) ----------------------------------------------
    "M-CRIT-01-change-during-open-fsca":
        "LAW MDR Art.120(3) + MDCG 2020-3 rev.1 §4.1 — a change made while an FSCA "
        "is open touches safety or performance; CAMD FAQ 17 exempts only the "
        "corrective action the authority has already assessed and accepted",
    "M-CRIT-02-significant-declared-non-significant":
        "LAW MDCG 2020-3 rev.1 §4.1 — significance has two cumulative elements; a "
        "manufacturer's declaration cannot collapse them (limitation alone excepted "
        "per CAMD FAQ 17)",
    "M-MAJ-01-intended-purpose":
        "LAW MDCG 2020-3 rev.1 §4.1 + MDR Art.120(3) — a change in intended purpose "
        "is significant; expansion yes, limitation no (CAMD FAQ 17)",
    "M-MAJ-02-clinical-benefit":
        "LAW MDCG 2020-3 rev.1 §4.3 — changes to clinical benefit are listed as "
        "significant",
    "M-MAJ-03-safety-or-performance":
        "LAW MDCG 2020-3 rev.1 §4.3 — changes affecting safety or performance are "
        "listed as significant",
    "M-MAJ-04-new-clinical-data":
        "LAW MDCG 2020-3 rev.1 §4.3 — new clinical data bearing on the benefit-risk "
        "assessment is significant",
    "M-MAJ-05-patient-contacting-material":
        "LAW MDCG 2020-3 rev.1 §4.3 — a change of patient-contacting material is "
        "listed as significant",
    "M-MAJ-06-sterilization-or-shelf-life":
        "LAW MDCG 2020-3 rev.1 §4.3 — sterilization and shelf-life changes are "
        "listed as significant",
    "M-MAJ-07-classification-change":
        "LAW MDR Annex VIII + MDCG 2020-3 rev.1 §4.3 — a classification change "
        "alters the conformity-assessment route itself",
    "M-MAJ-08-verification-not-documented":
        "DOCTRINE L2 — a non-significance conclusion is only defensible with V&V on "
        "file; MDR Art.10(9) supplies the background obligation",
    "M-MAJ-09-evidence-insufficient":
        "DOCTRINE L2 — unproven is not pass",
    "M-MAJ-10-not-eu-jurisdiction":
        "DOCTRINE scope — MDCG 2020-3 interprets MDR Art.120(3); it binds EU "
        "manufacturers only",
    "M-MIN-01-administrative":
        "LAW MDCG 2020-3 rev.1 §4.2 — administrative changes and site relocation or "
        "supplier swaps at unchanged specification are not design changes",
    "M-MIN-02-intended-purpose-limitation":
        "LAW CAMD FAQ 17 — limitations of the intended purpose are not significant "
        "within Art.120(3)",
    "M-MIN-03-corrective-action-accepted":
        "LAW CAMD FAQ 17 — design changes implementing a corrective action assessed "
        "and accepted by the competent authority are not significant",

    # --- NMPA (judge_nmpa.py) ------------------------------------------------
    "N-CRIT-01-no-certificate":
        "LAW 条例797 第二十一条 + 第八十一条(一) — 未取得注册证不得生产销售；罚则见 797 号",
    "N-CRIT-02-licence-item-filed-as-registration":
        "LAW 47号令 第七十九条 + 条例797 第八十一条(一) — 许可事项变更须经变更注册，"
        "以备案替代即落入未依法变更",
    "N-CRIT-03-level1-recall-open":
        "LAW 条例797 第八十四条 — 一级召回（分级见《医疗器械召回管理办法》）",
    "N-MAJ-01-licence-item-change":
        "LAW 47号令 第七十九条 第二款 — 名称/型号/规格/结构及组成/适用范围/产品技术要求/"
        "进口生产地址属许可事项",
    "N-MAJ-13-class1-filed-not-registered":
        "LAW 47号令 第八十八条 — 已备案产品的信息表及技术要求变化走变更备案，"
        "不存在「变更注册」这一许可",
    "N-MAJ-14-domestic-site-change-prerequisite":
        "LAW 47号令 第七十九条 末句 — 境内生产地址变更须先办生产许可变更，再备案",
    "N-MAJ-02-registration-item-change":
        "LAW 47号令 第七十九条 — 注册人/代理人名称住所等登记事项，30 日内备案",
    "N-MAJ-03-safety-effectiveness-unassessed":
        "LAW 47号令 第七十九条 第一款 — 实质性变化且可能影响安全有效的，须变更注册；"
        "未评估即无法排除该路径",
    "N-MAJ-04-technical-docs-not-updated":
        "LAW 47号令 第七十九条 + 第八十一条 — 产品技术要求属许可事项，且变更文件与原证"
        "合并使用，未更新即证载内容与实物不符",
    "N-MAJ-05-evidence-insufficient":
        "DOCTRINE L2 — 无证据的 go 降为 hold",
    "N-MAJ-06-level2-recall-open":
        "LAW 条例797 第八十四条 — 二级召回（分级见《医疗器械召回管理办法》）",
    "N-MAJ-07-not-nmpa-jurisdiction":
        "DOCTRINE scope — 47号令 与条例797 只约束境内注册人/备案人",
    "N-MIN-01-registration-textual-no-impact":
        "LAW 47号令 第七十九条 第一款末句 — 其他变化 30 日内备案；文字性更正无技术审评",

    # --- FDA PCCP (judge_pccp.py) --------------------------------------------
    "P-CRIT-01-claimed-coverage-without-pccp":
        "LAW FD&C Act §515C(a)(1)/(b)(1) — only a change consistent with an "
        "authorized or established PCCP is shielded",
    "P-CRIT-02-intended-use-change":
        "LAW §515C(b)(2)(A) + FDA PCCP guidance (4 Dec 2024) — intended-use changes "
        "stay outside PCCP coverage",
    "P-CRIT-03-acceptance-criteria-not-met":
        "LAW 21 CFR 892.2055(b)(2) — the quantitative acceptance criteria are special "
        "controls, so a non-conforming update cannot ride the plan",
    "P-CRIT-04-se-to-predicate-broken":
        "LAW §515C(b)(2)(B) — cumulative condition: the device must remain "
        "substantially equivalent to its predicate",
    "P-CRIT-05-modified-version-used-as-predicate":
        "LAW §515C(c) — a version implemented under a PCCP may not serve as a "
        "predicate; only the pre-change cleared or approved version may",
    "P-MAJ-01-outside-pccp-scope":
        "LAW §515C(b)(1) — the shield attaches only to a change consistent with the "
        "plan",
    "P-MAJ-02-modification-class-not-described":
        "LAW §515C(b)(2) + guidance Description of Modifications — an undescribed "
        "class is not a covered class",
    "P-MAJ-03-validation-not-documented":
        "LAW 21 CFR 892.2055(b)(2) — methodology and V&V must be documented",
    "P-MAJ-04-acceptance-criteria-unproven":
        "LAW 21 CFR 892.2055(b)(2) — unproven is not met",
    "P-MAJ-05-labeling-version-history-missing":
        "LAW 21 CFR 892.2055(b)(1) — labeling must carry a version history",
    "P-MAJ-06-udi-not-regenerated":
        "LAW FDA PCCP guidance (4 Dec 2024) — a new version is expected to carry a "
        "new UDI where the device has one",
    "P-MAJ-07-evidence-insufficient":
        "DOCTRINE L2 — unproven is not pass",
    "P-MAJ-08-pccp-status-unknown":
        "LAW §515C(a)/(b) — the existence of an authorized plan is the whole "
        "question, so an unstated one cannot be assumed",
    "P-MAJ-09-not-fda-jurisdiction":
        "DOCTRINE scope — §515C and 21 CFR 892.2055 bind US marketing only",
    "P-MIN-01-covered-retrain":
        "LAW §515C(b)(1) + 21 CFR 892.2055(b) — a retrain that stays inside the "
        "described class, meets its criteria and keeps V&V, version history and UDI "
        "is the case the statute was written for",

    # --- postmarket (judge_postmarket.py) ------------------------------------
    "PM-CRIT-01-class1-recall":
        "LAW 21 CFR 7.3(m)(1) — Class I recall definition",
    "PM-CRIT-02-unlicensed-on-market":
        "LAW 条例797 第八十一条(一) — 未取得注册证生产销售二/三类器械属违法",
    "PM-CRIT-03-death-or-serious-causal":
        "LAW 21 CFR 803.50 — deaths and serious injuries are reportable; a plausible "
        "causal link triggers urgent action",
    "PM-MAJ-01-class2-recall":
        "LAW 21 CFR 7.3(m)(2) — Class II recall definition",
    "PM-MAJ-02-user-config-deviation":
        "LAW 21 CFR 820.70(b) — operation outside the validated configuration is an "
        "unvalidated change",
    "PM-MAJ-03-high-report-volume":
        "DOCTRINE signal threshold — report volume is a triage trigger of ours; 21 CFR "
        "803 supplies the reporting base",
    "PM-MIN-01-class3-record":
        "LAW 21 CFR 7.3(m)(3) — Class III recall: unlikely adverse health consequences",
}


def basis_for(rule_id: str) -> str:
    """Clause basis for a rule id; empty string when the rule names none."""
    return CLAUSE_BASIS.get(rule_id, "")


def is_law(basis: str) -> bool:
    return basis.startswith("LAW ")


def shipped_rules() -> dict[str, str]:
    """rule id -> judge module, read from source so the list cannot drift.

    Parsed rather than imported on purpose: importing every judge would couple
    this audit to import side effects, and a rule list that comes from the
    judges' own source is the thing we actually want to audit.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    found: dict[str, str] = {}
    for path in sorted((root / "lgd_engine" / "judges").glob("judge_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = {k.value for k in node.keys if isinstance(k, ast.Constant)}
            if "rule" not in keys or "when" not in keys:
                continue
            for k, v in zip(node.keys, node.values):
                if (isinstance(k, ast.Constant) and k.value == "rule"
                        and isinstance(v, ast.Constant)):
                    found[v.value] = path.stem
    return found


__all__ = ["CLAUSE_BASIS", "basis_for", "is_law", "shipped_rules"]

