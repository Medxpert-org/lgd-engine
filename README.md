# LGD Engine

[![status](https://img.shields.io/badge/status-MVP%20draft-lightgrey)]()
[![license](https://img.shields.io/badge/license-Apache--2.0-blue)]()
[![python](https://img.shields.io/badge/python-3.9%2B-green)]()
[![gate CI](https://img.shields.io/github/actions/workflow/status/Medxpert-org/lgd-engine/gate.yml?branch=main&label=gate%20CI)](https://github.com/Medxpert-org/lgd-engine/actions/workflows/gate.yml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/Medxpert-org/lgd-engine/codeql.yml?branch=main&label=CodeQL)](https://github.com/Medxpert-org/lgd-engine/actions/workflows/codeql.yml)

**LGD Engine is the judgment core for medical-device AI change control.**
While general agent frameworks orchestrate LLMs, LGD Engine supplies the
*theory-bound gate*: every change verdict is produced by an auditable,
offline-testable judgment chain grounded in the LGD theory (three laws,
有籍有证有门禁 / registered-evidenced-gated, 触点即门 / every touchpoint
is a gate). Zero runtime dependencies — the core gate runs with no LLM.

## Quickstart

Shortest path — clone, run the gold tests, get your first verdict, then
wire it to your agent host:

```bash
git clone https://github.com/Medxpert-org/lgd-engine.git
cd lgd-engine
python -m demo1.change_gate --case demo1/cases/case01_red_pma_process.json
# exit code: 0 = go, 1 = hold, 2 = reject
```

Verify the whole gate before trusting it (stock Python 3.9+, stdlib only):

```bash
# Windows
.\demo1\run_demo1.ps1            # 5/5 + 6/6 change-gate self-tests
.\demo2\run_demo2.ps1            # 26/26 five-seat review self-tests

# Any OS
python demo1/test_demo1.py       # change-gate gold tests
python demo2/test_demo2.py       # five-seat review tests
python framework/gate_bot.py     # CI gate (four checks)
```

One decision from a case JSON:

```bash
python -m demo1.change_gate --all
python -m demo1.change_gate --case demo1/cases_jurisdiction/supplier_swap.json --jurisdiction NMPA
```

Editable install (optional) exposes the console script:

```bash
pip install -e .        # then use `lgd-gate` (see pyproject [project.scripts])
```

Then point your MCP client at it — copy-paste configs are in
[Interface layer](#interface-layer-beta) below.

## Architecture

Layered design — adapters on the outside, judgment core in the middle,
fully offline:

```
L0  AI hosts (Claude Desktop, Cursor, agents)
        │  stdio / (streamable-HTTP in 0.1)
        ▼
L1  lgd.gate  ── aggregation core (GateEngine + GateReport)
        │
        ├── L1.5  skill registry (skill.yaml manifest)
        │
        ▼
L2  DomainJudge ×13+  (offline, gold-tested; 2 shipped: 510(k), post-market)
        ▲
        │  evidence: precedents / cases / regulation citations
L3  lgd_engine/theory/laws.yaml   (declarative three-law rules)
```

Runnable surfaces today: `python -m demo1.web` serves a local web UI +
JSON endpoint (POST `http://127.0.0.1:8765/judge`) that returns the exact
`GateReport` shape the frozen OpenAPI contract defines.

See the framework drafts for the registry and adapter specs:
`framework/skill-manifest-spec.md`, `framework/plugin-adapter.md`,
`framework/ecosystem-map.md` (11 stages × 8 jurisdictions).

## Interface layer (Beta)

Four contract surfaces are in the trunk; all are local-trust adapters
until the public 0.1 release wires production endpoints (TLS, auth).

| Interface | Transport / entry | Run it | Verify it |
|---|---|---|---|
| REST (demo) | stdlib HTTP, `127.0.0.1:8765`, `POST /judge` | `python -m demo1.web` | `curl -X POST http://127.0.0.1:8765/judge -H 'Content-Type: application/json' -d @demo1/cases/case01_red_pma_process.json` |
| REST contract | OpenAPI 3.1, `docs/openapi.yaml` (`/v1/judge`, `/v1/decisions`) | — | `python docs/validate_openapi.py` (17/17 checks, stdlib) |
| SSE event stream | tails append-only `demo2/events.jsonl`, 6 event types | `python -m demo2.sse_server --port 8770 --smoke` | exits 0 after asserting all 6 types |
| MCP server (stdio) | `lgd_engine/mcp_server.py` | `python lgd_engine/mcp_smoke.py` | smoke exercises initialize / tools list / judge / RBAC-deny (denied → -32003) |
| TypeScript SDK | `lgd-engine-ts/` (zero-dep types mirroring OpenAPI) | `cd lgd-engine-ts && npm run smoke` | Node 18+; smoke exits 0 |
| Container | `Dockerfile` + `docker-compose.yml` | `docker compose up` | REST demo on `127.0.0.1:18090` (verified Docker Desktop 4.89.0) |

> Contract status note: `docs/openapi.yaml` freezes the production wire
> shape (`/v1/*`, TLS, bearer auth). No `/v1` service exists in the tree
> yet — `demo1/web.py` (`/judge`, no `/v1` prefix) is the behavioral
> reference for request/response semantics.

### MCP client config (copy-paste, local-trust)

Run the server from a clone for now; from the public 0.1 release,
`pip install lgd-engine` provides the `lgd-engine-mcp` console entry
(equivalent to `python -m lgd_engine.mcp_server`). Both forms resolve
all internal paths from the package itself, so no specific working
directory is required.

Claude Desktop — `claude_desktop_config.json`
(Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "lgd-engine": {
      "command": "python",
      "args": ["-m", "lgd_engine.mcp_server"]
    }
  }
}
```

Cursor — `.cursor/mcp.json` at your project root, or use the bundled
`.cursor-plugin/plugin.json` (declares the same stdio server for the
Cursor plugin host):

```json
{
  "mcpServers": {
    "lgd-engine": {
      "command": "python",
      "args": ["-m", "lgd_engine.mcp_server"]
    }
  }
}
```

Platform notes:
- Windows: `python` (or `py -3`); macOS/Linux: `python3` — replace the
  `command` value accordingly, or use the absolute path of your interpreter.
- The server binds stdio locally and trusts the caller's role claim
  (local-trust adapter, no network authentication boundary) — production
  wiring is scheduled for the public 0.1 release.
- streamable-HTTP: the 0.1 release will also expose a streamable-HTTP
  endpoint; client config will then use `"url"` instead of
  `command`/`args`.

## The LGD Foundation

LGD Engine is not a hollow scaffold: it is the executable expression of a
complete theory-and-evidence stack, all distilled into runnable rules.

The judgment chain is grounded in three laws:

1. **有籍 · Registered** — every judgment is tied to a registered context:
   a device record, a predicate, a case identifier. No context, no verdict.
2. **有证 · Evidenced** — every decision rule must cite evidence (a
   precedent id, a case entry, a regulation citation). A `go` with zero
   evidence refs is downgraded to `hold`.
3. **有门禁 · Gated** — every touchpoint is a gate (触点即门): release
   decisions, agent tool calls, MCP invocations and CI pushes all pass
   through the same three-state gate (`go` / `hold` / `reject`).

The rest of the stack:

- **Theory** — the doctrine, specified as declarative rules in
  `lgd_engine/theory/laws.yaml` (law, trigger predicates, gate action).
- **Published work** — a publication line (records registered with
  DataCite) that grounds the doctrine in medical-device change control and
  AI-agent governance; the paper accompanying this repository is under
  preparation and its self-citations are placeholders until registration.
- **Verified precedents** — change-classification precedents (MAJ/MOD/MIN,
  including FDA recall events such as Z-1924-2025 and Z-0893-2026) and a
  library of real change-control cases, distilled into the judge rules
  under `lgd_engine/judges/`.
- **13-domain judgment knowledge** — clinical evaluation, postmarket
  surveillance, UDI, SaMD and more, mapped onto the 11-stage medical-device
  ecosystem (see `framework/ecosystem-map.md` and
  `framework/eco-regulatory-matrix.md`, 11 stages × 8 jurisdictions). Two
  domain judges are implemented in this release (510(k) change
  classification, post-market); the remaining domains are roadmap adapters.
- **International alignment** — the roadmap tracks the ITU FG-TIDA and W3C
  AI-agent memory/interop threads, so the rules follow where global
  standards are heading.

Every judge carries an explicit evidence source, making the chain
theory → code → verifiable test (enforced in CI).

## Gate bot (CI) & security baseline

```bash
python framework/gate_bot.py          # exit 0 = PASS, exit 1 = FAIL
powershell -File framework/gate.ps1  # Windows wrapper
```

Checks: offline gold tests, LICENSE/NOTICE present, no plaintext keys,
manifest syntax (including adversarial re-checks: path-traversal manifest
entries and known secret shapes are rejected).

`security/security_baseline.md` maps OWASP Top 10 (2021) and OWASP Top 10
for LLM Applications (2025) to concrete defenses in this tree;
`python security/security_scan.py` re-checks the tree before every release.

## Verified test evidence (2026-11-03)

- demo1 change-gate gold tests: **5/5 PASS**; demo2 five-seat review: **26/26 PASS**
- `framework/gate_bot.py`: **4/4 checks PASS**; `security/security_scan.py`: **clean, 0 findings**
- MCP smoke (tools list + judge + RBAC deny): **PASS**; SSE smoke: **6/6 event types**
- GitHub Actions: `gate` CI and `CodeQL` **green on main**; Dependabot enabled;
  branch protection active (PR required + gate status check)
- Independent red-team / eval: 7-dimension security review closed with no open
  high-severity findings (LGD-EVAL-2026-009)

## Repository map

- Theory rules: `lgd_engine/theory/laws.yaml`
- Judges: `lgd_engine/judges/` (base, 510(k) change classification, post-market)
- Gate engine: `lgd_engine/gate/engine.py` — Python API:
  `GateEngine().register(Judge510kChange()).evaluate({...})` →
  `{verdict, reasons, per_judge, law_enforcements, evidence}`
- Framework docs: `framework/skill-manifest-spec.md`, `framework/plugin-adapter.md`,
  `framework/ecosystem-map.md`, `framework/13domains-mapping.md`
- LLM/agent-friendly summary: **[`llms.txt`](llms.txt)** (the llms.txt
  convention entry point for agents cloning this repo)

## Contributing

PRs welcome. Before opening one:

1. Run `python framework/gate_bot.py` — it must exit 0.
2. Every new judge or rule must ship with a gold test and an explicit
   evidence source (precedent id / case entry / regulation citation);
   a `go` verdict with zero evidence refs is rejected by the gate.
3. Keep the core offline and stdlib-only at MVP — optional extras go in
   `[project.optional-dependencies]`.

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
