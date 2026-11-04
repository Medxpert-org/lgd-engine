# TD proposal — executable assurance gates for post-market change control of AI-enabled medical software

**Contribution to:** ITU-T FG-TIDA (Focus Group on Trust and Identity for Humans and Agentic AI)
**Relates to ToR output:** 5) *security criteria and benchmarks for the ongoing assessment of AI agents*; and 3) *trust frameworks and lifecycle (assurance) models*
**Provided by:** an independent expert, in an individual capacity. No organisational affiliation is claimed or implied.
**Status:** draft for discussion. Not a standard, not a published specification.

---

## 1. What this contribution asks for, in one paragraph

Software that uses machine learning changes after it has been approved: retrained
weights, swapped suppliers, quietly altered decision thresholds. What is missing
is not another checklist. What is missing is a convention that makes an assurance
verdict *executable and falsifiable* — so that two parties looking at the same
evidence reach the same verdict, and so that "we found no evidence" can never be
mistaken for "the evidence is sufficient". This contribution proposes four
clauses and shows a working reference implementation that a reviewer can run
offline in under a minute.

## 2. The problem, stated precisely

Current assurance artefacts are prose plus vendor declarations. Three failure
modes follow, and each is observable in practice:

1. **Unspecified defaults.** When a submitted case leaves a required field
   unknown, most review procedures say nothing about what must happen. In
   practice the unknown silently reads as "no objection", and the verdict comes
   out affirmative.
2. **Evidence sufficiency is not representable.** A verdict of "acceptable" does
   not distinguish *sufficient evidence* from *no evidence examined*. Two
   assessments with opposite evidentiary bases are therefore indistinguishable in
   the record.
3. **The checker itself is untested.** A conformance check that has never been
   observed to fail is indistinguishable from a check that cannot fail. Review
   procedures rarely require the check to demonstrate that it rejects anything.

None of the three requires new science to fix. All three require a convention.

## 3. Proposed text (drafting language)

> **C1 — Determinism.** A conformance verdict SHALL be a function of the submitted
> evidence set alone. Given the same evidence, the verdict SHALL NOT depend on
> the order of rules evaluated, the presence of the assessor, or the interface
> used to submit it.

> **C2 — Fail-closed on the unknown.** Where a required field admits an
> enumerated set of values, a value outside that set SHALL NOT produce an
> affirmative verdict. The implementation SHALL treat an unknown value as a
> finding, not as an absence of a finding.

> **C3 — Evidence sufficiency as a first-class output.** Every verdict SHALL
> carry the identifiers of the rules that produced it. A verdict produced with no
> rule fired SHALL be reported as *insufficient evidence*, and SHALL NOT be
> representable as an approval.

> **C4 — Falsifiable checkers.** Each criterion SHALL be accompanied by an
> executable check whose process exit status encodes the verdict (0 = affirmative,
> 1 = withhold, 2 = negative, distinct from tool error). The check SHALL be
> supplied with at least one deliberately corrupted input on which it is required
> to return non-affirmative; a check that passes its own corrupted input SHALL be
> reported as vacuous and SHALL fail the assessment.

The exit-status convention in C4 matters because it makes the verdict legible to
a machine without parsing prose, and because it separates *the assessor could not
run* (a tool error) from *the answer is no* (a verdict). Conflating those two is
the most common way an automated gate reports success while checking nothing.

## 4. Executability evidence

The reference implementation is a small offline program with no runtime
dependencies. These commands and their exit statuses were observed on the
artefact named in §7; the numbers are reproducible, not asserted.

| Command | Observed | Meaning |
|---|---|---|
| `python -m lgd_engine.cli --case demo1/cases/case01_red_pma_process.json` | exit `2` | negative verdict — the exit status *is* the verdict |
| `python -m lgd_engine.cli --case demo1/cases/case05_green_label.json` | exit `0` | affirmative, with the firing rules listed in the reason chain (C3) |
| `python -m lgd_engine.cli --case contributions/itu-fg-tida/examples/unknown-enum.json` | exit `1`, rule `R-MAJ-06-unknown-evidence_sufficiency` | an enumerated field carried a value outside the known set; the judge withheld instead of reading the unknown as "no objection" (C2) |
| `python -m lgd_engine.cli --all demo1/cases` | exit `0`, `[summary] 5/5 cases match expected verdict` | every case reproduces its documented verdict |
| `python review/redteam_probe.py --selfcheck` | exit `0`, `22/22 probes PASS`, `SELFCHECK PASS` | 22 property probes; each is re-run against a deliberately broken implementation and must fail there (C4) |
| `python review/pre_release_review.py --selftest` | exit `0`, `SELFTEST PASS` | 19 mutants, each required to make its check fail (C4) |

Two properties of the harness are worth naming, because they are the parts a
reviewer can verify cheaply:

- **A probe that survives its own mutant is reported as vacuous and fails the
  run.** The harness therefore cannot be satisfied by a check that asserts
  nothing.
- **A host that cannot be reached is recorded as *blocked*, never as *passed*.**
  Network vantage is treated as evidence, not as an excuse.

## 5. Impact

- **On assessors:** a verdict becomes re-runnable by a third party. The cost of a
  second opinion drops from "read the report" to "run the check".
- **On suppliers:** the evidence package must name the rules that fired. This is
  more work once, and less argument afterwards.
- **On the Focus Group:** the four clauses are vocabulary-neutral. They constrain
  the *form* of an assurance verdict, not the risk model behind it, so they can
  be adopted alongside any of the reference architectures under discussion.

## 6. Boundary — what this contribution does not claim

- It does **not** propose a risk taxonomy, nor a threshold for what counts as
  acceptable risk. Those are domain questions and belong to regulators.
- It does **not** claim clinical or regulatory validity for any particular rule
  set. It constrains how a verdict is produced and reported.
- It does **not** assert organisational standing of any kind. The implementation
  is offered as an individual-capacity artefact for the group to use, fork or
  discard.
- The reference implementation covers a narrow domain (change control for
  AI-enabled medical software). Generality beyond that domain is a hypothesis,
  not a result.

## 7. Provenance

Reference implementation and its evidence files: `https://github.com/Medxpert-org/lgd-engine`
(see `review/evidence/` for the raw runs quoted in §4).
