# lgd-engine v0.1.0 · Demo1 — 医械变更门禁判定

> Local-only, zero-network, zero-external-action MVP.
> This is the **first concrete domain adapter** for the LGD (有籍有证有门禁) kernel.

## What it does

Given a JSON description of a medical-device change (risk class, change type,
recall class, evidence sufficiency, …), the gate emits one of:

- **GO** (🟢) — record-and-go, no further submission required
- **HOLD** (🟡) — conditional pass: needs supplementary evidence / 510(k) submission
- **REJECT** (🔴) — critical veto: change cannot transition; re-submit required

Rules are distilled from **10 VERIFIED FDA / NMPA change cases**
(`P2_医械变更判例分级样本集_20261103.md`); the five demo cases are
desensitized restatements, each tagged with its source case id.

## Layout

```
mvp/
├── lgd_engine/             # domain-agnostic kernel
│   ├── __init__.py         # version 0.1.0
│   ├── theory/laws.yaml   # LGD 三律 (有籍 / 有证 / 门禁)
│   ├── judges/
│   │   ├── base.py         # DomainJudge Protocol + JudgeVerdict
│   │   └── judge_510k.py   # first domain adapter
│   ├── gate/engine.py      # GateEngine aggregates verdicts + enforces laws
│   └── memory/localmem_min.py  # SQLite decision memory (FTS5 / LIKE fallback)
└── demo1/
    ├── cases/              # 5 desensitized case JSONs
    ├── change_gate.py      # CLI entry
    ├── test_demo1.py       # pure-assert self-test
    ├── web.py              # optional stdlib web UI
    ├── run_demo1.ps1       # one-click launcher (Windows PowerShell)
    └── README.md
```

## Runtime dependencies

- Python **3.9+** (uses `X | None` syntax; tested on 3.11)
- **No third-party pip packages required** for the default path.
  - `pyyaml` is *not* required — `laws.yaml` is loaded by hand if ever needed;
    the kernel itself does not parse YAML at runtime.
  - `fastembed` is **optional**: if installed, `LocalMemory.vector()` will use
    it; otherwise it degrades to SQLite `LIKE`/FTS5 keyword recall and tags
    the result as `fallback_keyword_no_fastembed`.
  - Install fastembed if you want vector recall: `pip install fastembed`
    (not required for this demo).

## Quick start (Windows PowerShell)

From `mvp/` directory:

```powershell
# one-click: self-test + run all cases
.\demo1\run_demo1.ps1

# or run a single case
python -m demo1.change_gate --case demo1/cases/case01_red_pma_process.json

# or run the self-test directly
python -m demo1.test_demo1

# optional web UI
python -m demo1.web        # then open http://127.0.0.1:8765
```

Exit codes from the CLI: `0`=go, `1`=hold, `2`=reject.
The self-test exits `0` only when **all** cases match their expected verdict.

## Case → expected verdict

| Case | Desensitized from | Expected |
|---|---|---|
| case01_red_pma_process.json  | MAJ-01 PMA battery / process change control | **reject** |
| case02_red_material.json     | MAJ-02 Class 1 recall, material nonconformance | **reject** |
| case03_yellow_special_510k.json | MOD-01 Special 510(k) label expansion | **hold** |
| case04_yellow_traditional_510k.json | MOD-02 Traditional 510(k) config reduction | **hold** |
| case05_green_label.json      | MIN-01 Class 3 label correction | **go** |

## Fixed interfaces (shared with Demo2 line)

```python
JudgeVerdict = {"verdict": "go|hold|reject",
                "reasons": [{"rule": str, "level": "critical|major|minor", "detail": str}],
                "evidence": [{"kind": str, "ref": str}]}

class DomainJudge:
    domain: str
    def evaluate(self, ctx: dict) -> dict   # returns JudgeVerdict

DecisionRecord = {"time": iso, "initiator": str, "subject": str,
                  "decision": str, "basis": str,
                  "status": "executed|pending|vetoed", "evidence_refs": []}
```

## LGD laws enforced

- **L1-有籍** — every CLI run writes a DecisionRecord to `demo1/demo1_memory.sqlite`.
- **L2-有证** — a `go` verdict with zero evidence refs is auto-downgraded to `hold`.
- **L3-门禁** — any `critical` reason forces final verdict to `reject`.
