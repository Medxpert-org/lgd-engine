/**
 * lgd-engine-ts — TypeScript client skeleton (mode ⑥ of the 7 integration modes).
 *
 * STATUS: BETA SKELETON. The types below mirror docs/openapi.yaml exactly.
 * The production REST server (/v1/judge, /v1/decisions) does not exist yet;
 * this client is the frozen wire contract ready to point at it once the Beta
 * milestone wires the HTTP surface. Today the same semantics run in-process:
 *   mvp/demo1/web.py  →  POST http://127.0.0.1:8765/judge (no /v1 prefix)
 *
 * Zero runtime dependencies: Node 18+ global fetch. No npm install needed.
 */

// ---------------------------------------------------------------------------
// Types — mirror of docs/openapi.yaml components/schemas
// ---------------------------------------------------------------------------

export type Verdict = "go" | "hold" | "reject";
export type ReasonLevel = "critical" | "major" | "minor";

export interface Reason {
  rule: string;
  level: ReasonLevel;
  detail: string;
}

export interface Evidence {
  kind: string; // e.g. "fda_510k"
  ref: string;  // e.g. "K190204"
}

export interface JudgeVerdict {
  verdict: Verdict;
  reasons: Reason[];
  evidence: Evidence[];
}

export interface GateReport {
  verdict: Verdict;
  per_judge: Record<string, JudgeVerdict>;
  reasons: Reason[];
  evidence: Evidence[];
  /** Which LGD laws fired: L1-RECORDED / L2-EVIDENCED / L3-GATED. */
  law_enforcements: string[];
}

export interface ChangeContext {
  device_risk_class?: "I" | "II" | "III";
  regulatory_path?: "510k" | "pma" | "nmpa_import";
  change_type: string;
  safety_impact?: "none" | "limited_reversible" | "severe_life_threatening";
  evidence_sufficiency?: "sufficient" | "needs_supplement" | "none";
  recall_class?: "none" | "class1" | "class2" | "class3";
  requires_submission?: boolean;
  predicate_unchanged?: boolean;
  device_description?: string;
  source_refs?: string[];
  /** The engine tolerates additional context keys. */
  [key: string]: unknown;
}

export type DecisionStatus = "pending" | "executed" | "vetoed";

export interface DecisionRecord {
  id?: number;
  time: string; // ISO-8601
  initiator: string;
  subject: string;
  decision: string;
  basis: string;
  status: DecisionStatus;
  evidence_refs?: string[];
  session_id?: string;
}

export interface DecisionsQuery {
  limit?: number; // default 50, cap 500
}

// ---------------------------------------------------------------------------
// Client skeleton
// ---------------------------------------------------------------------------

export interface LgdClientOptions {
  /** Base URL of the (future) production REST service, e.g. https://api.customer.internal */
  baseUrl?: string;
  /** Bearer token (customer IdP / vault). TLS termination is assumed outside. */
  bearerToken?: string;
  /** Alternative API key (X-API-Key header). */
  apiKey?: string;
}

export class LgdEngineClient {
  readonly baseUrl: string;
  private readonly bearerToken?: string;
  private readonly apiKey?: string;

  constructor(opts: LgdClientOptions = {}) {
    this.baseUrl = (opts.baseUrl ?? "http://127.0.0.1:8765").replace(/\/$/, "");
    this.bearerToken = opts.bearerToken;
    this.apiKey = opts.apiKey;
  }

  private authHeaders(): Record<string, string> {
    const h: Record<string, string> = {};
    if (this.bearerToken) h["Authorization"] = `Bearer ${this.bearerToken}`;
    if (this.apiKey) h["X-API-Key"] = this.apiKey;
    return h;
  }

  /**
   * Submit one change-context case → GateReport verdict chain.
   * NOTE: against today's demo server the path is /judge (no /v1 prefix);
   * against the production Beta service it will be /v1/judge.
   */
  async judge(ctx: ChangeContext, path = "/v1/judge"): Promise<GateReport> {
    const res = await fetch(this.baseUrl + path, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...this.authHeaders() },
      body: JSON.stringify(ctx),
    });
    if (!res.ok) {
      throw new Error(`lgd judge failed: HTTP ${res.status}`);
    }
    return (await res.json()) as GateReport;
  }

  /** List persisted decision records (append-only audit). */
  async decisions(query: DecisionsQuery = {}, path = "/v1/decisions"): Promise<DecisionRecord[]> {
    const qs = new URLSearchParams();
    if (query.limit !== undefined) qs.set("limit", String(query.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    const res = await fetch(this.baseUrl + path + suffix, { headers: this.authHeaders() });
    if (!res.ok) {
      throw new Error(`lgd decisions failed: HTTP ${res.status}`);
    }
    return (await res.json()) as DecisionRecord[];
  }
}

export default LgdEngineClient;
