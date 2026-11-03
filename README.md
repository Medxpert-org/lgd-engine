# LGD Engine

[![status](https://img.shields.io/badge/status-MVP%20draft-lightgrey)]()
[![license](https://img.shields.io/badge/license-Apache--2.0-blue)]()
[![python](https://img.shields.io/badge/python-3.10%2B-green)]()
[![gate CI](https://img.shields.io/github/actions/workflow/status/Medxpert-org/lgd-engine/gate.yml?branch=main&label=gate%20CI)]()

**LGD Engine is the judgment core for medical-device AI change control.**
While general agent frameworks orchestrate LLMs, LGD Engine supplies the
*theory-bound gate*: every change verdict is produced by a auditable, offline-testable
judgment chain grounded in the LGD theory (three laws, 有籍有证有门禁 /
registered-evidenced-gated, 触点即门 / every touchpoint is a gate).

## The LGD Foundation

LGD Engine is not a hollow scaffold: it is the executable expression of a
complete theory-and-evidence stack, all distilled into runnable rules:

- **Theory** — the LGD doctrine, specified as declarative rules in
  `lgd_engine/theory/laws.yaml` (law, trigger predicates, gate action).
- **Published work** — a publication line (records registered with DataCite)
  that grounds the doctrine in medical-device change control and AI-agent
  governance; the paper accompanying this repository is under preparation and
  its self-citations are placeholders until registration.
- **Verified precedents** — change-classification precedents (MAJ/MOD/MIN,
  including FDA recall events such as Z-1924-2025 and Z-0893-2026) and a library
  of real change-control cases, distilled into the judge rules under
  `lgd_engine/judges/`.
- **13-domain judgment knowledge** — clinical evaluation, postmarket
  surveillance, UDI, SaMD and more, mapped onto the 11-stage medical-device
  ecosystem (see `framework/ecosystem-map.md` and `framework/eco-regulatory-matrix.md`,
  11 stages x 8 jurisdictions). Two domain judges are implemented in this
  release (510(k) change classification, post-market); the remaining domains
  are roadmap adapters.
- **International alignment** — the roadmap tracks the ITU FG-TIDA and W3C
  AI-agent memory/interop threads, so the rules follow where global standards
  are heading.

Every judge carries an explicit evidence source (precedent id / case entry /
regulation citation), making the chain theory → code → verifiable test
(see `run_demo1.ps1` / `run_demo2.ps1` self-tests, enforced in CI).

## Quickstart

From a clone (recommended — `pip install lgd-engine` is not yet available; the
public 0.1 release will publish it):

```bash
# Windows (stock Python 3.9+)
.\demo1\run_demo1.ps1            # 5/5 + 6/6 change-gate self-tests
.\demo2\run_demo2.ps1            # 26/26 five-seat review self-tests

# Any OS
python demo1/test_demo1.py       # change-gate gold tests
python demo2/test_demo2.py       # five-seat review tests
python framework/gate_bot.py     # CI gate (four checks)
```

One decision from a case JSON:

```bash
python -m demo1.change_gate --case demo1/cases/case01_red_pma_process.json
python -m demo1.change_gate --case demo1/cases_jurisdiction/supplier_swap.json --jurisdiction NMPA
python -m demo1.change_gate --all
```

Offline by default: the core gate runs with no LLM required (`requires_llm: false`),
so verdicts are reproducible in CI.

## Architecture

Layered design, adapters on the outside, judgment core in the middle:

```
L0  AI hosts  --stdio/streamable-http-->  L1  lgd.gate (aggregation core)
                                              |
                                  L1.5  skill registry (skill.yaml manifest)
                                              |
                                  L2  DomainJudge x 13+ (offline, gold-tested)
```

See `docs/architecture.md` (to be added) and the framework draft:
`framework/skill-manifest-spec.md`, `framework/plugin-adapter.md`.

The MCP server binds stdio on a local machine and trusts the caller's role
claim — it is a local-trust adapter, not a network authentication boundary
(production wiring is scheduled for the public 0.1 release).

## Interface layer (Beta)

Four contract surfaces are in the trunk; all are local-trust adapters until
the public 0.1 release wires them to production endpoints.

- **REST / OpenAPI** — contract: `docs/openapi.yaml` (OpenAPI 3.1,
  `/v1/judge` POST + `/v1/decisions` GET). Validate it:
  `python docs/validate_openapi.py` (17/17 checks, stdlib).
- **SSE event stream** — `demo2/sse_server.py` tails the append-only
  `demo2/events.jsonl` (six event types). Generate a log that covers all six
  (the `critical` case triggers a `HOLDED` frame), then smoke — the server
  self-hosts and exits after the stream check:
  ```bash
  .\demo2\run_demo2.ps1 critical              # generates events.jsonl incl. HOLDED
  python -m demo2.sse_server --port 8770 --smoke   # streams, asserts 6 types, exits
  ```
- **MCP server (stdio)** — `lgd_engine/mcp_server.py`; the driver
  `python lgd_engine/mcp_smoke.py` runs initialize / tools list / judge /
  RBAC-deny against it (read-only role, denied tool returns -32003).
- **TypeScript SDK skeleton** — `lgd-engine-ts/` (zero-dependency types +
  `Client` skeleton mirroring the OpenAPI contract);
  `cd lgd-engine-ts && npm run smoke` under Node 18+.
- **Container** — `Dockerfile` + `docker-compose.yml` (verified on Docker
  Desktop 4.89.0; REST demo binds `127.0.0.1:18090`).

## Gate bot (CI)

```bash
python framework/gate_bot.py          # exit 0 = PASS, exit 1 = FAIL
powershell -File framework/gate.ps1    # Windows wrapper
```

Checks: offline gold tests, LICENSE/NOTICE present, no plaintext keys, manifest syntax.

## Security baseline

`security/security_baseline.md` maps OWASP Top 10 (2021) and OWASP Top 10 for
LLM Applications (2025) to concrete defenses in this tree.
`python security/security_scan.py` re-checks the tree before every release.

## Citation

```
@misc{zhao_lgd_engine_2026,
  author = {Zhao, X.},
  title  = {LGD Engine: A Theory-Bound Judgment Core for Medical-Device AI Change Control},
  year   = {2026},
  note   = {Preprint placeholder — to be completed upon submission}
}
```

## Author

**Zhao, X. (Independent Researcher)**

## License & Notice

Code: Apache License 2.0 — see `LICENSE`.
Theory attribution and provenance: see `NOTICE`.
