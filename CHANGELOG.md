# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

The package `lgd-engine` is **not yet published**. Everything below is merged
into `main` ahead of the public 0.1 release.

### Added

- `review/redteam_probe.py` — 22 adversarial probes over the real judges, the
  MCP surface and the CLI, testing properties rather than examples: verdict
  monotonicity along every risk axis, "unknown is never a go" for every
  enumerated field, law 2 reachability, MCP role resolution, the documented
  `{ctx: {...}}` wrapper, exit-code semantics and contract/code lockstep.
  `--selfcheck` runs every probe against a deliberately broken mutant and
  requires it to fail there; a probe that survives its own mutant is reported
  VACUOUS and fails the run. The harness is wired into the pre-release review
  as check 9 `redteam`.
- `review/pre_release_review.py` — the twelve-check pre-release gate, each check
  paired with a mutant that must make it fail (`--selftest`). `links`, `outsider`,
  `docs-claims`, `parity`, `relative-links`, `citation`, `license`, `legal`,
  `public`, `machine`, `redteam`. It exits non-zero on any finding that is not a
  `pass`, and never records `BLOCKED` (a host it could not reach) as a pass.
- `parity` distinguishes two facts that were previously one number:
  `parity-pushed` (can a stranger fetch exactly the commit we reviewed?) and
  `parity-sha` (does the default branch carry it?). An unpushed commit and an
  unmerged branch call for different actions, so they are different findings.
- `docs-claims` now re-counts every "N probes" claim in `README.md`, `llms.txt`
  and `CHANGELOG.md` against the `@probe` registrations in the harness. This
  entry's own predecessor said "twenty probes" for two commits after the harness
  had 22 — a stale count no gate was watching. (The check is deliberately literal:
  it cannot tell a claim from a quotation of an old one, so quoting is spelled out.)
- `gate_bot.py` check 5 `readme-counts`: the README's `**N stages**` and
  `**N domains**` claims are re-counted against the numbered rows in
  `framework/ecosystem-map.md` and `framework/13domains-mapping.md`.
  A documentation claim that no file backs is a claim, not a fact; the
  gate now fails when the two drift apart.
- `llms.txt` at the repository root — LLM/agent-friendly entry point per the
  llms.txt convention, covering the three laws, core interface, run
  instructions, and verified test evidence.
- MCP client configuration examples for local-trust use (Claude Desktop
  `claude_desktop_config.json` and Cursor `.cursor/mcp.json`), both invoking
  `python -m lgd_engine.mcp_server`, with platform notes and the local-trust
  boundary stated inline.
- `lgd-engine-mcp` console entry point in `pyproject.toml` (equivalent to
  `python -m lgd_engine.mcp_server`), alongside the existing `lgd-gate` entry.
- Cursor plugin manifest wiring for the local-trust MCP integration.
- PEP 621 metadata fixes in `pyproject.toml` (declarative `[project]` table,
  `license = { text = "Apache-2.0" }`, package discovery via
  `[tool.setuptools.packages.find]`).

### Fixed

- **The review self-test was slow enough to be skipped** (R21): `--selftest` spent
  the release path's `4 × 30 s` retry budget proving that a deliberately dead URL
  is dead — 3 m 22 s, longer than the wrapper running it. Its own mutants now use
  `1 × 8 s`, because the self-test asks "does this check detect a defect?", not
  "does it tolerate a flaky upstream?": 49 s, same mutants, same verdict.
- **`--db` took any path** (R18): the demo CLI handed `--db` straight to SQLite,
  which created parent directories wherever it was pointed and — on an existing
  non-database file — died with a traceback and exit 1 instead of a usage error.
  It now rejects an empty value and a non-SQLite target with exit **64**, and
  always prints the resolved path it will write to. Probe `E3`.
- **`lgd-gate --all` was documented but not implemented** (R19): the console entry
  had no `--all`, so the documented command errored out. Implemented as
  `--all CASES_DIR` with a summary line and `64` on usage errors. Probe `E4`.
- **Inverted evidence axis**: `evidence_sufficiency="none"` — the worst value —
  returned `go` while `"needs_supplement"` held. `R-MAJ-03` now covers both.
- **Predicate inversion**: `function_config_change` with
  `predicate_unchanged=false` (the worse direction, the equivalence basis is
  gone) scored better than `true`. New `R-MAJ-08-predicate-changed`.
- **A Class 2 recall only held for one change type**: `R-MAJ-02` required
  `maintenance_execution`, so a `design_defect` riding a Class 2 recall exited
  `0` (go). New `R-MAJ-07-class2-recall-field-correction`.
- **The postmarket "evidenced" law was dead code**: the branch that recorded
  `L2-EVIDENCED` sat below a line that had already downgraded a zero-evidence
  `go` to `hold`, so the law never fired and never appeared in the reason chain.
  Restructured so it is reachable, and pinned by probe C2.
- **Unknown enumerated values rode out as `go`** — recall class, cause type,
  harm severity, distribution scope, safety impact, evidence sufficiency,
  regulatory path. Fixed as a class in both judges: an unknown value holds with
  `R-MAJ-06-unknown-<field>` / `PM-MAJ-06-unknown-<field>`.
- **A rule predicate that raised was swallowed** in the postmarket judge
  (`except: pass`), i.e. fail open. A predicate error is now a hold signal.
- **MCP `role` was decorative**: it was read, logged, quoted in denial
  messages, and never consulted, so an undeclared role behaved exactly like a
  declared one. Now a declared `ROLE_TOOLS` table, failing closed.
- **The documented `{ctx: {...}}` wrapper was ignored**, so a client following
  the published schema judged an empty context; and non-object `arguments` were
  judged instead of rejected. Both now return a proper JSON-RPC error or the
  same report as flat arguments.
- **Published contract drifted from the code**: `change_type` enum lacked
  `supplier_substitution`, `source_refs` was typed `array of string` while the
  judges require `{kind, ref}` objects (a contract-conforming client could never
  satisfy law 2), `errors` was undocumented, `jurisdiction` and
  `equivalence_declared` were missing, six `mvp/` paths did not exist, and the
  response example named a domain and a rule that do not exist. All corrected;
  `docs/validate_openapi.py` now checks enum coverage and the ref shape (20/20).
- **The review counted a blocked vantage as a failure**, so a proxy outage read
  as "our repository is broken". Failures and blocked vantages are now counted
  separately and a network control URL distinguishes the two.
- **Fail-open on an unclassified change**: an unknown or missing `change_type`
  returned `go` with zero reasons, and a blank `{"kind": "", "ref": ""}` counted
  as evidence. Unknown now yields `hold` with `R-MAJ-06`; blank refs are dropped
  (S7 red team R1, three invariants in `demo1/test_demo1.py`).
- **A veto could be softened**: a major rule overwrote `reject` with `hold`, so a
  Class 1 recall reported `per_judge: HOLD` while the aggregate said `REJECT`.
  Major rules may escalate, never soften (R2).
- **A broken tool looked like a verdict**: a judge exception printed `REJECT` and
  exited `2`. The report now carries `errors`, the CLI exits `3`, usage errors
  exit `64`; a real REJECT still exits 2 (R3).
- `gate_bot.py` hardening: one canonical self-test path (a shadow
  `demo1/selftest.py` fails the gate), the gold test must report
  `N/N cases; N/N invariants`, the stdlib YAML fallback refuses unbalanced
  collections, list-valued `entry` traversal is caught, and the secret patterns
  cover AWS secret keys, password assignments and JWTs (R4–R7).
- A malformed manifest now produces a clean `[FAIL]` instead of a traceback.
- `gate_bot.py` gained a sixth check (`demo2` suite) and check 5 now compares the
  documented gate count across README, `llms.txt` and `release-prep/README.md`
  instead of README alone (R8).
- CI now runs what the docs claimed was "enforced in CI": OpenAPI validation,
  the injection/security self-tests and the SSE smoke (R11).

### Changed

- `docs/validate_openapi.py` reports its mode instead of an unqualified pass:
  a stdlib-only install runs the 5 substring checks and prints an explicit
  warning that 12 structural checks were skipped; the summary line reads
  `5/17 (text-scan only)` vs `17/17`. The README says the same where it used
  to claim "17/17 checks, stdlib".
- `demo1.change_gate` exit-code semantics are now stated where people look:
  Quickstart in the README, the module docstring, and a `[exit code]` line in
  the CLI output. Single-case exit code is the verdict (0/1/2) by design, so
  a correct REJECT exits 2; `--all` exits 0 only when every case matches.
- README links the rest of the stack — theory repository, doctrine DOIs
  (concept + v1.7.0), portal, silent-failure catalog, uibc-core — and the
  repository Homepage now points at the portal.
- README states the two counts this repository can source — 11 stages
  (`framework/ecosystem-map.md`, 11 numbered rows) and 13 domains
  (`framework/13domains-mapping.md`) — and labels the 14-link ecosystem
  caliber as **external**: it is not defined here and is not re-listed,
  because an earlier revision of this section asserted 14 without a
  source while the repository's own map said 11.
- README and `demo2/sse_server.py` document the SSE smoke precondition (the
  log must contain both a pass and a hold path); on failure the smoke names
  the missing types and the exact commands that generate them.
- `demo2/sse_server.py` stops printing a traceback when a client simply hangs
  up: an abandoned SSE stream raises `ConnectionResetError` /
  `ConnectionAbortedError` (Windows 10054 / 10053), which socketserver's
  default handler rendered as a server crash while the smoke still
  reported `6/6`. Those three connection-teardown types are now silent;
  every other exception still reaches the default handler.
- README separates the theory home from the engine home: theory, domain
  papers and standards participation (ITU FG-TIDA, W3C) are stated as
  maintained in `lgd-theory`; this repository implements the rules instead
  of tracking those threads itself (S6 review, positioning fix, option i).

### Fixed

- `security/prompt_injection_defense.py` self-test now asserts every
  expectation and prints `[summary] N/N checks passed`, exiting 1 on any
  failure. Previously it printed no summary and always exited 0, so CI could
  not detect a regression in the guards.

## [0.1.0] - unreleased

Planned first public release. Contents to be promoted from
`[Unreleased]` at release time, plus:

- Network-facing wiring for the interface layer (authentication for the MCP
  streamable-HTTP endpoint and REST surface), replacing the local-trust-only
  posture.
- Publication of the `lgd-engine` wheel to the package index.
- Finalization of citation metadata (preprint venue / DataCite record) —
  until then the citation in the README and `CITATION.cff` remains a
  placeholder.

[Unreleased]: https://github.com/Medxpert-org/lgd-engine/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Medxpert-org/lgd-engine/releases/tag/v0.1.0
