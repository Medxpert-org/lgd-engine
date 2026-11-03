# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

The package `lgd-engine` is **not yet published**. Everything below is merged
into `main` ahead of the public 0.1 release.

### Added

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
- README explains 11 stages / 13 domains / 14 links as three different
  scopes rather than leaving three numbers unexplained.
- README and `demo2/sse_server.py` document the SSE smoke precondition (the
  log must contain both a pass and a hold path); on failure the smoke names
  the missing types and the exact commands that generate them.
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
