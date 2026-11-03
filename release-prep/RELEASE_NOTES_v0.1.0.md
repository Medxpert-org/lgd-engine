# LGD Engine v0.1.0 — theory-bound change gate (MVP)

First tagged release. A judgment core for medical-device AI change control:
it decides **go / hold / reject** for a proposed change, and every verdict
carries the rule it came from and the evidence it was checked against.

## What it does

- **Change gate** — `python -m demo1.change_gate --case <file>`: emits a verdict
  with per-judge reasons and evidence. Exit code **is** the verdict
  (`0=go`, `1=hold`, `2=reject`); a correct REJECT exits 2, deliberately.
- **Five-seat review** — `demo2` runs POSTED → COMMENTED → VOTED → HOLDED /
  FINALIZED → DECISION_LOGGED over an append-only event log, streamable over
  SSE (`/events/stream`).
- **Gate bot** — `python framework/gate_bot.py`, 5 checks: offline gold test,
  license/NOTICE, no plaintext keys, manifest syntax, README-count drift.
- **Security baseline** — L1 input guard / L2 tool RBAC / L3 output filter,
  plus `security/security_scan.py` for pre-release scans.
- **Contracts** — OpenAPI 3.1 in `docs/openapi.yaml` (`/v1/judge`,
  `/v1/decisions`), validated by `docs/validate_openapi.py` (17 structural
  checks with PyYAML; 5 text-scan checks without, and it says so).
- **MCP** — `python -m lgd_engine.mcp_server` (`lgd-engine-mcp` entry point).

## What it does **not** do

Stated here so the release is not read as broader than it is:

- It does not call an LLM. `requires_llm: false`; the judges are deterministic.
- It does not implement the `/v1` service. `docs/openapi.yaml` freezes the
  production wire shape; `demo1/web.py` (`/judge`) is the behavioral reference.
- It does not judge all 11 lifecycle stages. 3 of 11 have working judges
  (#5 postmarket / #6 vigilance share one, #7 change control); the rest are
  named adapters on the roadmap (`framework/adapter-roadmap.md`).
- It is not on PyPI yet. Install from the repository.
- The 14-link ecosystem caliber quoted in ecosystem publications is **not**
  defined in this repository; `framework/ecosystem-map.md` (11 links) is the
  binding list here.

## Install

```bash
git clone https://github.com/Medxpert-org/lgd-engine.git
cd lgd-engine
python -m demo1.change_gate --case demo1/cases/case01_red_pma_process.json
```

Stdlib only. `pip install -e ".[yaml]"` adds the structural OpenAPI validation
and strict manifest parsing.

## Evidence at this tag

```
demo1 5/5 | demo2 26/26 | gate_bot 5/5 | security_scan 0 findings
openapi 17/17 (structural) | 5/17 (stdlib, mode printed)
injection 6/6 | MCP PASS | SSE 6/6, no traceback
```

Negative controls are part of the evidence, not an afterthought: the stdlib
OpenAPI run reports itself as text-scan only, a deliberately broken injection
guard yields 5/6 and exit 1, and a README count that no table backs fails
gate check 5.

## Citation

`CITATION.cff` is present and honest: version `0.1.0`, no DOI yet. A software
DOI is minted by Zenodo on the maintainer's account once the GitHub–Zenodo
webhook is enabled — see `release-prep/RELEASE_CHECKLIST.md` §3. Until then,
cite the repository URL.
