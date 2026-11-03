# Skill Manifest Specification (skill.yaml) — v1.0 draft

- Status: MVP skeleton, aligned with design doc section ⑦ (unified skill manifest).
- Purpose: one declarative, machine-readable `skill.yaml` per skill, so that every AI host
  (Doubao / Qwen / WorkBuddy / Claude / OpenAI SDK) can discover, route, gate and invoke the
  exact same skill with the exact same behavior ("one input, one output").
- Zero external actions: this file is a local draft, not published.

---

## 1. Required schema

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | string, `^[a-z0-9][a-z0-9-]{1,62}$` | yes | Unique skill id, kebab-case. |
| `version` | string, semver `MAJOR.MINOR.PATCH` | yes | Skill version. |
| `description` | string (≤ 280 chars) | yes | What the skill does; one line. |
| `gate_tag` | enum: `theory-bound` \| `auxiliary` | yes | Gate tag. `theory-bound` = bound to LGD 三律 / 有籍有证有门禁 / 触点即门 judgment; these run by default whitelist. `auxiliary` = utility skill, needs explicit `skill allow <name>`. |
| `requires_llm` | bool | yes | `false` = runs fully offline (gold-testable without any LLM). `true` = needs an LLM host. |
| `permissions` | enum: `read-only` \| `suggest` \| `execute` | yes | RBAC ceiling of the skill. `read-only` may only read KB/decision store. `suggest` may open branch/PR but never merge. `execute` may run tools/write inbox but never modify core rules. |
| `entry` | string (command) | yes | Invocation command, e.g. `python -m lgd.skills.change_gate`. |
| `dependencies` | list of strings | yes | Framework deps, e.g. `["lgd.judges", "lgd.gate"]`; empty list `[]` allowed. |

## 2. Optional fields

| Field | Type | Meaning |
|---|---|---|
| `author` | string | Human-readable attribution, e.g. `Zhao, X. (Independent Researcher)`. |
| `license` | string | SPDX id, default `Apache-2.0`. |
| `inputs` | object | Declared input schema (JSON-Schema-lite), for gate validation. |
| `outputs` | object | Declared output contract, e.g. `verdict: go \| hold \| reject`. |
| `network` | bool | Whether the skill may make outbound network calls. Default `false`. |
| `signature` | string | ed25519 signature of the skill package (post-MVP; `skill.invoke` verifies before load). |

## 3. Rules

1. `permissions` is a **ceiling**, not a grant. The calling AI seat's RBAC role is intersected
   with this ceiling; the weaker wins.
2. `requires_llm: false` skills MUST be callable from CI / offline gold tests. If a skill
   cannot be run offline, it must set `requires_llm: true` explicitly.
3. `gate_tag: theory-bound` skills MUST route their verdict through `lgd.gate` aggregation;
   auxiliary skills bypass the theory gate but are still logged to audit.
4. Any missing required field or malformed value = manifest invalid = `skill.list` refuses
   to expose the skill and `gate_bot.py` check ④ goes RED.

## 4. Minimal example (see examples/)

Two reference manifests ship with this spec:
- `examples/change-gate-skill.yaml` — medical-device change-control gate (theory-bound, offline).
- `examples/touchpoint-gate-skill.yaml` — touchpoint gate annotation (theory-bound, offline).
