# Evaluation report — generated, not written

This file is produced by `benchmarks/eval_method_note.py --report`. Do not edit
it by hand: the marker line below is asserted by check C12, so a hand-written
number that disagrees with the repository fails the evaluation. C12 is excluded
from the counts below — a report cannot contain the verdict on itself.

`<!-- eval-report branch=redteam/pccp-absence-20261119 head=7013212 checks=19 passed=19 -->`

Run at 2026-11-19 00:03 UTC against `redteam/pccp-absence-20261119` at `7013212`, from a fresh clone.

| # | Claim checked | Result |
|---|---|---|
| E0 | clone arrives clean (no case-only or uncommitted noise) | PASS |
| C1 | NMPA table 9/9 offline | PASS |
| C2 | byte-identical rerun | PASS |
| C3 | critical rule forces reject | PASS |
| C4 | go without evidence downgraded to hold | PASS |
| C5 | crashing judge is flagged, not a clean veto | PASS |
| C6 | exit codes reject=2 / go=0 / usage=64 | PASS |
| C7 | MCP smoke: 7 tools + RBAC both ways | PASS |
| C8 | baseline gate 12/12 vs naive 5/12 | PASS |
| C9 | dossier page in sync with engine | PASS |
| C10 | every rule names a LAW / DOCTRINE basis | PASS |
| C11 | verdict deterministic + cheap (no model) | PASS |
| C13 | competitor claims carry provenance labels | PASS |
| X1 | tampered page makes --check fail | PASS |
| X2 | suite runs and reports 69 tests | PASS |
| X3 | dependencies = [] and no third-party imports | PASS |
| X4 | note claims 37 cases, disk has 37 | PASS |
| X5 | tree still clean after the whole run | PASS |
| X6 | docs quote 69 assertions and 37 cases everywhere, and every cited audit command exists | PASS |

**19/19 checks passed** (plus C12, which validates this file).

Scope of this report: it says nothing about correctness against real filings;
it says that every claim the method note makes about *itself* survives an
outsider re-running the same commands on a clean clone.
