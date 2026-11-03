// Plain-JS runtime smoke for the TS skeleton logic (no tsc available, no install allowed).
// It replicates the exact URL/header/query-building logic from src/index.ts
// against a local mock server, so we know the client *logic* runs on Node 22.
import http from "node:http";
import assert from "node:assert/strict";

let seen = null;

const mock = http.createServer((req, res) => {
  seen = { method: req.method, url: req.url, auth: req.headers.authorization, apikey: req.headers["x-api-key"] };
  if (req.url === "/v1/judge") {
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({
      verdict: "hold",
      per_judge: { "med-device-510k-change": { verdict: "hold", reasons: [], evidence: [] } },
      reasons: [{ rule: "R", level: "major", detail: "d" }],
      evidence: [],
      law_enforcements: [],
    }));
  } else if (req.url.startsWith("/v1/decisions")) {
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify([{ id: 1, time: "2026-11-03T00:00:00+00:00", initiator: "mcp-server", subject: "s", decision: "PASS", basis: "b", status: "executed" }]));
  } else {
    res.statusCode = 404;
    res.end("nope");
  }
});

await new Promise((r) => mock.listen(0, "127.0.0.1", r));
const port = mock.address().port;

// --- replicate LgdEngineClient logic from src/index.ts ----------------------
function build({ baseUrl = `http://127.0.0.1:${port}`, bearerToken, apiKey } = {}) {
  const b = baseUrl.replace(/\/$/, "");
  const authHeaders = () => {
    const h = {};
    if (bearerToken) h["Authorization"] = `Bearer ${bearerToken}`;
    if (apiKey) h["X-API-Key"] = apiKey;
    return h;
  };
  return {
    async judge(ctx) {
      const res = await fetch(b + "/v1/judge", { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(ctx) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    async decisions(query = {}) {
      const qs = new URLSearchParams();
      if (query.limit !== undefined) qs.set("limit", String(query.limit));
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      const res = await fetch(b + "/v1/decisions" + suffix, { headers: authHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
  };
}

// --- assertions -------------------------------------------------------------
const client = build({ bearerToken: "tok-123", apiKey: "key-456" });

const report = await client.judge({ change_type: "material_nonconforming" });
assert.equal(report.verdict, "hold");
assert.ok(seen.method === "POST" && seen.url === "/v1/judge", "judge POSTs to /v1/judge");
assert.equal(seen.auth, "Bearer tok-123", "bearer header attached");
assert.equal(seen.apikey, "key-456", "X-API-Key header attached");

const rows = await client.decisions({ limit: 25 });
assert.equal(rows.length, 1);
assert.ok(seen.url === "/v1/decisions?limit=25", `limit query string built, got ${seen.url}`);

await new Promise((r) => mock.close(r));
console.log("SMOKE OK: judge() POST+auth+GateReport parse; decisions() limit query + parse");
