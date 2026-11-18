#!/usr/bin/env python3
"""mcp_server.py — minimal MCP server (stdio, line-delimited JSON-RPC 2.0).

Tools exposed:
  - list_judges     : list registered DomainJudge domains
  - judge_change    : 510(k) change-classification verdict (Judge510kChange)
  - judge_postmarket: postmarket-surveillance verdict (JudgePostmarket)
  - judge_pccp      : PCCP change-scope verdict (JudgePccpScope)
  - record_decision : append-only audit write of a signed-off verdict (reviewer only)

L2 authorization: the caller declares a role via params["role"] (default
"read-only"). Roles are resolved against ROLE_TOOLS; a role that is not declared
there is denied (fail closed), and a declared role may only reach the tools in
its set. Every allow/deny is audited into LocalMemory with the deciding rule as
the basis. No secrets are ever logged.

Run:
    python lgd_engine/mcp_server.py     # speaks JSON-RPC on stdin/stdout
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lgd_engine.gate.engine import GateEngine                # noqa: E402
from lgd_engine import __version__ as _PKG_VERSION            # noqa: E402
from lgd_engine.judges.judge_510k import Judge510kChange      # noqa: E402
from lgd_engine.judges.judge_postmarket import JudgePostmarket  # noqa: E402
from lgd_engine.judges.judge_pccp import JudgePccpScope       # noqa: E402
from lgd_engine.judges.judge_mdr import JudgeMdrSignificance   # noqa: E402
from lgd_engine.judges.judge_nmpa import JudgeNmpaChangeRegistration  # noqa: E402
from lgd_engine.memory.localmem_min import LocalMemory        # noqa: E402

READONLY_TOOLS = {"list_judges", "judge_change", "judge_postmarket", "judge_pccp",
                  "judge_mdr", "judge_nmpa"}

# The one capability that separates the two roles: recording a signed-off decision
# is an append-only audit write, not a verdict-producing read. Until 2026-11-18
# ROLE_TOOLS listed 'reviewer' with exactly the read-only set, so the table
# promised a separation it did not implement (pinned as a known limitation in
# tests/test_contract.py, now closed).
REVIEW_TOOLS = {"record_decision"}

# Role table. Declared roles are the ONLY thing that makes a tool reachable:
# before this table existed the role was read into a variable, logged in the
# audit row, quoted in the denial message — and then never consulted, so every
# caller was silently read-only and an undeclared role was indistinguishable
# from a declared one (probe D1, 2026-11-04).
DEFAULT_ROLE = "read-only"
ROLE_TOOLS = {
    "read-only": frozenset(READONLY_TOOLS),
    "reviewer": frozenset(READONLY_TOOLS | REVIEW_TOOLS),
}

TOOL_SCHEMAS = {
    "list_judges": {
        "description": "List registered DomainJudge domains.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "judge_change": {
        "description": "Run the 510(k) change-classification judge over a change ctx.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "change_type": {"type": "string"},
                "safety_impact": {"type": "string"},
                "recall_class": {"type": "string"},
                "predicate_unchanged": {"type": "boolean"},
                "source_refs": {"type": "array"},
            },
            "required": ["change_type"],
        },
    },
    "judge_postmarket": {
        "description": "Run the postmarket-surveillance judge over a ctx.",
        "inputSchema": {"type": "object", "properties": {"ctx": {"type": "object"}}},
    },
    "judge_pccp": {
        "description": ("Ask whether a change may ride an authorized PCCP "
                        "(FD&C 515C / 21 CFR 892.2055) or needs its own submission."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pccp_authorized": {"type": "boolean"},
                "change_within_pccp_scope": {"type": "boolean"},
                "affects_intended_use": {"type": "boolean"},
                "acceptance_criteria_met": {"type": "boolean"},
                "change_type": {"type": "string"},
                "evidence_sufficiency": {"type": "string"},
                "jurisdiction": {"type": "string"},
                "source_refs": {"type": "array"},
            },
        },
    },
    "judge_mdr": {
        "description": ("Ask whether a change to a CE-marked device is significant under "
                        "MDCG 2020-3 (needs notified-body assessment) or not."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "change_category": {"type": "string"},
                "affects_intended_purpose": {"type": "boolean"},
                "affects_clinical_benefit": {"type": "boolean"},
                "affects_safety_or_performance": {"type": "boolean"},
                "fsca_open": {"type": "boolean"},
                "declared_not_significant": {"type": "boolean"},
                "evidence_sufficiency": {"type": "string"},
                "jurisdiction": {"type": "string"},
                "source_refs": {"type": "array"},
            },
        },
    },
    "judge_nmpa": {
        "description": ("Ask whether a change to a China-registered device needs 变更注册 "
                        "(licence item), 备案 (registration item), or re-registration."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "has_registration_certificate": {"type": "boolean"},
                "change_fields": {"type": "array"},
                "requested_path": {"type": "string"},
                "safety_effectiveness_assessed": {"type": "boolean"},
                "technical_docs_updated": {"type": "boolean"},
                "evidence_sufficiency": {"type": "string"},
                "recall_level": {"type": "string"},
                "jurisdiction": {"type": "string"},
                "source_refs": {"type": "array"},
            },
        },
    },
    "record_decision": {
        "description": ("Record a signed-off decision into the audit log (append-only). "
                        "Requires role=reviewer."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "verdict": {"type": "string", "enum": ["go", "hold", "reject"]},
                "rationale": {"type": "string"},
                "evidence_refs": {"type": "array"},
            },
            "required": ["case_id", "verdict", "rationale"],
        },
    },
}


def build_audit() -> LocalMemory:
    return LocalMemory(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "mcp_audit.sqlite"))


def handle(recv: dict, audit: LocalMemory) -> dict:
    mid = recv.get("id")
    method = recv.get("method")
    params = recv.get("params") or {}

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "lgd-engine-mcp", "version": _PKG_VERSION},
            "capabilities": {"tools": {}},
        }}

    if method == "tools/list":
        tools = [{"name": n, **TOOL_SCHEMAS[n]} for n in
                 ("list_judges", "judge_change", "judge_postmarket", "judge_pccp",
                  "judge_mdr", "judge_nmpa", "record_decision")]
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": tools}}

    if method == "tools/call":
        name = params.get("name", "")
        raw_role = params.get("role", DEFAULT_ROLE)
        role = raw_role.strip().lower() if isinstance(raw_role, str) else ""
        args = params.get("arguments")
        if args is None:
            args = {}

        if not isinstance(args, dict):
            audit.record({
                "initiator": "mcp-server",
                "subject": f"malformed arguments rejected: tool={name!r} role={role!r}",
                "decision": "hold",
                "basis": "tools/call arguments must be a JSON object",
                "status": "vetoed",
                "evidence_refs": [],
            })
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32602,
                              "message": "invalid params: arguments must be an object"}}

        # The published schema for judge_postmarket is {"ctx": {...}}; the
        # judges take the ctx fields flat. Accept both instead of silently
        # judging an empty context (probe D3).
        if isinstance(args.get("ctx"), dict):
            args = args["ctx"]

        allowed = ROLE_TOOLS.get(role)
        if allowed is None:
            audit.record({
                "initiator": "mcp-server",
                "subject": f"undeclared role rejected: role={role!r} tool={name!r}",
                "decision": "hold",
                "basis": "L2 RBAC: role is not declared in ROLE_TOOLS (fail closed)",
                "status": "vetoed",
                "evidence_refs": [],
            })
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32003,
                              "message": f"permission denied: role={role!r} is not "
                                         f"declared; allowed roles: "
                                         f"{sorted(ROLE_TOOLS)}"}}

        if name not in allowed:
            audit.record({
                "initiator": "mcp-server",
                "subject": f"unauthorized tool call rejected: {name!r} role={role}",
                "decision": "hold",
                "basis": f"L2 RBAC: role {role!r} may call {sorted(allowed)}",
                "status": "vetoed",
                "evidence_refs": [],
            })
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32003,
                              "message": f"permission denied: {name!r} not allowed "
                                         f"for role={role}"}}

        if name == "list_judges":
            result = {"judges": [
                Judge510kChange().domain,
                JudgePostmarket().domain,
                JudgePccpScope().domain,
                JudgeMdrSignificance().domain,
                JudgeNmpaChangeRegistration().domain,
            ]}
        elif name == "judge_change":
            report = GateEngine([Judge510kChange()]).evaluate(args)
            result = {"report": report.to_dict()}
        elif name == "judge_postmarket":
            report = GateEngine([JudgePostmarket()]).evaluate(args)
            result = {"report": report.to_dict()}
        elif name == "judge_pccp":
            report = GateEngine([JudgePccpScope()]).evaluate(args)
            result = {"report": report.to_dict()}
        elif name == "judge_mdr":
            report = GateEngine([JudgeMdrSignificance()]).evaluate(args)
            result = {"report": report.to_dict()}
        elif name == "judge_nmpa":
            report = GateEngine([JudgeNmpaChangeRegistration()]).evaluate(args)
            result = {"report": report.to_dict()}
        else:  # record_decision
            verdict = args.get("verdict")
            if verdict not in ("go", "hold", "reject"):
                return {"jsonrpc": "2.0", "id": mid,
                        "error": {"code": -32602,
                                  "message": "invalid params: verdict must be one of "
                                             "go / hold / reject (a decision without a "
                                             "verdict is not a decision)"}}
            if not (args.get("case_id") or "").strip() or not (args.get("rationale") or "").strip():
                return {"jsonrpc": "2.0", "id": mid,
                        "error": {"code": -32602,
                                  "message": "invalid params: case_id and rationale are "
                                             "required — an unsigned decision cannot be "
                                             "audited"}}
            result = {"recorded": {
                "case_id": args["case_id"],
                "verdict": verdict,
                "by_role": role,
            }}

        audit.record({
            "initiator": "mcp-server",
            "subject": f"tool {name} called by role={role}",
            "decision": (result.get("report", {}).get("verdict")
                         or result.get("recorded", {}).get("verdict") or "n/a"),
            "basis": f"tools/call {name}",
            "status": "recorded" if name == "record_decision" else "executed",
            "evidence_refs": [],
        })
        return {"jsonrpc": "2.0", "id": mid, "result": {"content": [
            {"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}}

    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": f"method not found: {method}"}}


def main() -> int:
    audit = build_audit()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        recv = None
        try:
            recv = json.loads(line)
            resp = handle(recv, audit)
        except json.JSONDecodeError as exc:
            resp = {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32700, "message": f"parse error: {exc}"}}
        # JSON-RPC notifications (a parsed message with no "id", e.g.
        # notifications/initialized) must not be answered at all. Before this
        # guard the server replied -32601 "method not found" to the handshake
        # notification, which strict clients read as a protocol violation. A
        # parse error keeps recv=None and still gets its -32700 reply.
        if isinstance(recv, dict) and "id" not in recv:
            continue
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    audit.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
