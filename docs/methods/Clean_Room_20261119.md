# Clean-room rerun on a second machine

> This is a dated snapshot of one session, not a standing claim. Numbers below refer
> to commit `953805b` only. Current baseline: `Eval_Report_v1.md` and `README.md`.

## Why this file exists

Every check in this repository until today was run on the machine that wrote it.
"Anyone can rerun this" was therefore an assertion, not a fact. This records the first
run on a *different* computer, with an anonymous HTTPS clone — no deploy key, no
maintainer credentials, no local state, no virtualenv.

## Conditions

| | Machine A (author) | Machine B (clean room) |
|---|---|---|
| OS | Windows 11 | Windows 11 |
| Python | 3.11 | 3.13.18 |
| git | present | 2.47.1.windows.1 |
| Clone | local working tree | `git clone --depth 1 --branch ci/contract-tests-20261118 https://github.com/MedXpert-org/lgd-engine.git` |
| Credentials | maintainer | **none** (anonymous) |
| Elapsed | — | about 10 minutes |

Machine B is a second physical desktop belonging to the same person; it is *another
machine*, but not another *organisation*. That distinction matters for what this
proves and is stated plainly in `Method_Note_v1.md`.

## Results on machine B, commit `953805b`

| Command | Result |
|---|---|
| `python -m unittest discover -s tests` | **OK**, 60 tests |
| `python lgd_engine/mcp_smoke.py` | **SMOKE: PASS** (7 tools) |
| `python benchmarks/adversarial_baseline.py` | gate **12/12**, naive **5/12**, delta **7** |
| `python benchmarks/build_demo_page.py --check` | **OK: demo page matches the engine output** |
| `python benchmarks/clause_matrix.py` | **60 rules / 60 with a basis (LAW 51 / DOCTRINE 9)** |
| `python benchmarks/verdict_cost.py` | deterministic **YES**, **0 network / 0 model** |
| `python benchmarks/edge_claims.py` | **observed 2 / inferred 2 / unverified 3**, problems **0** |
| `python benchmarks/eval_method_note.py --repo <clean clone>` | **20/20 checks passed** |

## The one number that changed, and why it is published as a budget

`verdict_cost.py` reports a p95 of **9.2 µs** on machine A and **27.0 µs** on machine B
for the same 6,000 verdicts. Same code, same cases, same answer — different CPU.

This is exactly why the public page publishes a *tested budget* (≤ 500 µs) instead of
the measured microseconds: a per-run measurement on the front page would flap every
time someone reruns it on different hardware, and a number that moves without the
engine changing is not evidence of anything.

## What this run does not prove

- It does not show that an **unaffiliated** reviewer reproduces it. Two machines, one owner.
- It does not show the verdicts are **clinically or legally correct** — only that the
  same inputs produce the same outputs on different hardware, and that the repository's
  self-checks hold there.
- Machine B has no test path that machine A lacks; a Linux/macOS run is still untested
  by a human, though CI covers Linux.
