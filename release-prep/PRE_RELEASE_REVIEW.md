# Pre-release review — what an outside reader must be able to do

This file is the release gate for a public contribution. It exists because the
requirements we are judged on are not ours to define:

- **ITU-T** takes a contribution as material that may be redistributed without
  restriction (A.1 §3.1.6), wants the study-group template, needs it 12 calendar
  days before a meeting (§3.1.8), and requires a software copyright and
  licensing declaration when software is contributed (§3.1.7).
  <https://www.itu.int/en/ITU-T/wtsa12/Documents/resolutions/ITU-T%20A.1.pdf>
- **Common Patent Policy ITU-T/ITU-R/ISO/IEC** — early disclosure, statement and
  licensing declaration form. <https://www.itu.int/en/ITU-T/ipr/Pages/policy.aspx>
- **W3C Community Groups** — open to all, but joining means signing the CLA, and
  most groups take contributions as GitHub pull requests with a public record.
  <https://www.w3.org/community/faq> · <https://www.w3.org/community/about>
- **Zenodo** — if both `.zenodo.json` and `CITATION.cff` exist, `.zenodo.json`
  wins and CITATION.cff is ignored for the release archive.
  <https://help.zenodo.org/docs/github/describe-software/zenodo-json>
- **FORCE11 Software Citation Principles** — importance, credit and attribution,
  unique identification, persistence, accessibility, specificity.
  <https://force11.org/info/software-citation-principles-published-2016/> ·
  <https://doi.org/10.7717/peerj-cs.86>
- **FAIR4RS** — the same idea applied to research software.
  <https://doi.org/10.15497/RDA00068>

Translated into one sentence: an outside reader must be able to **reach** the
material, **run** it, and **verify** the claim themselves. Everything below is
either that, or it is not in the review.

All links above were fetched, not remembered; `review/pre_release_review.py`
re-fetches them on every run and requires an expected text marker in the body,
so a soft-404 or a login wall cannot pass as a live link.

---

## 1. How the review runs

| Seat | What it does | Independence |
|---|---|---|
| **Automated gate** (`review/pre_release_review.py`) | 8 checks, exit 1 on any failure, `--selftest` proves each check can fail | runs from a clean export of the committed tree |
| **Red team** (independent agent) | jailbreak/injection, tool-permission boundary, forged evidence, gate mutation, exit-code semantics, publish integrity | did not write the code under test; reported FAIL |
| **Outsider** (independent agent, no project context) | copies the repo, reads only `README.md` + `llms.txt`, follows them literally | was told not to read source to guess usage |
| **External vantage** | an outside fetcher reads the public surfaces anonymously (no token) | different network path from this machine |

Vantages matter: from this host, `github.com` and `zenodo.org` are reset at the
connection level, while `raw.githubusercontent.com` and the GitHub API work.
A single-vantage checker would have reported false failures (or false passes).
The gate therefore records `BLOCKED` — never `PASS` — for a host it cannot
reach, and the review uses an external vantage for those.

## 2. Automated checks

| Check | The claim it tests | Can it fail? |
|---|---|---|
| `links` | every cited URL resolves and contains its expected text | yes — bogus host, absent marker |
| `outsider` | the committed tree runs every documented command verbatim | yes — a broken gold test |
| `docs-claims` | numbers in the docs equal what the tree produces | yes — 12 stages vs 11 rows |
| `relative-links` | file paths named in the docs exist (declared non-files excepted) | yes — a path that is not there |
| `citation` | CITATION.cff complete, version-consistent, no silent placeholder, DOI only if it resolves | yes — missing title, fake DOI |
| `license` | LICENSE / pyproject / CITATION agree and NOTICE exists | yes — MIT in pyproject |
| `public` | the default branch is readable without a token | yes — a nonexistent repo |
| `machine` | llms.txt and JSON/YAML entry points exist and parse | yes — llms.txt removed |

Latest machine output: `review/evidence/pre_release_latest.json`.

## 3. Red team — verdict FAIL, and what came of it

The red team was told to distrust the author's "all green" claim. It found real
defects. **These are reproduced by the author, fixed, and pinned by regression
tests** — a finding is only closed when a test fails without the fix.

| # | Finding | Reproduction | Status |
|---|---|---|---|
| R1 | **Fail-open**: an unclassified `change_type` returned `GO` with 0 reasons and an empty evidence package — violating the project's own law 2 | `{"change_type":"xyz_unknown_change", "source_refs":[{"kind":"","ref":""}]}` → `GATE VERDICT: GO`, `(0 reasons, 1 evidence)`, evidence rendered as `()` | **fixed** — unknown/missing change type is a `hold` with `R-MAJ-06`, blank refs are not evidence. Invariants `unknown-change-type`, `blank-evidence`, `no-change-type` |
| R2 | **Verdict softening**: the judge reported `HOLD` while the aggregate said `REJECT` (a critical veto overwritten by a major rule) | `{"recall_class":"class1","change_type":"supplier_substitution","equivalence_declared":"yes"}` → `per_judge: HOLD` + `GATE VERDICT: REJECT` | **fixed** — a major rule can escalate but never soften a veto. Invariant `veto-not-softened` |
| R3 | **Tool failure disguised as a verdict**: a judge exception printed `REJECT` and exited `2`, exactly like a real veto | `{"source_refs":["a-string"]}` → `judge raised: AttributeError` … `exit code 2` | **fixed** — the report carries `errors`, the CLI exits **3**, usage errors exit **64**; a real REJECT still exits 2 |
| R4 | **Gate could be turned green**: a stub `demo1/selftest.py`, or a `sys.exit(0)` test, passed | drop-in stub → `RESULT: PASS` | **fixed** — one canonical test path, a shadow file is a failure, and the summary must report `N/N cases; N/N invariants` |
| R5 | **"No plaintext keys" was narrower than its name**: AWS secret keys, `db_password=…`, JWTs passed | `db_password=…` in a doc → gate green | **fixed** — patterns added; verified red |
| R6 | **Malformed YAML passed without PyYAML** (which is the CI-realistic path) | `version: [unclosed` → gate green | **fixed** — stdlib fallback refuses unbalanced flow collections; a malformed file now produces a clean `[FAIL]`, not a traceback |
| R7 | **`entry` as a list bypassed the traversal check** | `entry: ["../../etc/evil.py"]` → gate green | **fixed** — list entries are checked; verified red |
| R8 | **Three release surfaces, three gate counts**: README said 5/5, `llms.txt` and `release-prep/README.md` said 4/4, the gate ran 5 | `grep "checks PASS"` across the three files | **fixed** — one check now reads all three; all say 6/6 |
| R9 | **Publish integrity**: "7-dimension security review closed with no open high-severity findings (LGD-EVAL-2026-009)" had no artifact anywhere in the tree | `grep -rn LGD-EVAL-2026-009` → comments and prose only | **fixed by removal** — the claim is gone from README, llms.txt and release-prep/README.md, replaced by a pointer to this file |
| R10 | README said a zero-evidence `go` is "rejected by the gate"; the implementation downgrades it to `hold` | README §Contributing vs `L2-EVIDENCED` | **fixed** — the prose now matches the law and the code |
| R11 | CI did not run the suites the docs said were "enforced in CI" | `.github/workflows/gate.yml` had 4 steps | **fixed** — OpenAPI, injection/security self-tests and the SSE smoke are now CI steps; `demo2` moved into `gate_bot` |

### Still open (reported by the red team, not fixed here)

These are behavioural and need a decision, not a patch — they are release
blockers, not typos:

1. **Predicate inversion** — `function_config_change` with
   `predicate_unchanged=false` (the more dangerous case) can score better than
   `true`. The rule table needs a review, not a line edit.
2. **`postmarket` L2-EVIDENCED is dead code** — the branch is unreachable, so
   that domain's "evidenced" law is decorative.
3. **MCP `role` is ignored** — any role value reaches the same tool set; the
   audit line ("read-only role cannot call this tool") misleads.
4. **`--db` accepts an arbitrary path**, so the CLI writes wherever it is told.
5. **`docs/openapi.yaml` `change_type` enum lacks `supplier_substitution`**,
   while the judge has rules for it: a contract-valid input can crash the judge.
6. **`.zenodo.json` precedence** — today only `CITATION.cff` exists, which is
   correct; adding a `.zenodo.json` later silently overrides it.

## 4. Outsider test — what a stranger hits

An independent agent copied the tree and followed only `README.md` and
`llms.txt`. It reported **18 documentation gaps** and could not finish the
journey without guessing. Fixed in this branch:

| Gap | Fix |
|---|---|
| `pip install "lgd-engine[yaml]"` 404s (not on PyPI) | README now uses `pip install -e ".[yaml]"` and says the package is not published |
| The documented gate count disagreed across files | all three release docs now say 6/6, enforced by gate check 5 |
| `--all` "does not exist" on `lgd-gate` while the docs show it | exit codes separated (64 for usage); the `--all` gap on the console entry is **still open** |
| No prerequisites section | added: Python 3.9+, git, optional PyYAML, Node/Docker only for those demos |
| SSE "self-hosts, asserts, exits" with no precondition | llms.txt now states the two session commands that must run first |
| `demo1/test_ecosystem.py` produced a 6/6 nobody documented | documented in the README quickstart |

Still open from that report: the Docker/TypeScript claims (`npm run smoke`,
`docker compose up`) are documented but were **not run** in this review — no
Docker on this host — so they are labelled NOT VERIFIED rather than claimed;
and the portal page does not mention this repository.

## 5. External vantage

An outside fetcher read `https://github.com/Medxpert-org/lgd-engine`
anonymously. Result: **public, Apache-2.0 visible** — and the page still served
the *main* branch, i.e. `(four checks)`, `4/4`, the "ITU FG-TIDA / W3C" line and
"preprint placeholder". Everything fixed on this branch is invisible to an
outside reader until the branch is merged. That is the single largest gap
between "what we fixed" and "what the world can see".

Anonymous read of `raw.githubusercontent.com/.../main/README.md` → `HTTP 200`
(gate check `public`), so the public-surface check is not taken on trust.

## 6. Verdict

**BLOCKED — not releasable.** Machine checks are green and the red-team P0s are
fixed and pinned, but four things still stand between this tree and a public
contribution:

1. Six behavioural findings in §3 are open (predicate inversion and the
   dead-code "evidenced" law are the serious ones).
2. The fixes are on a branch: the public surface still shows the old claims
   until the PR is merged.
3. No DOI, no tag, no release — and `CITATION.cff` correctly carries no DOI
   until Zenodo mints one. Publishing a citation entry without an identifier
   would break the FORCE11 persistence principle.
4. A W3C Community Group contribution needs a signed CLA and a public record of
   the contribution; this repository has neither a CLA bot nor a DCO line.

Re-run before any release:

```bash
python review/pre_release_review.py --json review/evidence/pre_release_latest.json
python review/pre_release_review.py --selftest     # proves the checks can fail
python framework/gate_bot.py                       # 6 checks
```
