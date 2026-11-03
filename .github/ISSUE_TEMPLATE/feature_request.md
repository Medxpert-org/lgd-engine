---
name: Feature request
about: Propose a new judge, rule, adapter, or interface change
title: "[feat] "
labels: ["enhancement"]
---

**What problem are you trying to solve?**
A clear and concise description of the problem. E.g. "I need change
classification for [jurisdiction / domain] and no existing judge covers it."

**Proposed solution**
A clear and concise description of what you want to happen. If this is a new
domain judge, name the domain (it must map onto the 13-domain map in
`framework/`) and the 11-stage ecosystem stage.

**LGD semantics (required — no evidence, no rule)**
Every rule in this engine cites evidence. Please provide:
- Evidence source this rule would cite (precedent id / case entry /
  regulation citation):
- Expected verdict behavior for the case(s) you have in mind
  (`go` / `hold` / `reject`):
- Which of the three laws the rule enforces (有籍 Registered / 有证 Evidenced
  / 有门禁 Gated):

**Alternatives considered**
A clear and concise description of any alternative solutions or features you
considered.

**Interface-layer impact (if any)**
If your request touches the MCP server, REST/OpenAPI, SSE stream, or
container: state whether it widens or narrows the current **local-trust**
boundary. Silent network exposure will not be accepted.

**Additional context**
Add any other context, links to precedents, or screenshots here.
