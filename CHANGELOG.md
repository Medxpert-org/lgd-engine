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
