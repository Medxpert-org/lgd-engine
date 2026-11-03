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
| **Automated gate** (`review/pre_release_review.py`) | 9 checks, exit 1 on anything that is not a pass, `--selftest` proves each check can fail | runs against a clean export of the committed tree, not the working copy |
| **Probe harness** (`review/redteam_probe.py`) | 20 probes over the real judges, MCP surface and CLI; `--selfcheck` proves each probe can fail | the probes run against mutants as well as the product, so a probe that measures nothing fails the run |
| **Independent red team** (separate agent seat, S7 round) | injection, tool-permission boundary, forged evidence, gate mutation, exit-code semantics, publish integrity | did not write the code under test; reported FAIL |
| **Outsider** (separate agent seat, no project context, S7 round) | copies the repo, reads only `README.md` + `llms.txt`, follows them literally | was told not to read source to guess usage |
| **External vantage** | an outside fetcher reads the public surfaces anonymously (no token) | different network path from this machine |

Two honesty notes about this round:

1. A fresh independent agent seat could **not** be dispatched for this run — the
   host's credit stop-flag was active. The S7 seat reports above stand, and the
   machine harness now covers the same claims mechanically, but "a new human-side
   seat reviewed commit `c8c430c`" is **NOT VERIFIED**. It is written here rather
   than implied.
2. Vantages matter: from this host, `github.com` and `zenodo.org` are reset at the
   connection level, `raw.githubusercontent.com` works most of the time, and on
   2026-11-04 the proxy in front of this machine returned `502` for a stretch.
   The gate therefore records `BLOCKED` — never `PASS` — for a host it cannot
   reach, and a control URL on the same host decides whether that is our
   repository or the network.

## 2. Automated checks

| Check | The claim it tests | Can it fail? |
|---|---|---|
| `links` | every cited URL resolves and contains its expected text | yes — bogus host, absent marker |
| `outsider` | the committed tree runs every documented command verbatim | yes — a broken gold test |
| `docs-claims` | numbers in the docs equal what the tree produces | yes — four checks claimed vs six run |
| `relative-links` | file paths named in the docs exist (declared non-files excepted) | yes — a path that is not there |
| `citation` | CITATION.cff complete, version-consistent, no silent placeholder, DOI only if it resolves | yes — missing title, fake DOI |
| `license` | LICENSE / pyproject / CITATION agree and NOTICE exists | yes — MIT in pyproject |
| `public` | the default branch is readable without a token | yes — a nonexistent repo |
| `machine` | llms.txt and JSON/YAML entry points exist and parse | yes — llms.txt removed |
| `redteam` | the judgment core survives the probes, and every probe can fail | yes — one sabotaged probe is reported VACUOUS |

`--selftest` runs all nine mutations and requires a failing finding from each:
`SELFTEST PASS` is the output, and the selftest is itself a check that can fail.

Latest machine output: `review/evidence/pre_release_latest.json` (the run's own
summary line is the single source for counts — nothing here restates them).

## 3. Red team — what it found, and what happened to it

A finding is only closed when a test fails without the fix. The S7 round's
author-side reproductions are in `demo1/test_demo1.py`; the 2026-11-04 round's are
in `review/redteam_probe.py`, with the pre-fix run kept verbatim in
`review/evidence/redteam_before.json` (9/19 probes passing).

### S7 round

| # | Finding | Reproduction | Status |
|---|---|---|---|
| R1 | **Fail-open**: an unclassified `change_type` returned `GO` with 0 reasons and an empty evidence package | `{"change_type":"xyz_unknown_change","source_refs":[{"kind":"","ref":""}]}` → `GATE VERDICT: GO` | **fixed** — `R-MAJ-06`; blank refs are not evidence. Invariants `unknown-change-type`, `blank-evidence`, `no-change-type` |
| R2 | **Verdict softening**: the judge reported `HOLD` while the aggregate said `REJECT` | `{"recall_class":"class1","change_type":"supplier_substitution","equivalence_declared":"yes"}` → `per_judge: HOLD` + `REJECT` | **fixed** — a major rule may escalate, never soften. Invariant `veto-not-softened` |
| R3 | **Tool failure disguised as a verdict**: a judge exception printed `REJECT` and exited `2` | `{"source_refs":["a-string"]}` → `judge raised` … `exit 2` | **fixed** — `errors` in the report, CLI exits **3**, usage **64** |
| R4 | **Gate could be turned green**: a stub `demo1/selftest.py` passed | drop-in stub → `RESULT: PASS` | **fixed** — one canonical test path, a shadow file is a failure |
| R5 | **"No plaintext keys" was narrower than its name** | `db_password=…` in a doc → gate green | **fixed** — patterns added, verified red |
| R6 | **Malformed YAML passed without PyYAML** | `version: [unclosed` → gate green | **fixed** — stdlib fallback refuses unbalanced flow collections |
| R7 | **`entry` as a list bypassed the traversal check** | `entry: ["../../etc/evil.py"]` → gate green | **fixed** — list entries checked, verified red |
| R8 | **Three release surfaces, three gate counts** | `grep "checks PASS"` across three files | **fixed** — one check reads all three |
| R9 | **Publish integrity**: "7-dimension review closed, no open high-severity findings" had no artifact in the tree | `grep -rn LGD-EVAL-2026-009` → comments and prose only | **fixed by removal** |
| R10 | README said a zero-evidence `go` is "rejected"; the code downgrades to `hold` | README §Contributing vs `L2-EVIDENCED` | **fixed** — prose matches law and code |
| R11 | CI did not run the suites the docs said were enforced | 4 steps in `gate.yml` | **fixed** — OpenAPI, injection/security and SSE smoke are CI steps |

### 2026-11-04 round — the probe harness

| # | Probe | Finding | Reproduction (before → after) | Status |
|---|---|---|---|---|
| R12 | `A1` | **Predicate inversion**: `function_config_change` with `predicate_unchanged=false` — the worse direction — scored better than `true` | `false → go` (no rule) vs `true → hold`; now `false → hold` via `R-MAJ-08` | **fixed** |
| R13 | `C2` | **Dead "evidenced" law**: the postmarket `L2-EVIDENCED` branch was unreachable — the line above it already turned a zero-evidence `go` into `hold`, so the law never fired and never appeared in the reason chain | `verdict=hold rules=[]`; now `hold` + `L2-EVIDENCED` | **fixed** |
| R14 | `D1`,`D3`,`D4` | **MCP `role` was decorative**: read, logged, quoted in denials, never consulted — an undeclared role was indistinguishable from a declared one. The documented `{ctx: {...}}` wrapper was ignored, so a contract-following client judged an empty context; non-object `arguments` were judged instead of rejected | `role=auditor → result`; `{ctx:…}` ≠ flat; `arguments=5 → result`; now `error -32003` / equal reports / `error -32602` | **fixed** |
| R15 | `F1`,`F2` | **Contract drifted from code**: `change_type` enum lacked `supplier_substitution`; `source_refs` typed `array of string` while the judges require `{kind, ref}` objects — a contract-conforming client could never satisfy law 2. Also six `mvp/` paths that do not exist, an example naming a domain and rule that do not exist, and no `errors`/`jurisdiction`/`equivalence_declared` | `docs/validate_openapi.py` 20/20; probes F1/F2 | **fixed** |
| — | `A1`,`C3`,`C4`,`C5`,`E2` | **Additional holes found by the same harness**: inverted `evidence_sufficiency` axis (`none` → go while `needs_supplement` held); blank refs satisfied law 2 in the postmarket judge; unknown recall class / cause / severity / distribution rode out as `go`; a raising rule predicate was swallowed (`except: pass`); a Class 2 recall only held for `maintenance_execution`, so `design_defect` riding it exited `0` | see `review/evidence/redteam_before.json` | **fixed** as classes, not instances: every enumerated axis now holds on an unknown value in both judges |

### Withdrawn

The S7 report also listed "`--db` accepts an arbitrary path, so the CLI writes
wherever it is told". **Not reproducible on this tree**: neither `demo2/session.py`
nor any other entry point defines a `--db` flag (`argparse` declares `--case`,
`--auto`, `--parallel` only). `DecisionStore(db_path)` is a library constructor
that a host application calls with its own path — normal for a library, and not a
CLI surface. Recorded here as withdrawn rather than quietly deleted.

### Still open (not defects in the gate; they are release decisions)

1. `.zenodo.json` precedence: only `CITATION.cff` exists today, which is correct.
   Adding a `.zenodo.json` later silently overrides it — a trap, not a bug.
2. `lgd-gate --all` parity: the console entry has fewer flags than the demo CLI.

## 4. Outsider test — what a stranger hits

An independent agent copied the tree and followed only `README.md` and
`llms.txt`. It reported **18 documentation gaps** and could not finish the
journey without guessing. Fixed in this branch:

| Gap | Fix |
|---|---|
| `pip install "lgd-engine[yaml]"` 404s (not on PyPI) | README uses `pip install -e ".[yaml]"` and says the package is not published |
| The documented gate count disagreed across files | all release docs say 6/6, enforced by gate check 5 |
| No prerequisites section | added: Python 3.9+, git, optional PyYAML, Node/Docker only for those demos |
| SSE "self-hosts, asserts, exits" with no precondition | llms.txt states the two session commands that must run first |
| `demo1/test_ecosystem.py` produced a 6/6 nobody documented | documented in the README quickstart |
| Usage errors exited 2, indistinguishable from a real reject | usage exits 64, tool errors 3 |

Still open from that report, and labelled **NOT VERIFIED** rather than claimed:

- the **container** surface (`docker compose up`) is documented but was **not
  run** in this review — no Docker on this host, and no container step in CI. The
  three docs that claimed "verified Docker Desktop 4.89.0" now say so instead of
  claiming a run nobody recorded;
- the portal page does not mention this repository;
- `lgd-gate --all` is documented but absent from the console entry.

Verified during this round, after three docs had claimed it without evidence:
`cd lgd-engine-ts && npm run smoke` → `SMOKE OK: judge() POST+auth+GateReport
parse; decisions() limit query + parse`, exit 0, on Node 24.14.0 (the docs claim
Node 18+). The TypeScript surface is therefore PASS for this round, with the
Node version and the exact output recorded here.

## 5. External vantage

An outside fetcher read `https://github.com/Medxpert-org/lgd-engine`
anonymously: **public, Apache-2.0 visible** — and the page still served the
*main* branch, i.e. every fix on this branch is invisible to an outside reader
until the PR is merged. That is the largest remaining gap between "what we fixed"
and "what the world can see".

Anonymous read of `raw.githubusercontent.com/.../main/README.md` is gate check
`public`. On 2026-11-04 the proxy in front of this host returned `502` for part
of the run; the check recorded `BLOCKED` (with the control URL's failure as
evidence) rather than turning a network outage into a repository defect.

## 6. Verdict

**Not releasable yet — and this time the reason is not the code.**

The machine verdict is whatever `review/evidence/pre_release_latest.json` says on
the commit you are reading; the verdict *here* is a judgement about the world,
and it is **BLOCKED** for three reasons that no patch can close:

1. **The fixes are on a branch.** Until the PR is merged, `main` still shows the
   old counts and the unbacked review claim. An outside reader sees the branch we
   have not shipped.
2. **No DOI, no tag, no release.** `CITATION.cff` correctly carries no DOI until
   Zenodo mints one; minting requires the account holder to enable the GitHub
   integration. Publishing a citation entry without an identifier would break the
   FORCE11 persistence principle.
3. **No CLA and no DCO.** A W3C Community Group contribution needs a signed CLA
   and a public record of the contribution; this repository has neither a CLA bot
   nor a `Signed-off-by` requirement.

Re-run before any release:

```bash
python review/redteam_probe.py --selfcheck           # 20 probes, each proven able to fail
python review/pre_release_review.py --json review/evidence/pre_release_latest.json
python review/pre_release_review.py --selftest       # proves all 9 checks can fail
python framework/gate_bot.py                         # 6 checks
python docs/validate_openapi.py                      # contract/code lockstep, 20/20
```
