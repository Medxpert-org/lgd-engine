# Verdict drift across releases

Which case verdicts moved between a pinned git ref and the working tree.
Regenerate: `python benchmarks/verdict_drift.py --write`; check: `python benchmarks/verdict_drift.py --check`.

## 1bc5340 — #30 — before the seven red-team fixes

_seven cases still earned go; this row proves the instrument can see a flip_

- cases measured: 37 of 37
- verdicts unchanged: 30
- verdicts changed: 7

| case | domain | before | after | declared expectation |
|---|---|---|---|---|
| `FDA-510K-RED-01` | 510k | go | hold | hold |
| `FDA-PM-RED-01` | postmarket | go | hold | hold |
| `FDA-PCCP-RED-01` | pccp | go | hold | hold |
| `MDR-RED-01` | mdr | go | hold | hold |
| `MDR-RED-02` | mdr | go | hold | hold |
| `NMPA-RED-01` | nmpa | go | hold | hold |
| `NMPA-RED-02` | nmpa | go | hold | hold |

## 28fe22b — #44 — before representation safety

_only spelling was canonicalised: no shipped case was meant to move_

- cases measured: 37 of 37
- verdicts unchanged: 37
- verdicts changed: 0

No case changed verdict. That is the point of this row: a release may change how a field is read without changing what any shipped case decides.

## 58c0369 — #45 — representation safety merged

_the anchor for this generation: an undeclared flip shows up against this row_

- cases measured: 37 of 37
- verdicts unchanged: 37
- verdicts changed: 0

No case changed verdict. That is the point of this row: a release may change how a field is read without changing what any shipped case decides.

