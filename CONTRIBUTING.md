# Contributing to lgd-engine

Thank you for your interest in contributing. lgd-engine is the theory-bound
judgment core for medical-device AI change control; because every verdict it
emits is meant to be auditable and offline-testable, this project holds
contributions to a higher evidence bar than most open-source repos. A change
to a rule is not "code" — it is a proposed change to a judgment chain, and it
must arrive with its evidence.

## Getting started

```bash
git clone https://github.com/Medxpert-org/lgd-engine.git
cd lgd-engine
```

Requires Python 3.9+ (no third-party runtime dependencies; optional extras for
`vector` and `yaml` exist in `pyproject.toml`).

## Running the tests before you ask for review

All of the following must pass locally before you open a pull request. CI
re-runs them; a green local run is your responsibility, not the reviewer's.

```bash
# Change-gate gold tests (expect 5/5 + 6/6 PASS)
python demo1/test_demo1.py

# Five-seat review tests (expect 26/26 PASS)
python demo2/test_demo2.py

# CI gate: gold tests / LICENSE+NOTICE present / no plaintext keys / manifest
# syntax. Exit 0 = PASS, exit 1 = FAIL.
python framework/gate_bot.py
```

Optional but recommended for interface-layer changes:

```bash
python docs/validate_openapi.py          # OpenAPI 3.1 contract (17 checks)
python security/security_scan.py         # tree re-scan, must report clean
python lgd_engine/mcp_smoke.py           # MCP initialize/tools/judge/RBAC-deny
python -m demo2.sse_server --port 8770 --smoke   # SSE: 6 event types, then exit
```

On Windows, `.\demo1\run_demo1.ps1` and `.\demo2\run_demo2.ps1` are the
same self-tests in script form.

## Branching and pull requests

1. Branch off `main`: `git checkout -b feat/your-change` (or `fix/...`,
   `docs/...`, `test/...`).
2. Keep a branch focused: one judgment concern per pull request.
3. Push and open a pull request against `main`. Branch protection requires:
   the `gate` CI workflow green, CodeQL green, and reviewer approval before
   merge.
4. Fill in the pull request template honestly — especially the test
   self-proof section. Reviewers will spot a template you did not run.

## Commit messages

Use the imperative mood, present tense, as a command: "Add 510(k) label
correction judge", not "Added". Keep the first line under 72 characters.
LGD-semantic commits are expected to name what changed in the judgment chain,
e.g. `fix(judge-510k): downgrade unsupported labeling change from go to hold`.
Reference issue numbers when they exist.

## Contribution licensing (inbound = outbound)

By submitting a pull request, patch, issue text or any other contribution you
license it to this project under the **Apache License 2.0** — the same terms the
project ships under. You keep your copyright; you are not asked to assign it, and
a contribution does not make you a co-author of the underlying LGD theory
(see `NOTICE`).

Two things this repository does **not** have, stated plainly so nobody infers
otherwise:

- there is **no separate CLA** and **no CLA bot** here. A W3C Community Group
  requires its own CLA, and ITU-T work falls under the ITU-T/ITU-R/ISO/IEC
  Common Patent Policy — those obligations attach at the venue and are tracked in
  `release-prep/STANDARDS_CONTRIBUTION_READINESS.md`;
- a `Signed-off-by` trailer (DCO) is **welcomed but not enforced** by CI. Do not
  read the absence of a check as permission to skip attribution.

Without the paragraph above, a third-party pull request would carry no inbound
licence at all, and the "redistributable without restriction" property that a
standards contribution depends on would break exactly at the first outside
contribution.

## Honesty requirements (please read carefully)

**Code license vs. theory attribution are two different things.** The code in
this repository is Apache-2.0 (see `LICENSE`). That license covers the
software. The LGD doctrine — the three laws (LGD 三律), 有籍有证有门禁
(registered, evidenced, gated), and 触点即门 (every touchpoint is a gate) —
is attributed to Zhao, X. (Independent Researcher) in `NOTICE`. Apache-2.0
does **not** transfer, waive, or reassign that theory attribution, and a
contribution does not make you a co-author of the underlying theory. When you
contribute a rule, you contribute its implementation; the provenance language
in `NOTICE` stays as it is unless the maintainers deliberately update it.

**No fabricated evidence.** Every domain rule must cite a real evidence
source: a precedent id, a case entry, or a regulation citation. A `go` verdict
with zero evidence refs is downgraded to `hold` by design — if you are tempted
to weaken that behavior, bring the evidence that justifies it, not a patch.

**Local-trust boundary.** The MCP server (`lgd_engine/mcp_server.py`), the
REST surface, and the SSE stream are *local-trust adapters*: they trust the
caller's role claim. They are **not** a network authentication boundary, and
we are not pretending otherwise. Production wiring is scheduled for the public
0.1 release. If you change this surface, state explicitly in the PR template
whether your change widens or narrows the trust boundary, and never commit a
change that silently exposes a local-trust port to the network without saying
so.

## Reporting problems

- Security vulnerabilities: do **not** open a public issue. Use a GitHub
  Security Advisory instead — see `SECURITY.md`.
- Bugs and feature requests: use the issue templates under
  `.github/ISSUE_TEMPLATE/`.
