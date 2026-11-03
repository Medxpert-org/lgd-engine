# lgd-engine-ts — TypeScript SDK skeleton (mode ⑥)

**Status: Beta skeleton (frozen contract).** The types and client below mirror
[`docs/openapi.yaml`](../docs/openapi.yaml) exactly. The production REST
service (`/v1/judge`, `/v1/decisions`) does not exist yet — this SDK is ready
to point at it once the Beta milestone wires the HTTP surface.

## What is real today

- Node **v22.23.2** present on this machine (probe 2026-11-03).
- `test/smoke.mjs` runs the *same* URL/header/query logic as `src/index.ts`
  against a local mock server — `npm run smoke` passed under Node 22.
- **Not measured here:** `tsc` typecheck — no `tsc` on PATH and no package
  install allowed (zero-network, zero-third-party discipline). `src/index.ts`
  is hand-checked against the OpenAPI contract; typecheck CI lands later.

## Usage (once the Beta REST service exists)

```ts
import { LgdEngineClient } from "lgd-engine-ts";

const client = new LgdEngineClient({
  baseUrl: "https://api.your-internal.com",   // TLS-terminated proxy
  bearerToken: process.env.LGD_TOKEN,         // injected from vault
});

const report = await client.judge({
  change_type: "material_nonconforming",
  device_risk_class: "II",
  safety_impact: "none",
  predicate_unchanged: true,
});
// report.verdict: "go" | "hold" | "reject"
// report.reasons / report.per_judge / report.law_enforcements

const audit = await client.decisions({ limit: 50 });
```

## Design notes

- Zero runtime dependencies: relies on Node 18+ global `fetch`.
- Demo-mode override: against today's `python -m demo1.web` server
  (`http://127.0.0.1:8765`), call `judge(ctx, "/judge")` — identical body and
  response shape, only the path differs.
- Security: tokens come from env/vault, never from code; TLS termination is
  expected outside the client.
