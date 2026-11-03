---
name: Bug report
about: Report a wrong verdict, a failing test, or broken behavior
title: "[bug] "
labels: ["bug"]
---

**Describe the bug**
A clear and concise description of what the bug is. If lgd-engine emitted a
verdict (go / hold / reject) that you believe is wrong, quote the verdict.

**LGD change context (fill this in — it drives triage)**
- Change taxonomy token (e.g. `label_correction`, `supplier_swap`):
- Jurisdiction (e.g. FDA, NMPA, MDR):
- Device risk class:
- Expected gate level / verdict (`go` / `hold` / `reject`):
- Evidence refs the rule should have cited (precedent id / case entry /
  regulation citation):

**To reproduce**
Steps to reproduce the behavior, e.g.:
1. Run `python -m demo1.change_gate --case ...`
2. See wrong verdict `...`

**Expected behavior**
A clear and concise description of what you expected to happen, and which law
(有籍 Registered / 有证 Evidenced / 有门禁 Gated) you believe was violated.

**Environment (please complete):**
- OS:
- Python version (`python --version`):
- How you ran lgd-engine (clone / `python -m ...` / MCP client):
- Commit hash (`git rev-parse HEAD`):

**Logs / output**
Paste the relevant command output here, including failure messages:
```

```

**Additional context**
Add any other context about the problem here.
