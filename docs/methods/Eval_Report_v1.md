# Evaluation report — generated, not written

This file is produced by `benchmarks/eval_method_note.py --report`. Do not edit
it by hand: the marker line below is asserted by check C12, so a hand-written
number that disagrees with the repository fails the evaluation. C12 is excluded
from the counts below — a report cannot contain the verdict on itself.

`<!-- eval-report branch=ci/contract-tests-20261118 head=f124772 checks=17 passed=17 -->`

Run at 2026-11-18 18:07 UTC against `ci/contract-tests-20261118` at `f124772`, from a fresh clone.

| # | Claim checked | Result |
|---|---|---|
| E0 | clone arrives clean (no case-only or uncommitted noise) | PASS |
| C1 | NMPA table 7/7 offline | PASS |
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
| X1 | tampered page makes --check fail | PASS |
| X2 | suite reports Ran 54 tests | PASS |
| X3 | dependencies = [] and no third-party imports | PASS |
| X4 | note claims 30 cases, disk has 30 | PASS |
| X5 | tree still clean after the whole run | PASS |

**17/17 checks passed** (plus C12, which validates this file).

Scope of this report: it says nothing about correctness against real filings;
it says that every claim the method note makes about *itself* survives an
outsider re-running the same commands on a clean clone.
