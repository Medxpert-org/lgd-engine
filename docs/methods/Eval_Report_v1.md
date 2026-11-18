# Independent Evaluation Report — Method Note v1.0 → v1.1

**Evaluator:** independent pass (separate run, no author context carried into the checks;
the harness is committed so a third party can repeat it — independence comes from the
script, not from the credential of whoever ran it)
**Subject:** `docs/methods/Method_Note_v1.md` v1.0 and the repository it describes
**Date:** 2026-11-18
**Base commit:** `198bbf7` (v1.0) → evaluated on `8765b93` after fixes
**Verdict:** **CONDITIONAL PASS at v1.0 → PASS at v1.1** (five findings, all closed)

> **Snapshot note.** This report is a record of the state at `8765b93` (38 assertions,
> 24 cases, 5/5 NMPA). After it was written, the NMPA table was re-checked against the
> statute text and three deviations were fixed (see `Legal_Check_20261118.md`), moving
> the counts to **40 assertions, 26 cases, 7/7 NMPA**. The findings and verdicts below
> stand; the counts are the counts of that day, not of today.

---

## 1. What was tested, and how

The evaluation deliberately did not read the author's reasoning. It took only two
artefacts: the note itself, and the public repository. It then behaved like a
stranger with a deadline:

1. **Clean clone at an unfamiliar path.** `git clone --branch ci/contract-tests-20261118`
   into a temporary directory, so no untracked or uncommitted author state could
   help the commands pass.
2. **Verbatim execution.** Every command written in §1 and §5 of the note was run
   exactly as printed — no corrections, no substitutions.
3. **Adversarial additions** beyond the note's own table:
   - tamper the generated page and confirm `--check` actually fails (does the
     anti-drift guard exist, or is it a claim?);
   - check declared exit codes for `reject` / `go` / usage error separately;
   - scan for third-party imports and confirm `dependencies = []`;
   - confirm the tree is still clean after the entire run (did the checks themselves
     write anything?).
4. **Document-versus-repository cross-check.** Counts claimed in prose (38 assertions,
   24 cases, 5 tables, 12 probes) were compared against files on disk.

Reproduction of this evaluation: the script used is reproduced in Appendix A.

---

## 2. Results — every claim the note makes

| Claim (note §) | Check performed | Result |
|---|---|---|
| C1 five tables run offline | `--all demo1/cases_nmpa --domain nmpa` | **PASS** (5/5) |
| C2 byte-identical reruns | same MDR case run twice, diffed | **PASS** (zero diff) |
| C3 critical forces reject | `TestThreeLaws.test_l3_critical_forces_reject` | **PASS** |
| C4 go without evidence → hold | `TestThreeLaws.test_l2_go_without_evidence_is_hold` | **PASS** |
| C5 crashing judge ≠ veto | `TestThreeLaws.test_crashing_judge_is_reject_and_flagged` | **PASS** |
| C6 exit codes 2 / 0 / 64 | three separate CLI invocations | **PASS** (2 / 0 / 64) |
| C7 MCP smoke, 7 tools, RBAC | `python lgd_engine/mcp_smoke.py` | **PASS** (`SMOKE: PASS`) |
| C8 baseline 12/12 vs 5/12 | `python benchmarks/adversarial_baseline.py` | **PASS** |
| C9 page cannot drift | `build_demo_page.py --check` | **PASS** |
| X1 drift guard is real | page tampered, `--check` re-run | **PASS** (guard failed as designed) |
| X2 assertion count | `unittest discover` | **PASS** (`Ran 38 tests`) |
| X3 stdlib only | import scan + `pyproject.toml` | **PASS** |
| X4 corpus count | files on disk vs prose | **PASS** (24 = 24) |
| X5 no side effects | `git status` after whole run | **PASS** (clean) |

No claim in the note failed at the level of "the command does not do what the text
says." The findings below are about the *repository and the prose*, not about
whether the engine works.

---

## 3. Findings

### E1 — Major (defect, fixed): case-only duplicate filenames dirtied every clone

`.github/PULL_REQUEST_TEMPLATE.md` (414 B) and `.github/pull_request_template.md`
(2,093 B) were both tracked. On case-insensitive filesystems only one can exist on
disk, so a fresh clone at the evaluation path reported `M .github/PULL_REQUEST_TEMPLATE.md`
before anything was touched.

**Why this matters beyond cosmetics:** a stranger's first interaction with the
repository is a dirty working tree. That reads as "someone was editing here," which
undermines the exact claim the project is making. Automated checks still passed,
which is how this survived — but the first impression did not.

**Fix (`8765b93`):** the 414-byte Chinese gate checklist was folded into the retained
English template; the duplicate index entry was removed. Verified afterwards: clone
reports `dirty=0`.

### E2 — Moderate (doc defect, fixed): four table rows described checks instead of commands

C2 read "run any case twice, diff the output"; C4/C5 read "same suite, …". A reader
cannot execute a description. All four rows now name the exact test id, e.g.
`python -m unittest tests.test_contract.TestThreeLaws.test_l3_critical_forces_reject -v`.

**Why this matters:** the note's value proposition is "every claim is paired with the
command that checks it." A row that cannot be pasted into a terminal weakens the
proposition for exactly the reader it targets.

### E3 — Substantive (disclosure added): expected verdicts are not independent of the rules

The 24 case files and their expected verdicts were authored by the same party that
wrote the tables. Corpus agreement therefore demonstrates *consistency*, not
*correctness*: it pins behaviour against regression, but it cannot show the rules
match regulatory practice. The note previously implied more than that by presenting
"5/5 cases match expected verdict" as the headline evidence.

**Fix:** §6 gained item 7, stating the circularity explicitly and naming what would
be stronger (cases authored independently from the regulations alone — not done).

**Why this matters:** this is the finding most likely to be raised by an external
reviewer, and the one that would do the most damage if discovered rather than
disclosed.

### E4 — Minor (doc inconsistency, fixed): Python version

Prose said 3.10+; `pyproject.toml` declares `requires-python = ">=3.9"`. Now stated
once, sourced from the manifest.

### E5 — Minor (doc gap, fixed): probe file not named

The 12 adversarial probes existed only as a number in prose. §4.2 now points to
`benchmarks/adversarial_baseline.py` and invites falsification.

---

## 4. What this evaluation did **not** establish

- **No accuracy estimate.** 24 cases cannot yield precision/recall, and none is
claimed. The evaluation checked whether claims are *checkable and true as stated*, not
whether the tables are *right about regulation*.
- **No regulatory correctness review.** Validating rule text against primary sources
  (FD&C §515C, MDCG 2020-3 rev.1, Order 47) against a lawyer's or notified body's
  reading was out of scope. The rules cite their basis; the citations were not
  independently legal-reviewed.
- **No cross-platform matrix.** Executed on Windows (PowerShell) in a case-insensitive
  filesystem — which is *why* E1 surfaced. Linux/macOS runs are inferred to work from
  CI but were not run here.
- **No performance or scale testing.** Out of scope for a method note.

---

## 5. Verdict and conditions

**PASS at v1.1**, on the specific claim set: *the enumerated judgment tables are
reproducible offline, their reasons are inspectable, and their failure mode is refusal
rather than a guess.*

Conditions attached to any public deposit of this note:

1. Keep §6 complete, including the circularity disclosure added here. Removing it
   would convert a disclosed limitation into a misrepresentation.
2. Cite the commit hash alongside the note; the claims were verified against `8765b93`
   and will not hold for arbitrary future states.
3. If the note is extended to new jurisdictions, the §1 table must be extended first
   — an unchecked claim should not enter the document ahead of its command.

---

## Appendix A — evaluation script

The run is reproducible from the repository; the script performs, in order: clean
clone → C1–C9 verbatim → page tamper test → assertion count → dependency scan →
corpus count → post-run cleanliness. Its outputs are recorded in
`docs/methods/Eval_Transcript_20261118.txt`.
