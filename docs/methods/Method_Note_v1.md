# A Deterministic Regulatory Change Gate: Method Note v1.2

**Project:** LGD Engine (`MedXpert-org/lgd-engine`)
**Version:** 1.2 · 2026-11-18 (v1.0 reviewed by an independent pass; see `Eval_Report_v1.md`)
**Licence:** see repository `LICENSE` / `NOTICE`
**Status:** method note (not a benchmark paper, not a product claim)

> **Revision note (v1.2).** The NMPA table was checked clause by clause against the
> consolidated statute text (Order 47 §79–§88; Reg. 797 §21/§55/§81/§84/§85) — see
> `Legal_Check_20261118.md`. Three real deviations were found and fixed: (L1) product
> class was not modelled, so a Class I change was told to seek a 变更注册 that does not
> exist for it; (L2) the penalty citation named the superseded 739 instead of the
> current 797; (L3) "textual correction of the production address" and "domestic
> production-site change" shared one field, so a genuine relocation could be filed as
> a typo fix and read as `go`. Two cases and two assertions now pin these fixes.
> MDR and PCCP remain unchecked at clause level.

> **Revision note (v1.1).** An independent evaluation run — a clean clone at a
> stranger's path, every command in §1 executed verbatim — found five issues, all
> now closed: (E1) the repository tracked two `.github` PR templates differing only
> in letter case, so any Windows/macOS clone reported a dirty tree on arrival;
> (E2) four rows of the §1 table described checks instead of giving runnable commands;
> (E3) the note did not disclose that expected verdicts were authored alongside the
> rules (see §6.7); (E4) the document claimed Python 3.10 while `pyproject.toml`
> declares `>=3.9`; (E5) the adversarial probes had no file pointer. v1.0 remains
> reproducible in history, but this version is the one to cite.

---

## Abstract

Software that helps teams decide whether a change to a medical device requires a new
regulatory submission is usually built either as a document-retrieval assistant ("here
is the relevant guidance") or as a language-model judge ("this looks like a
significant change"). Both answer in prose, both are hard to audit, and neither fails
in a way a reviewer can inspect. This note describes a different decomposition: the
regulatory decision is expressed as an ordered, executable rule table over structured
case fields; the output is a three-valued verdict (`go` / `hold` / `reject`) plus the
identifiers of the rules that fired; and the whole thing is pinned by a small case
corpus whose expected verdicts ship with the code, so any reader can re-run the
decision and compare, character by character, against what the README claims.

Five judgment tables are implemented (US 510(k) change classification, post-market
action triage, FDA PCCP scope, EU MDR significance under MDCG 2020-3, and China NMPA
change registration under Order 47). The claim this note makes is deliberately narrow:
*for the enumerated change classes, the decision is reproducible offline, its reasons
are inspectable, and its failure mode is a refusal rather than a guess.* It does not
claim to be a better general-purpose guardrail, and Section 2 lists what is not new
here.

---

## 1. Claims, and how to check each one

Every claim below is paired with the command that verifies it. If a command's output
differs from the expected line, that is a finding to report, not a documentation error
to be explained away.

| # | Claim | Check | Expected |
|---|---|---|---|
| C1 | Five judgment tables ship and run offline | `python -m lgd_engine.cli --all demo1/cases_nmpa --domain nmpa` | `5/5 cases match expected verdict` |
| C2 | Verdicts are byte-identical across runs | `python -m unittest tests.test_contract.TestCliContract.test_single_case_is_deterministic -v` | `OK` |
| C3 | A critical rule forces `reject` regardless of other judges | `python -m unittest tests.test_contract.TestThreeLaws.test_l3_critical_forces_reject -v` | `OK` |
| C4 | A `go` with no evidence is downgraded to `hold` | `python -m unittest tests.test_contract.TestThreeLaws.test_l2_go_without_evidence_is_hold -v` | `OK` |
| C5 | A crashing judge is not a legitimate veto | `python -m unittest tests.test_contract.TestThreeLaws.test_crashing_judge_is_reject_and_flagged -v` | `OK` |
| C6 | Exit codes carry meaning distinct from prose | `python -m lgd_engine.cli --case demo1/cases_nmpa/nmpa04_red_licence_as_filing.json --domain nmpa; echo $?` (PowerShell: `$LASTEXITCODE`) | `2` (reject); `0` = go; `64` = usage error |
| C7 | Read-only role cannot record a decision | `python lgd_engine/mcp_smoke.py` | `SMOKE: PASS` |
| C8 | A keyword shortcut fails where the tables do not | `python benchmarks/adversarial_baseline.py` | `gate 12/12`, `naive 5/12` |
| C9 | The browser dossier cannot drift from the code | `python benchmarks/build_demo_page.py --check` | `OK` |
| C10 | All of the above run on every push | GitHub Actions `gate` workflow | green on every commit cited below |

The assertion count grows as tables are added. As of this version: **40 assertions**,
**24 case files**, **5 tables**, **12 adversarial probes**.

---

## 2. What is *not* new here

Being explicit about this is part of the method; a claim that everything is novel is
usually a claim that nothing was checked.

- **Deterministic policy evaluation is not new.** Open Policy Agent (Rego), AWS Cedar
  and similar engines evaluate declarative policy deterministically, with audit trails.
- **Pre-execution interception of agent actions is not new.** Microsoft's
  `agent-governance-toolkit` (public repository, ~6.5k stars at the time of writing)
  describes deterministic pre-execution checks, identity and sandboxing; NVIDIA
  NeMo Guardrails and Guardrails AI occupy adjacent ground with input/output rails.
- **Regulatory decision trees are not new.** Notified bodies, consultancies and
  several commercial tools encode "does this change require a new submission" logic.
- **Splitting a verdict into three values is not new.** Tri-state review outcomes are
  standard in quality systems.

What this work does differently is narrower than "a better guardrail": it publishes
*executable rule tables whose inputs are the fields a regulatory reviewer actually
has*, ships the case corpus that pins them, and treats "cannot classify" as a refusal
rather than a pass. Section 7 states the resulting gap precisely.

---

## 3. Method

### 3.1 Three laws, operationalised

The project's own framing uses three laws; here they are as mechanisms, not slogans.

| Law | Mechanism in code | Observable consequence |
|---|---|---|
| **L1 Recorded** (有籍) | Every evaluated case can be persisted append-only with case id, verdict, rationale | A decision exists outside the reviewer's head; a later reviewer can diff it |
| **L2 Evidenced** (有证) | `go` with zero evidence refs is downgraded to `hold`, and the downgrade is recorded as a rule hit | Optimism cannot pass silently; the absence of evidence is itself a finding |
| **L3 Gated** (有门禁) | Any `critical` reason forces `reject`, regardless of other judges' verdicts | A single veto is not averaged away by consensus |

The laws are enforced in `lgd_engine/gate/engine.py` and asserted in
`tests/test_contract.py`; they are not documentation claims.

### 3.2 Judge contract

A judgment table is a pure function:

```
ctx (structured case fields) → {verdict, reasons[], evidence[]}
```

where each reason is `{rule: stable id, level: critical|major|minor, detail: text}` and
each evidence item is `{kind, ref}`. Purity matters for three reasons: the same input
must give the same output (C2); a unit test can call the judge without a server (C3);
and a reason id can be cited in an audit record without quoting prose.

Rule ids are stable strings (`N-CRIT-02-licence-item-filed-as-registration`,
`M-CRIT-01 change-during-open-fsca`). They are the citation unit — a reviewer
disagreeing with a decision can name the rule, not the paragraph.

### 3.3 Verdict algebra

Aggregation is intentionally non-Bayesian and non-voting:

```
if any critical            → reject      (L3; the veto is absolute)
else if any major          → hold
else if any go and evidence → go          (L2 applied at aggregate level too)
else                       → hold        (no judges ran / nothing established)
```

Two failure semantics are load-bearing:

1. **A crashing judge is an error, not a verdict.** The engine records the exception
   in `errors[]` and returns `reject`, but the CLI's distinct exit codes and the
   populated `errors[]` let a consumer tell "the tool broke" from "the change is
   rejected." Without this, a broken install would read as a legitimate veto.
2. **Unknown is not a pass.** Unmapped field names, unknown enum values, unknown
   routes and missing change fields each push the verdict to `hold`. An implementation
   that defaults to `go` on unrecognised input is wrong in the direction that hurts.

### 3.4 Cross-jurisdiction non-impersonation

Regulatory change rules differ by jurisdiction, and a table written for one regulator
must not answer for another. The tables therefore declare their jurisdiction and
`hold` explicitly when the input is outside it — MDR holds on `jurisdiction=FDA`,
PCCP holds on non-FDA input, NMPA holds on non-NMPA input — with the reason stating
that the question belongs to another route. Refusing to answer is the correct
behaviour here, and it is asserted rather than assumed.

A useful side effect: one case file (`demo1/cases_jurisdiction/supplier_swap.json`)
declares *per-jurisdiction expectations* for the same material — `hold` for FDA,
`go` for NMPA — and the dossier page displays both, so the divergence is visible
rather than buried.

### 3.5 The five tables

| Table | Jurisdiction | Question answered | Codes |
|---|---|---|---|
| 510(k) change classification | FDA / NMPA | new 510(k) needed? | `judge_510k.py` |
| Post-market action triage | FDA / NMPA | what to do after an event | `judge_postmarket.py` |
| PCCP scope | FDA (FD&C §515C, FDORA 2022; 21 CFR 892.2055) | covered by an authorised PCCP? | `judge_pccp.py` |
| EU MDR significance | EU (Reg. 2017/745 Art.120 + Annex IX; MDCG 2020-3 rev.1) | significant → notified body? | `judge_mdr.py` |
| NMPA change registration | China (Order 47 §79; Reg. 797 §21/§55/§81) | 变更注册 / 备案 / re-registration | `judge_nmpa.py` |

Two of these tables share a design pattern worth naming, because it is where
shortcuts hide: **the route is decided by the field, not by the applicant's
declaration.** Filing a licence-item change as a registration filing, or declaring an
intended-purpose change "not significant", is a `reject` — not a slower `hold`. The
shortcut is not merely discouraged; the route is marked unavailable.

---

## 4. Case corpus and the adversarial baseline

### 4.1 Corpus

24 case files across 5 directories (`demo1/cases*`), each with a declared expected
verdict (or a per-jurisdiction pair). Cases are desensitised constructs, not
customer data; `_desensitized_from` records what real-world pattern each one models.
Every case is evaluated by the same code path used in production; there is no
"test-only" branch.

### 4.2 Baseline, and why it is included

A comparison against a stronger system would require access this project does not
have. What is available — and more informative for the specific failure modes here —
is a *plausible shortcut*: a classifier that reads the JSON keys and text for
keywords (`class1`/`severe` → reject; `requires_submission` truthy or "intended_use"
present → hold; else go). Both implementations and all 12 probes live in
`benchmarks/adversarial_baseline.py`, so a reader can inspect, extend or falsify
the comparison rather than take its verdict. On the fixed probes:

```
gate  : 12/12 match expected
naive : 5/12 match expected
delta : 7 probes the shortcut gets wrong
```

The shortcut fails in **both** directions, which is the point:

- **False permits (4):** empty evidence, unknown change type, unknown safety class,
  and the string `"yes"` accepted as an equivalent declaration.
- **False blocks (3):** a green PCCP case held because the JSON contained the *key*
  `affects_intended_use` with value `false` — key presence mistaken for key meaning.

A keyword classifier cannot distinguish "the field exists" from "the field is true",
and cannot distinguish "no evidence supplied" from "evidence not applicable". These
are the two error classes the rule tables are built to avoid, and the baseline makes
that concrete instead of asserting it.

The comparison is explicitly bounded: 12 probes, a synthetic shortcut rather than a
commercial product, and no claim about any vendor's accuracy. It is a sanity floor,
not a leaderboard.

---

## 5. Reproducibility protocol

A third party needs no credentials, no network, and no third-party packages
(the engine declares `dependencies = []` and `requires-python = ">=3.9"`).

```bash
git clone https://github.com/MedXpert-org/lgd-engine
cd lgd-engine
python -m unittest discover -s tests -v          # 40 assertions
python lgd_engine/mcp_smoke.py                   # 7 tools, RBAC both ways
python benchmarks/adversarial_baseline.py        # 12/12 vs 5/12
python benchmarks/build_demo_page.py --check     # dossier in sync with the code
```

Browser-only readers can open `demo/judge-dossier.html`, or the public mirror linked
from the README; the page is generated by the engine, and the `--check` step fails CI
whenever it drifts, so the page cannot state a verdict the code does not produce.

**Provenance.** Each change to the tables or the corpus is a commit with a CI run id
in the project log; the run is public. A reader disputing a verdict has the commit,
the run, and the command.

---

## 6. Limitations and threat model

Stated plainly, because a gate that oversells itself is a liability.

1. **Enumerated classes only.** The tables decide only the change classes they
   enumerate; anything outside is `hold`. Coverage is the bottleneck, not
   cleverness. IVDR and other regimes are deliberately unimplemented.
2. **Not a legal opinion.** The output is an initial screen against published
   criteria; it does not replace a regulator's or notified body's assessment, and it
   does not read the guidance documents themselves — rules are code, and changing a
   rule requires changing code and passing CI.
3. **Input quality dominates.** Every field is supplied by the caller. A gate fed
   optimistic fields will return an optimistic verdict, correctly and reproducibly.
   The evidence rule (L2) raises the cost of optimism; it does not detect lying.
4. **No identity or sandbox layer.** This repository does not authenticate callers,
   sandbox execution, or manage secrets; RBAC here means "which MCP tools a role may
   call" and nothing more.
5. **Corpus size.** 26 cases is enough to pin behaviour, not enough to estimate
   accuracy. No precision/recall figure is claimed, because none was measured.
6. **Adversarial robustness is bounded.** `security/` and `review/` contain injection
   and fail-closed probes; they establish specific properties on specific inputs,
   not immunity.
7. **The expected verdicts are not independent of the rules.** The case corpus was
   authored alongside the tables, by the same author. It therefore *pins behaviour*
—it catches regressions, and it lets a stranger see what the code does—but it does
   not independently validate that the rules match regulatory practice. A different
   author writing the cases from the regulations alone would be a stronger test, and
   has not been done. Readers should treat corpus agreement as consistency evidence,
   not as accuracy evidence.

---

## 7. Positioning: the gap that is actually open

Public repositories in the adjacent space, observed via the GitHub API on
2026-11-18 (stars are an observation of that moment, not a quality measure):

| Project | Stars | What it provides |
|---|---|---|
| `guardrails-ai/guardrails` | ~7.6k | validation rails for LLM I/O |
| `NVIDIA-NeMo/Guardrails` | ~7.5k | programmable conversation rails |
| `microsoft/agent-governance-toolkit` | ~6.6k | deterministic pre-execution checks, identity, sandbox |
| `protectai/llm-guard` | ~3.2k | input/output scanning |
| `openguardrails/openguardrails` | ~0.4k | open guardrail protocol |
| **`MedXpert-org/lgd-engine`** | **0** | 5 regulatory judgment tables, 24 pinned cases, public CI |

On breadth, identity, sandboxing and ecosystem size, the established projects are
far ahead, and any claim of general superiority would be false. The gap this work
occupies is narrower and can be checked: **the adjacent regulatory tools retrieve
and summarise (what does the guidance say) — this one returns a verdict with
rule-level reasons over the fields a reviewer holds, offline, with a corpus that
pins it.** Whether that gap is worth occupying is a question for readers, not for
this note.

---

## 8. How to cite

```
Zhao, X. (2026). A Deterministic Regulatory Change Gate: Method Note v1.2.
LGD Engine, MedXpert-org/lgd-engine. https://github.com/MedXpert-org/lgd-engine
```

If a DOI is minted for this note, cite the DOI version; the repository commit hash
identifies the exact code the claims were checked against.

---

## Appendix A — Rule tables (summary)

**510(k)** — risk class, change type, safety impact, submission requirement,
predicate status, evidence sufficiency, recall class.
**Post-market** — event severity, reportability, corrective action status, evidence.
**PCCP** — authorised PCCP present, change within scope, acceptance criteria met,
intended-use change, verification filed, labelling/UDI updated.
**MDR** — FSCA open, significance criteria (intended purpose, clinical benefit,
safety/performance, new clinical data, patient-contacting materials, sterilisation,
classification), declaration vs criteria, evidence.
**NMPA** — certificate in force, change fields (licence vs registration tables),
requested route, safety-effectiveness assessment, technical documents updated,
recall level, evidence.

Full rule ids, conditions and rationales are in each judge module and in
`docs/*判定器_*.md`; the dossier page lists what fired for every shipped case.

## Appendix B — Reproduction checklist

- [ ] Clone, run the four commands in §5; compare each line to the expected output.
- [ ] Open the dossier page; pick one `reject` case; read the rule id that fired.
- [ ] Change one field in a copy of that case to make the veto inapplicable; re-run;
   confirm the verdict moves as the rule table (not the prose) implies.
- [ ] Run `build_demo_page.py --check` after any edit; confirm the guard works.
- [ ] If any step disagrees, open an issue with the command and the output.

---

## 中文摘要

本方法说明描述一种把"监管变更判定"从自然语言问答改写成可执行规则表的方法：输入是评审人实际持有的结构化字段，输出是三值判决（go / hold / reject）加上被触发的规则编号；判定纯粹、可离线重跑、失败时表现为"拒绝回答"而非"猜测"。已实现五张判定表（美国 510(k) 变更分类、上市后处置、FDA PCCP 范围、EU MDR 重大变更、中国 NMPA 变更注册），随包发布 24 个带预期判决的案件与 12 条对抗探针；同一批输入下，确定性判定器 12/12 命中预期，关键词捷径仅 5/12。

本说明明确划出边界：确定性策略求值、智能体前置拦截、监管决策树均非本文首创；本文的贡献限于"把可枚举的变更类别做成可复跑的规则表，并用案件语料钉住行为"。不宣称精度/召回率，不宣称可替代监管判断，不宣称具备身份与沙箱能力。截至本版本：40 条契约断言、5 张判定表、26 个案件、7 个 MCP 工具，全部由公共 CI 每次推送执行。
