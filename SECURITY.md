# Security Policy

## Reporting a vulnerability

**Please do not open a public GitHub issue for security problems.**

Instead, report a vulnerability through a private **GitHub Security Advisory**:

> https://github.com/Medxpert-org/lgd-engine/security/advisories/new

Include as much detail as you can: a description of the issue, the affected
component and version, reproduction steps, and any suggested impact. Reports
received through this channel are private to the maintainers until triaged.

If you cannot use GitHub Security Advisories for any reason, open a blank
private issue on the repository; do not publish exploit details publicly
before we have had a chance to respond.

## What is in scope

Security review is requested for:

- the judgment core (`lgd_engine/gate/`, `lgd_engine/theory/`),
- domain judges (`lgd_engine/judges/`),
- the MCP server (`lgd_engine/mcp_server.py`) and its smoke harness,
- the REST/OpenAPI surface (`docs/openapi.yaml`, `docs/validate_openapi.py`),
- the SSE event stream (`demo2/sse_server.py`),
- the TypeScript SDK skeleton (`lgd-engine-ts/`),
- the container definition (`Dockerfile`, `docker-compose.yml`), and
- declared dependencies in `pyproject.toml` (Dependabot enabled).

## Known boundary — please read before reporting

The MCP server, the REST surface, and the SSE stream are **local-trust
adapters**. They trust the caller's role claim and bind locally (stdio /
`127.0.0.1`). They are **not** a network authentication boundary, and this is a
deliberate, documented state of the 0.1 pre-release, not a hidden defect.

- A report saying "the local MCP server does not authenticate network
  callers" is **not** a new finding — it is already disclosed in the README
  and in `CONTRIBUTING.md`. Production wiring (network-facing endpoints with
  real authentication) is scheduled for the public 0.1 release.
- A report saying "a local user can claim a higher role than they hold" is
  also expected: the server trusts the local caller. Only treat it as a
  vulnerability if a change you observed *widens* this boundary, e.g. a port
  that started binding to `0.0.0.0`, or a server that began reading secrets
  from untrusted input.

## Response expectations (conservative)

We commit to **best-effort** handling, not to fixed response-time numbers:

- We will acknowledge receipt and begin triaging privately.
- We will investigate and communicate a remediation plan or a documented
  "won't fix" rationale through the advisory.
- We will coordinate any public disclosure so that a fix — or an
  agreed workaround — lands first, and the CHANGELOG / release notes record
  the issue honestly.

We are a small maintainer team, so response times vary; please do not assume
silence means acceptance.

## Out of scope

- Reports against third-party services this project merely references
  (e.g. Claude Desktop, Cursor) — please report those to their vendors.
- Social engineering of maintainers.
- Issues that only affect unmodified builds run on a machine the attacker
  already controls with full privileges.
