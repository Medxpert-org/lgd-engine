# Pull Request

## Description
A clear and concise description of what this PR changes and why. Reference
the issue if one exists (e.g. `Closes #123`).

If this PR changes judgment semantics (a rule, a judge, a verdict), state the
evidence it rests on: precedent id / case entry / regulation citation. No
evidence citation, no merge — that is the 有证 (Evidenced) law, applied to
contributions.

## Type of change
- [ ] Rule / judge semantics change
- [ ] Bug fix (wrong verdict or failing test)
- [ ] Interface-layer change (MCP / REST / SSE / TS SDK / container)
- [ ] Documentation
- [ ] Test / CI hardening
- [ ] Other (please describe):

## Test self-proof — actually run these, then paste the real output
- [ ] `python demo1/test_demo1.py` — expect **5/5 + 6/6 PASS**
- [ ] `python demo2/test_demo2.py` — expect **26/26 PASS**
- [ ] `python framework/gate_bot.py` — expect exit **0**

Paste the actual tail of the output here:
```
<paste output>
```

If your change touches an interface layer, also check the relevant smoke:
- [ ] `python docs/validate_openapi.py` (17 checks)
- [ ] `python security/security_scan.py` (clean)
- [ ] `python lgd_engine/mcp_smoke.py`
- [ ] `python -m demo2.sse_server --port 8770 --smoke` (6 event types)

## CI expectations
This repository runs `gate` CI plus CodeQL on every pull request, with
branch protection requiring both green and reviewer approval. Confirm:
- [ ] I expect `gate` CI to pass on this branch.
- [ ] I expect CodeQL to report no new alerts.

## Local-trust impact declaration
- [ ] My change does not touch the trust boundary (MCP stdio / REST / SSE).
- [ ] My change touches it — here is exactly how it narrows, holds, or
  widens the current local-trust posture (required):

```
<declaration>
```

## Attribution statement
- [ ] I understand this code is contributed under Apache-2.0, and that this
  does **not** transfer or waive the LGD theory attribution recorded in
  `NOTICE` (the three laws / 有籍有证有门禁 / 触点即门).

By submitting this pull request, I confirm the statements above are accurate.
