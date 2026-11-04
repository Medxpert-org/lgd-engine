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
| **Automated gate** (`review/pre_release_review.py`) | 12 checks, exit 1 on anything that is not a pass, `--selftest` proves each check can fail | runs against a clean export of the committed tree, not the working copy |
| **Probe harness** (`review/redteam_probe.py`) | 22 probes over the real judges, MCP surface and CLI; `--selfcheck` proves each probe can fail | the probes run against mutants as well as the product, so a probe that measures nothing fails the run |
| **Independent red team** (separate agent seat, S7 round) | injection, tool-permission boundary, forged evidence, gate mutation, exit-code semantics, publish integrity | did not write the code under test; reported FAIL |
| **Outsider** (separate agent seat, no project context, S7 round) | copies the repo, reads only `README.md` + `llms.txt`, follows them literally | was told not to read source to guess usage |
| **External vantage** | an outside fetcher reads the public surfaces anonymously (no token) | different network path from this machine |

Two honesty notes about this round:

1. A fresh **engineering** agent seat could **not** be dispatched for this run —
   the host's credit stop-flag was active. The S7 seat reports above stand, and the
   machine harness covers the same claims mechanically, but "a new human-side
   engineering seat reviewed commit `c8c430c`" is **NOT VERIFIED**. It is written
   here rather than implied. What did run: the **S7 compliance seat** (the legal and
   process gate, `release-prep/STANDARDS_CONTRIBUTION_READINESS.md`) — and because
   that seat is not the author of the code, its verdict on the legal artifacts is
   separated from the author's own claims.
2. Red line 1 of the team charter ("the verifier must not be the author") is **not
   satisfied by the probe harness**: it was written by the implementer. The harness
   buys falsifiability (every probe is proven able to fail against a mutant), not
   institutional independence. Anything called "independent" in this file means
   *role separation*, never a third party.
3. Vantages matter: from this host, `github.com` and `zenodo.org` are reset at the
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
| `parity` | the tree an outsider can fetch is the tree this review examined: `parity-pushed` (the reviewed commit is on its upstream) and `parity-sha` (the default branch carries it) — and the documented commands run on *that* tree | yes — a commit that is not HEAD, and a commit that never reached its upstream |
| `relative-links` | file paths named in the docs exist (declared non-files excepted) | yes — a path that is not there |
| `citation` | CITATION.cff complete, version-consistent, no silent placeholder, DOI only if it resolves | yes — missing title, fake DOI |
| `license` | LICENSE / pyproject / CITATION agree and NOTICE exists | yes — MIT in pyproject |
| `legal` | the legal artifacts a standards contribution rests on carry substance: §3 patent grant, a NOTICE that names a holder, an inbound (not just outbound) contribution licence, and a readiness note whose negative claims declare their retrieval scope | yes — strip §3 from a copy of LICENSE |
| `public` | the default branch is readable without a token | yes — a nonexistent repo |
| `machine` | llms.txt and JSON/YAML entry points exist and parse | yes — llms.txt removed |
| `redteam` | the judgment core survives the probes, and every probe can fail | yes — one sabotaged probe is reported VACUOUS |
| `identity` | the public wording claims nothing about standing we cannot support: no reverse assertion about entity status, no self-claim to be a standard, a copyright holder that reads as a person, a participation docket that states the identity and names the channels that require a legal entity, and no brand-as-business reference in public docs | yes — five mutants, one per wording |

`--selftest` runs all nineteen mutations and requires a failing finding from each:
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

### Correction — a finding I withdrew for the wrong reason

The S7 report listed "`--db` accepts an arbitrary path, so the CLI writes wherever
it is told". I withdrew it after checking `demo2/session.py`, which declares only
`--case`, `--auto` and `--parallel`, and concluding that no entry point had the
flag. **That conclusion was wrong**: `demo1/change_gate.py` line 116 declares
`--db` and hands it to `LocalMemory`, which `makedirs` the parent and opens SQLite
there. The search was too narrow and the negative claim was stated as if it were
global — anti-pattern 45, committed by the review that quotes anti-pattern 45.

Reinstated and fixed as **R18**, with probe `E3`:

| # | Probe | Finding | Was | Now |
|---|---|---|---|---|
| R18 | `E3` | `--db` took any path: created parent directories anywhere, and on an existing non-database file died with a sqlite traceback instead of a usage error | `--db notes.txt` → traceback, exit 1 | empty value or non-SQLite target → **exit 64** with a sentence, and the resolved path is always printed (`[memory] decisions recorded in …`) |

The same sweep found the sibling item on the open list: **R19**, `lgd-gate --all`
was documented but only implemented on the demo CLI. It is now implemented on the
console entry (`--all CASES_DIR`, summary line, `64` on usage error), pinned by
probe `E4`.

| # | Finding | Was | Now |
|---|---|---|---|
| R20 | **`parity` answered two different questions with one verdict.** "Nobody can fetch what we reviewed" and "the review is not merged yet" are different failures with different owners — a stranger cannot *see* the work vs. a stranger sees an older tree. Reporting one number let the first hide inside the second | `origin/main behind HEAD` — one failing finding, no way to tell `ahead 7` (unpushed) from `behind 17` (unmerged) | split into `parity-pushed` (is the reviewed commit on its upstream?) and `parity-sha` (does the default branch carry it?). On `87cf070`: pushed **PASS**, sha **FAIL**. Mutant `parity/unpushed` builds a repo whose only commit never reached `origin/main` and requires the *fail* wording — a `blocked` finding does not count as detection |
| R21 | **The self-test was slow enough to be skipped**, which is the same as absent. `--selftest` spent the release path's `4 × 30 s` retry budget proving that a deliberately dead URL is dead: 3 m 22 s, killed by its own wrapper twice during this session | `--selftest` → >3 m, no output for the first 2 m (network retries on `example.invalid`) | `--selftest` lowers `RETRIES`/`TIMEOUT` to `1`/`8 s` for its own mutants only, with the reason in a comment: the self-test asks "does this check detect a defect?", not "does it tolerate a flaky upstream?". **49 s**, same mutants, same verdict |
| R22 | **A stale count nobody re-counted.** `CHANGELOG.md` said "20 adversarial probes" for two commits after the harness reached 22 — the only place the docs-claims check did not look. `gate_bot` check 5 re-counts the README's stage/domain counts; nothing re-counted the probe count | `grep "probes" CHANGELOG.md` → `20`; harness registers 22 | `docs-claims` now re-counts every "N probes" claim in `README.md`, `llms.txt` and `CHANGELOG.md` against the `@probe` registrations; mutant `docs-claims/probe-count` edits the CHANGELOG to `999` and requires a failure. The check is literal by design — it cannot tell a claim from a quotation — so history is written out in words |
| R23 | **Internal business reasoning in a public tree.** `framework/adapter-roadmap.md` justified its P0 priorities with a note about the business direction of a brand — an internal product decision, published. A reader of a standards contribution learns from that what our commercial priorities are, which is exactly the line the participation rules draw around third-party submissions | one internal note in `framework/adapter-roadmap.md`, found by scanning the public docs for the brand name | reworded to a technical justification, and **mechanised**: check 12 `identity` fails on any brand reference outside the repository URL (mutant `identity/brand-in-docs`), on any reverse assertion about entity status, on any self-claim to be a standard, on a corporate copyright holder, and on a missing participation docket. The check is literal, so even an example command quoting the name trips it |

### Still open (not defects in the gate; they are release decisions)

1. `.zenodo.json` precedence: only `CITATION.cff` exists today, which is correct.
   Adding a `.zenodo.json` later silently overrides it — a trap, not a bug.

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
*main* branch.

Check `parity` turns that observation into a measurement: it resolves the public
default branch as this clone last fetched it (`origin/main`), reports the commit
gap, and then exports **that** tree and runs the documented commands against it.
On this tree it reports `origin/main` **14 commits behind** the reviewed branch —
the published tree is not the reviewed tree — while the quickstart and both gold
suites still run on it (`rc=2` = reject for the quickstart case, `rc=0` for the
5/5 and 26/26 suites). So a stranger's clone works; it is just old, and none of
the fixes in this review are in it. That is the largest remaining gap between
"what we fixed" and "what the world can see", and it is a merge, not a patch.

Anonymous read of `raw.githubusercontent.com/.../main/README.md` is gate check
`public`. On 2026-11-04 the proxy in front of this host returned `502` for part
of the run; the check recorded `BLOCKED` (with the control URL's failure as
evidence) rather than turning a network outage into a repository defect.

## 6. Legal and process gate — the S7 compliance seat

The engineering checks cannot see the obligations that actually decide whether a
standards body can accept a contribution, so a separate seat reviewed them:
**`release-prep/STANDARDS_CONTRIBUTION_READINESS.md`** (13 items, each with the
standard it comes from, the artefact that satisfies it and a
pass / risk / blocked verdict — plus the retrieval scope behind every negative
claim, so "we found nothing" cannot masquerade as "there is nothing").

What it found, in one line each:

- **Fixed this round:** `CONTRIBUTING.md` had an *outbound* licence and no
  *inbound* one. A third-party pull request would therefore carry no licence at
  all, and "redistributable without restriction" (ITU-T A.1 §3.1.6) would break at
  the first outside contribution. It now states inbound = outbound, and states
  plainly that there is **no CLA** and **no enforced DCO** rather than implying
  otherwise.
- **Risk, with material present:** the paper declaration that accompanies an
  ITU-T submission (§3.1.7) is not written; no Patent Statement has been filed and
  no essential-patent search has been done (Apache-2.0 §3 grants a licence, which
  is not the same as a declaration to the venue); the DOI is absent until Zenodo
  mints one, and `CITATION.cff` correctly does not invent one.
- **Blocked, and not by code:** the 12-calendar-day submission window (§3.1.8) has
  no schedule, and the W3C Community Group CLA needs a decision on who signs —
  an individual or the entity.

Three items are escalated rather than decided here, because they are outside what
a code review can settle: which patent declaration to file, who holds the CLA, and
whether to submit as a document contribution or a software contribution.

### What we may submit, and as whom

The participation rules are not advice; they decide whether a submission is
accepted at all, so they are recorded and gated rather than remembered:

- **`release-prep/STANDARDS_PARTICIPATION_DOCKET.md`** — the channel table (what
  an individual may use, and what requires a legal entity we do not claim), the
  in-flight window ledger, and the twelve red lines with this round's verdict on
  each. It is the progress source of truth, not a narrative.
- **`contributions/itu-fg-tida/TD-executable-assurance-gates.md`** — a first
  contribution drafted to the shape a focus group takes: plain language first,
  then four clauses written as text that could be pasted into a draft, then the
  commands and exit statuses that show the clauses can be executed, then what the
  contribution does *not* cover. It claims no standing, carries no DOI, and points
  at the repository in a single line instead of pasting our publication into
  someone else's process repository.
- **Check 12 `identity`** keeps the wording honest mechanically, because wording
  is the part that rots silently.

The one action this repository cannot take is the submission itself: it is
irreversible, it is made in a named individual's capacity, and the deadline is
still unknown pending the secretariat's answer. That stays with the person whose
name it would carry.

## 7. Verdict

**Not releasable yet — and this time the reason is not the code.**

The machine verdict is whatever `review/evidence/pre_release_latest.json` says on
the commit you are reading. On this branch it is **FAIL, and the one failing
finding is `parity`** — every other check passes, including the probes. That is
deliberate: a review of a tree nobody can fetch answers the wrong question, so
"published ≠ reviewed" is recorded as a failure rather than as a footnote.

The verdict *here* is a judgement about the world, and it is **BLOCKED** for
three reasons that no patch can close:

1. **The fixes are pushed, not merged.** `parity` splits the question in two,
   because the two answers call for different actions. `parity-pushed` asks
   "can a stranger fetch exactly what was reviewed?" — **PASS** as of
   `87cf070` on `origin/fix/s6-review-20261104`. `parity-sha` asks "does a
   stranger landing on the default branch get it?" — **FAIL**, `origin/main`
   is 17 commits behind. The remaining action is a merge by the repository
   owner, not another commit from this session.
2. **No DOI, no tag, no release.** `CITATION.cff` correctly carries no DOI until
   Zenodo mints one; minting requires the account holder to enable the GitHub
   integration. Publishing a citation entry without an identifier would break the
   FORCE11 persistence principle.
3. **No CLA, no DCO, and no paper declaration.** A W3C Community Group
   contribution needs a signed CLA (and a decision on who signs it); an ITU-T
   submission needs the §3.1.7 paper declaration and a patent position; this
   repository has neither a CLA bot nor a `Signed-off-by` requirement. §6 and
   `release-prep/STANDARDS_CONTRIBUTION_READINESS.md` track these; two of them are
   entity-level decisions, not patches.

The earlier drafts of this section said push was blocked and the branch was
`ahead 4` — that was true when written and is false now, so it is replaced rather
than left to rot: all nine commits are on the remote, and `parity-pushed` is the
finding that proves it rather than the sentence that claims it.

### Verified from outside — 2026-11-04

Not "it is on GitHub" but "here is what a stranger gets from it". A fresh shallow
clone of the pushed branch, over the transport a stranger uses, was handed only
the repository:

```bash
git clone --depth 1 --branch fix/s6-review-20261104 \
    https://github.com/Medxpert-org/lgd-engine.git
# HEAD = 103105a
python review/redteam_probe.py --selfcheck            # 22/22 probes PASS, SELFCHECK PASS
python review/pre_release_review.py --selftest        # SELFTEST PASS, 19 mutants
# review/report.html -> MACHINE · FAIL / RELEASE · BLOCKED
```

Every number in that list came from the clone, not from this machine: no path in
the tree points back here, and the two harnesses need nothing that is not in the
repository. The one question the clone cannot settle is `parity-sha` — only the
owner merging it settles that, which is item 1 above.

Re-run before any release:

```bash
python review/redteam_probe.py --selfcheck           # 22 probes, each proven able to fail
python review/pre_release_review.py --json review/evidence/pre_release_latest.json
python review/pre_release_review.py --selftest       # proves all 12 checks (19 mutants) can fail
python review/pre_release_review.py --only legal     # the legal artefacts, substance not presence
python framework/gate_bot.py                         # 6 checks
python docs/validate_openapi.py                      # contract/code lockstep, 20/20
```
