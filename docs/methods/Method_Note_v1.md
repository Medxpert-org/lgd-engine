# A Deterministic Regulatory Change Gate: Method Note v1.2

**Project:** LGD Engine (`MedXpert-org/lgd-engine`)
**Version:** 1.2 · 2026-11-18 (v1.0 reviewed by an independent pass; see `Eval_Report_v1.md`)
**Licence:** see repository `LICENSE` / `NOTICE`
**Status:** method note (not a benchmark paper, not a product claim)

> **Revision note (v1.6).** The clause matrix now travels with the dossier page, so
> an outsider can read rule→provision without cloning anything, and the page's case
> and assertion counts are computed from the repository at build time instead of
> hard-coded (they had drifted to "19 cases / 36 assertions" while the repo shipped
> 30 / 49). Two guard fixes: `--check` now normalises each side against the timestamp
> found *in that side* — passing an external clock made it fail whenever a build and
> a check straddled a minute boundary, a false alarm that would have taught us to
> ignore the guard.

> **Revision note (v1.5).** Clause-level verification of all five tables exposed one
> remaining structural weakness: a rule could state a conclusion without naming the
> provision behind it, which makes it indistinguishable from an opinion. Now every
> shipped rule carries a basis in `lgd_engine/judges/basis.py`, labelled **LAW** (a
> provision whose text we read) or **DOCTRINE** (a house rule declared as such — the L2
> evidence bar, or the fact that a judge speaks for one jurisdiction only). Current
> split: **67 rules · 55 LAW · 12 DOCTRINE · 0 unbased**, enforced in both directions by
> `TestClauseBasis` (a rule with no basis fails; a basis entry naming no rule also
> fails, because dead authority is how citation tables rot while still looking
> complete). Readable form: `docs/methods/Clause_Matrix.md`. The doctrinal share is
> capped at 12 by test, so it cannot quietly grow into a majority of opinions wearing
> the clothes of law. Assertions 45 → 60; the out-of-tree evaluator gained C10.

> **Revision note (v1.4).** The last unchecked table — FDA PCCP — was verified against
> FD&C §515C and 21 CFR 892.2055. Three gaps closed: (L6) the 510(k) route has **two
> cumulative conditions** (safe-and-effective AND still substantially equivalent to the
> predicate) and we modelled only the first, so an update that broke equivalence to the
> predicate could have been read as `go`; (L7) §515C(c) forbids treating a
> **PCCP-modified version as a predicate**, a prohibition that belongs to no single
> device and is therefore usually unencoded — now a veto; (L8) the guidance date was
> wrong (final guidance issued 4 Dec 2024, not Aug 2025). All five tables are now
> clause-checked; PCCP cases 5 → 7, assertions 43 → 45.

> **Revision note (v1.3).** The MDR table was checked against MDCG 2020-3 rev.1 §4.1–§4.2
> and CAMD FAQ 17. Two over-blocks were found, both legal routes our table was refusing:
> (L4) a *limitation* of intended purpose (removed patient group, added contraindication)
> was treated as significant, so a manufacturer shrinking its own claim was told to seek
> notified-body assessment; (L5) a design change implementing a corrective action the
> competent authority had assessed and accepted was still vetoed by the open-FSCA rule and
> re-blocked by the significance criteria. Both now route to `go` with their own reason
> codes; the expansion/limitation asymmetry is pinned by a test. MDR cases 5 → 7,
> assertions 40 → 43.

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

The assertion count grows as tables are added. As of this version: **88 assertions**,
**37 case files** (31 corpus + 6 red-team), **5 tables**, **12 adversarial probes**.

### 1.5 One defect this method found in itself

The corpus above was written by the same author as the rules, which is the weakest
possible form of evidence. So the rules were attacked from the other side: a Class I
device (备案管理) was given an *administrative* field change and sent down a
**变更注册** route and, separately, a **首次注册** route. Both came back **go**.

The cause was structural, not a typo: the class/route check was keyed on the *changed
fields* (`N-MAJ-13` fires only when a 许可事项 field changes on a Class I device), so
an administrative change riding a registration route was never examined — the route
itself was the thing that did not exist, and it passed. `N-MAJ-15` now keys on the
requested route, and the two probes ship as cases `NMPA-RED-01/02` with declared
expectations, so the gap cannot silently reopen.

This is the intended shape of the evidence: **a rule table that has never convicted
itself has not been tested**, only reviewed.

### 1.6 Two more, and the class they belong to

Red-teaming was then pushed into the remaining domains, looking for one specific
shape: **a single self-declared flag that switches off a whole block of rules.**

**MDR — the accepted-corrective-action flag.** `corrective_action_accepted_by_authority:
true` skipped *every* major rule, so an expansion of indication, a change affecting
safety or performance, and a change of risk class all returned **go**. The exemption
in CAMD FAQ 17 is for *the change that implements* the accepted corrective action; the
code read "an accepted action exists" as "this change is accepted". `M-MAJ-13` now
requires both markers, and the lawful case keeps its route by declaring the
implementation.

**510(k) — a value the vocabulary knew and the table never placed.** `label_expansion`
was in `KNOWN_CHANGE_TYPES`, matched no rule, and returned go with an **empty reason
chain** — a labelling change that adds a patient population riding the label-correction
path, against 21 CFR 807.81(a)(3)(i). `R-MAJ-09` places it on the new-510(k) side.

The second one generalised: the guard against unknown values only fires for values the
table does *not* know. A test that walks the vocabulary found **four more** types
claimed only conditionally (`design_defect`, `material_nonconforming`,
`process_change_control`, `maintenance_execution`) — each returning an empty-chain go
when handed neutral facts. Rather than four more predicate rules, `R-MAJ-10` closes the
class: **a verdict that cannot name its rule is not a verdict**, so it holds. A test now
requires every known change type to be claimed by at least one rule, which is what
turned one defect into an inventory.

### 1.7 The question the table forgot to ask

Postmarket surveillance was the next domain, and one probe was enough: a record with
`harm_severity: death` and `recall_class: none` came back **go with an empty reason
chain**.

The table only asked *"is there a recall?"* — the answer was no, so nothing fired. But
**21 CFR 803.50 does not wait for a recall class**: a device-related death or serious
injury is reportable within 30 days. `PM-MAJ-04` now fires on the harm severity itself,
independently of the recall axis. It is the same error as the MDR acceptance flag in a
different dress: **a rule that conditions on a downstream artefact (a recall class, an
acceptance marker) inherits the artefact's absence as permission.**

The green path got the matching fix: `PM-MIN-02` makes every go name the rule that let
it through, so silence is no longer indistinguishable from "the table has nothing for
this field". The rule is declared (`"guard": True`), not inlined — the clause matrix
immediately reported an inlined copy as dead authority, which is what an undeclared
rule is.

---

### 1.8 Absence was the cheapest way through

PCCP was the last domain, and the probe was one line: delete a field from an otherwise
compliant record.

Four special controls — the modification class description, the validation record, the
labeling version history, the new UDI — were tested with `is False`. **A field that was
simply absent returned go.** Nothing was falsified; the record did not mention it, and
the gate read silence as satisfaction.

The table already carried the right doctrine one rule earlier: `P-MAJ-04` says *unproven
is not met* for the acceptance criteria. It had never been applied to the other four.
They now test `is not True`, so `False` and absent land the same way; `pccp08` ships as
`FDA-PCCP-RED-01`.

Two things fell out of the fix, both worth more than the fix itself:

- **The fixtures encoded the hole.** The MCP reachability test asserted `go` for a
  payload that omitted four of the controls, and the three domain tests asserted the
  literal `"7/7"` / `"9/9"` — the same fixed tax removed from the evaluator two
  revisions earlier, still sitting in the suite. Adding one legitimate case broke a test
  for a reason unrelated to the case. They now count the files on disk.
- A suite that only ever exercises a *complete* record cannot tell "met" from
  "unspecified". `TestPccpAbsence` asserts both spellings of "not shown" get the same
  verdict.

### 1.9 From a habit to a mechanism

Five domains, five fixes, one shape: rule after rule waited on an intermediate artefact,
so the artefact's absence read as permission. By the fifth fix it was clear the
per-domain patches were the wrong unit. A list of twenty fixed predicates only covers
the twenty absent fields someone happened to think of; the twenty-first would be found
by whoever came next, and they would be right to call it a bug.

So the input contract stops being a document and becomes an assertion at run time. Each
judge declares `REQUIRED_FIELDS` — the smallest set of keys without which it cannot say
anything at all — and `evaluate()` refuses to judge a record that omits one:

    missing = [k for k in REQUIRED_FIELDS if k not in ctx]
    if missing:
        return {"verdict": "hold", "reasons": [{"rule": "REQ-01-input-contract", ...}]}

The sets are deliberately *minimal*, not the whole schema: 510(k) asks for `change_type`,
MDR for `change_category`, NMPA for `change_fields` and `requested_path`, PCCP for
`pccp_authorized` and `change_within_pccp_scope`, postmarket for `recall_class` and
`harm_severity`. A field that only makes a case richer is not required; a field without
which the table has nothing to look up is.

Three things keep this honest:

- **One rule, not five.** `REQ-01-input-contract` is a single cross-cutting rule with a
  single basis entry, in the same position as `L2-EVIDENCED`. Five copies of a rule that
  says one thing is how a rule table starts lying about its own size (67 rules, 12
  DOCTRINE).
- **The declaration is checked against the corpus.** A field declared required but missing
  from one shipped case would silently flip that case to `hold`; `TestInputContract` fails
  instead, so a contract and its cases cannot drift apart.
- **The property is tested over every case, not one probe per domain.**
  `TestInputContract.test_deleting_a_required_field_never_yields_go` deletes each required
  key from each of the 37 cases and asserts the answer is not `go`, and
  `benchmarks/absence_sweep.py` states the same invariant as a standalone check anyone
  can run: *no required field can be deleted into a green light*.

The second fix came from asking the obvious follow-up: if a missing key is not a
permission, what is a key whose value is `null`? Or `""`, `[]`, `{}`, or `0` in a boolean
slot? Sixteen combinations across the same 37 cases still returned `go`, because the guard
said `k not in ctx` — a check about the JSON file, not about the record. The contract now
declares a *type* per key (`REQUIRED_FIELDS = {"pccp_authorized": bool, ...}`) and
`is_unusable()` rejects absent, blank and wrongly-typed values alike. The invariant widened
to match: **no required input can be deleted or blanked into a green light**, which is what
`absence_sweep.py` and `TestInputContract` now assert over every case and five spellings.

What is **not** claimed: that `hold` is correct for every incomplete record. A missing
field that merely removes a *fact the case asserted* — no death claimed, no recall class
claimed — legitimately returns `go`, because the record no longer asserts the hazard.
The invariant is narrower and it is the one we can defend: an input the judge cannot work
without may never be read as an input nobody objected to.

### 1.10 The other forty-two fields

`absence_sweep.py` proves something about the fields we chose to require. The obvious
reviewer question is what happens to the rest — and "we thought about it" is not an answer.

So every field any rule reads is classified, in a generated table
([`absence_taxonomy.json`](absence_taxonomy.json), 58 fields):

| kind | n | meaning |
|---|---|---|
| `required` | 18 | absent, blank or wrongly typed → `hold` (enforced, see §1.9) |
| `claim` | 26 | the case asserts something; removing the assertion may legitimately change the answer |
| `bookkeeping` | 11 | identifies the case or carries citations |
| `weak_evidence` | 3 | proof-shaped, but some shipped case omits it — cannot be required without silently flipping that case |

The last row is the residue, published rather than hidden, and its size is **capped in the
test suite** so it can shrink and not quietly grow. Each entry carries the reason it is
still weak.

Two things this forced, both worth more than the table:

- **`evidence_sufficiency` was briefly required in postmarket, where no rule reads it.**
  A field can be in every shipped case and still be a field the judgement never consults;
  requiring it would be a contract about the corpus rather than about the decision. The
  suite now reads the judge source directly and fails if a required field is never read.
- **The strong reading of "evidence" turns out to be expensive.** `predicate_unchanged`,
  `verification_documented`, `technical_docs_updated`, `acceptance_criteria_met` and
  `evidence_sufficiency` are evidence-shaped *and* universal, so they moved from
  "unclassified" to required — that is where the 42 green results came from. The five
  PCCP/NMPA fields that stayed weak are weak only because a shipped case omits them: the
  way to close them is to make the corpus universal, not to relax the guard.

- **Putting the guard first cost us a veto.** With the contract checked before the
  rules, a record that was missing a required field *and* violated a critical rule
  returned `hold` -- the veto reason disappeared with it. `demo1`'s
  `INV veto-not-softened` caught it, so the critical rules now run first: an
  incomplete record may make a verdict more cautious, never more lenient.
  `TestVetoPrecedence` evaluates each critical predicate directly and requires a
  firing rule to surface as `reject`, on shipped and deliberately broken records alike.

#### 1.10.1 The residue is a fact, not a mood

The first version of the table capped `weak_evidence` at 5 and gave each entry a
reason. Two of those five turned out to be wrong, and the way they were wrong is
worth keeping:

- **NMPA `safety_effectiveness_assessed` was called weak while all nine shipped
  NMPA cases supply it.** It was never weak; it was simply not required yet.
  Requiring it changed no verdict.
- **PCCP `remains_se_to_predicate` was weak only because five cases predated the
  field.** They now carry it (`true` where equivalence held, `false` on the
  intended-use change), so it is required and no verdict moved.

Each entry now carries `absent_in`, **computed by scanning the corpus** rather than
written by hand, and the suite checks both directions: a `required` field must be
omitted by no shipped case, and a `weak_evidence` field must be omitted by at least
one. "Weak" can no longer quietly mean "unenforced".

What is left — three PCCP fields — is weak for a specific reason: one case
(`pccp08_red_team_absent_special_controls.json`) exists to test their absence.
Requiring them would replace a specific rule with a generic one, which is a worse
trade than a published residue of three.

### 1.11 How much better, counted

Every safety tool says "more reliable". A delta is a claim until it can be recomputed,
so the comparison is generated: [`Baseline_Scorecard.md`](Baseline_Scorecard.md).

Four shortcuts are scored on the same two corpora -- the 37 cases with declared
expectations, and 846 records made by deleting or blanking a contract field:

| engine | shipped agreement | false greens |
|---|---|---|
| **gate** | **37/37** | **0/846** |
| always-go | 7/37 | 702/846 |
| keyword grep | 11/37 | 612/846 |
| presence checklist + keyword | 11/37 | 510/846 |
| single severity rule | 9/37 | 648/846 |

The second column is the honest one. On the shipped corpus a keyword shortcut is
already close, because the cases were written to be legible. The separation appears
only where the record is still well-formed JSON and the shortcut cannot tell *absent*
from *not objected* -- which is exactly the failure this table exists to name.

The baselines are stand-ins for the shortcuts a hurried integration converges on,
not products, and no vendor's behaviour is claimed. A fifth shortcut, or a real
tool, is one dictionary entry away and is scored by the same command.

### 1.12 The same fact, written differently

Deleting a field was attack one. Every field present, only the spelling changed,
is attack two -- and it is the one a real integration hits first, because a
downstream system that writes `CLASS1` instead of `class1` has not lied about
anything.

`benchmarks/representation_sweep.py` re-runs each of the 37 cases with every
scalar rewritten, 1725 variants, and holds two promises:

| family | variants | promised outcome | measured |
|---|---|---|---|
| lexical (case, padding, spacing) | ~1400 | identical verdict | **0 flips** |
| boolean written as string / int | ~330 | same or *more cautious*, never `go`, never `reject` | **0 go · 0 reject · 137 hold** |

Both promises failed before this section existed: 9 variants turned a `reject`
or `hold` into `go`, and 6 turned a `go` into `reject`. The causes were two, both
old bugs wearing new clothes: rules compared exact tokens, so casing decided
semantics; and a boolean written `"true"` is a type error that reads as truthy
to a plain `if`, so a *typo* could manufacture a veto.

The fixes are one boundary and one declaration. Strings are canonicalised once at
the engine entry (strip, collapse spacing, casefold) -- no field dropped, no value
coerced, and a wrong type is still not repaired. Each judge now declares every
boolean it reads with `is True` / `is False`, and `misused()` puts those under the
same guard as the contract, so a mistyped flag yields `hold` rather than a verdict
built on a string. A test scans judge source for booleans that are read but not
declared, so the next field cannot be added without a decision.

### 1.13 Did the last fix flip somebody else's verdict?

Every measurement above looks at one version of the engine. None of them could
answer the question a maintainer is actually asked: this release changed how a
field is read -- which *other* verdicts moved?

`benchmarks/verdict_drift.py` runs two engines over the same 37 case files: a
pinned git ref, checked out into a throwaway worktree, and the working tree. The
result is published as `docs/methods/verdict_drift.json` and checked by the test
suite, not remembered:

| pinned ref | verdicts changed | what the row proves |
|---|---|---|
| `1bc5340` (#30) | **7** -- all `go -> hold`, every one a red-team case | the instrument can see a flip; a tool that reports zero for every ref would be broken, not clean |
| `28fe22b` (#44) | **0** of 37 | canonicalising spelling moved no shipped verdict |
| `58c0369` (#45) | **0** of 37 | the anchor for this generation |

The seven moves are the point of the row. At #30, cases whose own JSON declares
`hold` were still earning `go`; they are the probes that later became the
absence contract. Naming them one by one from a checkout, rather than from
memory, is the difference between "we fixed it" and "we can show what it used to
decide".

A fix that flips a case against a pinned row has to regenerate this table, which
puts the flip in the diff where a reviewer sees it. CI runs `--check` on every
push, so an undeclared flip fails the build instead of shipping quietly.

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

37 case files across 6 directories (`demo1/cases*`), each with a declared expected
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
python -m unittest discover -s tests -v          # 62 assertions
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
5. **Corpus size.** 34 cases is enough to pin behaviour, not enough to estimate
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
| **`MedXpert-org/lgd-engine`** | **0** | 5 regulatory judgment tables, 30 pinned cases, public CI |

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

本方法说明描述一种把"监管变更判定"从自然语言问答改写成可执行规则表的方法：输入是评审人实际持有的结构化字段，输出是三值判决（go / hold / reject）加上被触发的规则编号；判定纯粹、可离线重跑、失败时表现为"拒绝回答"而非"猜测"。已实现五张判定表（美国 510(k) 变更分类、上市后处置、FDA PCCP 范围、EU MDR 重大变更、中国 NMPA 变更注册），随包发布 34 个带预期判决的案件与 12 条对抗探针；同一批输入下，确定性判定器 12/12 命中预期，关键词捷径仅 5/12。

本说明明确划出边界：确定性策略求值、智能体前置拦截、监管决策树均非本文首创；本文的贡献限于"把可枚举的变更类别做成可复跑的规则表，并用案件语料钉住行为"。不宣称精度/召回率，不宣称可替代监管判断，不宣称具备身份与沙箱能力。截至本版本：79 条契约断言、5 张判定表、37 个案件、7 个 MCP 工具，全部由公共 CI 每次推送执行。
