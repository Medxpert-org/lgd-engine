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

## Prerequisites

- Python 3.9+ (`python --version`). Nothing else: the gate, the judges and the
  CLI are stdlib-only.
- `git`, if you are cloning rather than downloading a zip.
- Optional: PyYAML only for the 17-check OpenAPI validation
  (`pip install -e ".[yaml]"` from a checkout). Without it the validator says so
  and runs 5 text checks instead of pretending it ran 17.
- Node 18+ only for the TypeScript SDK smoke; Docker only for the compose demo.

## Quickstart

Shortest path — clone, run the gold tests, get your first verdict, then
wire it to your agent host:

```bash
git clone https://github.com/Medxpert-org/lgd-engine.git
cd lgd-engine
python -m demo1.change_gate --case demo1/cases/case01_red_pma_process.json
# exit code: 0 = go, 1 = hold, 2 = reject
```

> **Exit codes are verdicts.** In single-case mode the process exit code *is*
> the verdict: `0` = go, `1` = hold, `2` = reject. A correct reject therefore
> exits `2` — CI wrappers must map the code to the verdict instead of treating
> any non-zero exit as a failed run. `--all` instead exits `0` only when every
> case matches its expected verdict, and `1` on any mismatch. The CLI prints
> the same mapping on its last line.

Verify the whole gate before trusting it (stock Python 3.9+, stdlib only):

```bash
# Windows
.\demo1\run_demo1.ps1            # 5/5 + 6/6 change-gate self-tests
.\demo2\run_demo2.ps1            # 26/26 five-seat review self-tests

# Any OS
python demo1/test_demo1.py       # change-gate gold tests
python demo2/test_demo2.py       # five-seat review tests
python demo1/test_ecosystem.py   # 13-domain / 11-stage alignment tests
python framework/gate_bot.py     # CI gate (six checks)
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
| REST contract | OpenAPI 3.1, `docs/openapi.yaml` (`/v1/judge`, `/v1/decisions`) | — | `python docs/validate_openapi.py` — 5 text checks on a stdlib install, 17/17 structural once the `yaml` extra is installed from a checkout
(`pip install -e ".[yaml]"`; the package is not on PyPI yet); the script prints an explicit warning when it had to skip the 12 structural checks |
| SSE event stream | tails append-only `demo2/events.jsonl`, 6 event types | `python -m demo2.sse_server --port 8770 --smoke` | exits 0 only after all 6 types appear (precondition: see the SSE note below) |
| MCP server (stdio) | `lgd_engine/mcp_server.py` | `python lgd_engine/mcp_smoke.py` | smoke exercises initialize / tools list / judge / RBAC-deny (denied → -32003) |
| TypeScript SDK | `lgd-engine-ts/` (zero-dep types mirroring OpenAPI) | `cd lgd-engine-ts && npm run smoke` | Node 18+; smoke exits 0 |
| Container | `Dockerfile` + `docker-compose.yml` | `docker compose up` | REST demo on `127.0.0.1:18090` — NOT VERIFIED in the 2026-11-04 review (no Docker on the reviewing host, no container step in CI) |

> Contract status note: `docs/openapi.yaml` freezes the production wire
> shape (`/v1/*`, TLS, bearer auth). No `/v1` service exists in the tree
> yet — `demo1/web.py` (`/judge`, no `/v1` prefix) is the behavioral
> reference for request/response semantics.

> **SSE smoke precondition.** The smoke asserts all six event types, so the
> append-only log must already contain both a pass path and a hold path:
> `python -m demo2.session --case demo2/case_gate_report.json --auto` and
> `python -m demo2.session --case demo2/case_gate_report_critical.json --auto`
> (or `.\demo2\run_demo2.ps1` plus `.\demo2\run_demo2.ps1 critical`). On a
> fresh clone the log is empty, the smoke exits `1`, and it now names the
> missing types and the exact command to generate them.

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

**Theory home vs. engine home.** This repository is the engine
implementation. The theory itself — the doctrine, the domain papers and the
standards participation (ITU FG-TIDA, W3C) — is maintained in
[lgd-theory](https://github.com/zhaoxinghua09-cell/lgd-theory) under the
theory line; this repository neither restates nor owns it.

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
- **International alignment** — standards tracking lives in the theory line:
  the ITU FG-TIDA and W3C AI-agent memory/interop threads are followed in
  [lgd-theory](https://github.com/zhaoxinghua09-cell/lgd-theory), and this
  repository implements the rules those threads settle rather than tracking
  them itself.

Every judge carries an explicit evidence source, making the chain
theory → code → verifiable test (enforced in CI).

### Where the rest of the stack lives

This repository is the engine. The theory, the evidence catalog and the
challenge core are maintained in their own repositories, so this README
links out instead of duplicating them:

- Theory flagship (doctrine, three laws, domain papers):
  https://github.com/zhaoxinghua09-cell/lgd-theory
- Doctrine DOI — concept record: https://doi.org/10.5281/zenodo.22456647
  (current version v1.7.0: https://doi.org/10.5281/zenodo.23446125)
- Portal (all public surfaces in one place):
  https://zhaoxinghua09-cell.github.io/lgd-hub/
- Silent-failure catalog (failure modes this gate is built to catch):
  https://github.com/zhaoxinghua09-cell/silent-failure-catalog
- uibc-core — verifiable evidence packages for autonomous agents
  (software DOI https://doi.org/10.5281/zenodo.22821834):
  https://github.com/zhaoxinghua09-cell/uibc-core

### Three counts, three scopes

`11 stages` and `13 domains` appear throughout this repository and they
measure different things — neither is a count of the other:

- **11 stages** — the engine's implemented lifecycle model, i.e. the
  adapter family enumerated in `framework/ecosystem-map.md` (11 stages ×
  8 jurisdictions). This is an engineering projection: it covers the
  stages the gate can judge today or has a named adapter for.
- **13 domains** — the judgment-domain taxonomy (clinical evaluation,
  postmarket, UDI, SaMD, …) mapped onto those stages in
  `framework/13domains-mapping.md`. Several domains are cross-stage
  (compliance grading, risk management), which is why 13 ≠ 11.
- **14 links (14 环)** — a wider industry-chain caliber that circulates in
  the theory line's ecosystem publications. It is **not defined in this
  repository** and this README does not re-list it: `framework/ecosystem-map.md`
  is the binding list here and it has 11 links. Treat 14 as an external
  caliber — cite its defining document when you use it, and do not infer it
  from this repo.

So: 11 环节 = the list this repo binds (`framework/ecosystem-map.md`),
13 域 = judgment domains, and 14 环 = an external ecosystem caliber that
this engine projects onto those 11 stages rather than re-defines.

Both in-repo counts are asserted by CI: `framework/gate_bot.py` re-counts
the rows in `framework/ecosystem-map.md` (11) and
`framework/13domains-mapping.md` (13) and fails if either drifts from the
numbers above.

## Adversarial probes — the fail-closed claim, executable

```bash
python review/redteam_probe.py              # 22 probes over the real judges, MCP and CLI
python review/redteam_probe.py --selfcheck  # proves every probe can fail
```

The probes test properties, not examples: verdict monotonicity along every risk
axis, "unknown is never a go" for every enumerated field, law 2 reachability,
MCP role resolution, the documented `{ctx: {...}}` wrapper, exit-code semantics
and contract/code lockstep.

`--selfcheck` is the part that matters. Each probe declares a mutant — a
deliberately broken stand-in for the component under test — and the run fails
if that probe still passes against its mutant. A check that cannot fail is
decoration, so a vacuous probe is a hard failure here, not a green tick.

## Gate bot (CI) & security baseline

```bash
python framework/gate_bot.py          # exit 0 = PASS, exit 1 = FAIL
powershell -File framework/gate.ps1  # Windows wrapper
```

Checks: offline gold tests, LICENSE/NOTICE present, no plaintext keys,
manifest syntax (including adversarial re-checks: path-traversal manifest
entries and known secret shapes are rejected), and README count drift (the
`11 stages` / `13 domains` claims above are re-counted against their tables
on every run).

`security/security_baseline.md` maps OWASP Top 10 (2021) and OWASP Top 10
for LLM Applications (2025) to concrete defenses in this tree;
`python security/security_scan.py` re-checks the tree before every release.

## Verified test evidence (2026-11-04)

- demo1 change-gate gold tests: **5/5 PASS**; demo2 five-seat review: **26/26 PASS**
- Adversarial probes: **22/22 PASS**, and `--selfcheck` confirms every probe
  fails against its own mutant. The same harness found 10 defects on the
  pre-fix tree — evidence is kept in `review/evidence/redteam_before.json`
  (9/19 passing) next to the post-fix run
- `framework/gate_bot.py`: **6/6 checks PASS** (incl. doc-count drift and the demo2 suite); `security/security_scan.py`: **clean, 0 findings**
- MCP smoke (tools list + judge + RBAC deny): **PASS**; SSE smoke: **6/6 event types**
- TypeScript SDK: `cd lgd-engine-ts && npm run smoke` → `SMOKE OK` (exit 0) on
  Node 24.14.0, 2026-11-04. The container surface is **NOT VERIFIED** — no Docker
  on the reviewing host and no container step in CI.
- GitHub Actions: `gate` CI and `CodeQL` **green on main**; Dependabot enabled;
  branch protection active (PR required + gate status check)
- Negative controls (each one must be able to fail, and does): stdlib OpenAPI
  scan → `5/17 (text-scan only)`; injection self-test with a broken guard →
  `5/6`, exit 1; SSE smoke on an empty log → explicit empty-log error;
  README claiming 12 stages → gate check 5 FAIL
- Pre-release review: `release-prep/PRE_RELEASE_REVIEW.md` carries the red-team,
  outsider and external-AI results, including findings that are **still
  open**. Earlier revisions of this file claimed a closed 7-dimension
  review (LGD-EVAL-2026-009) with no artifact behind it; that claim was
  removed rather than restated.

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
   a `go` verdict with zero evidence refs is downgraded to `hold` (law 2 — it is
   never silently released, and never turned into a `reject` either).
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
