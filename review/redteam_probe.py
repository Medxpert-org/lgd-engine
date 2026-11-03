#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adversarial probe harness for the LGD gate core.

Why this file exists
--------------------
The pre-release review has to stand behind two claims that a written checklist
cannot support:

  1. "the gate fails closed" — an unknown, missing or blank input must never
     produce a `go`.
  2. "a worse input never yields a better verdict" — the verdict lattice
     go < hold < reject must be monotone along every risk axis.

Both claims are *properties*, so they are tested as properties: a probe is
declared here, run against the real judges, and the harness records evidence.
Nothing in this file restates a rule table (single source: the judges).

The load-bearing part is `--selfcheck`. Every probe declares a `mutant` — a
deliberately broken stand-in for the component under test. `--selfcheck` runs
the whole suite against that mutant and asserts the probe FAILS. A probe that
still passes against a yes-man implementation is measuring nothing, and is
reported as VACUOUS (a hard failure). This is the negative control the hard
rules ask for: no negative control, no evidence.

Usage
-----
    python review/redteam_probe.py            # run probes, exit 1 on any FAIL
    python review/redteam_probe.py --selfcheck  # prove every probe can fail
    python review/redteam_probe.py --json out.json

Exit codes: 0 all probes pass, 1 any probe/vacuity failure, 2 harness error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Callable, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SEVERITY = {"go": 0, "hold": 1, "reject": 2}   # the verdict lattice


# ---------------------------------------------------------------------------
# Component access (the only place that imports the product)
# ---------------------------------------------------------------------------

class RealEnv:
    """The product under test. Probe functions only ever see this interface."""

    def __init__(self) -> None:
        from lgd_engine.judges.judge_510k import Judge510kChange
        from lgd_engine.judges.judge_postmarket import JudgePostmarket
        self._j510 = Judge510kChange()
        self._jpm = JudgePostmarket()

    def judge510(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return self._j510.evaluate(ctx)

    def judge_pm(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return self._jpm.evaluate(ctx)

    def mcp(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call the MCP tools/call path in-process with a throwaway audit DB."""
        from lgd_engine import mcp_server
        from lgd_engine.memory.localmem_min import LocalMemory
        tmp = tempfile.mkdtemp(prefix="probe-mcp-")
        mem = LocalMemory(os.path.join(tmp, "audit.sqlite"))
        try:
            return mcp_server.handle(
                {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params},
                mem,
            )
        finally:
            try:
                mem.close()
            except Exception:
                pass

    def openapi_text(self) -> str:
        with open(os.path.join(ROOT, "docs", "openapi.yaml"), "r", encoding="utf-8") as f:
            return f.read()

    def known_change_types(self) -> set:
        from lgd_engine.judges.judge_510k import KNOWN_CHANGE_TYPES
        return set(KNOWN_CHANGE_TYPES)

    def engine_with_raising_judge(self) -> Dict[str, Any]:
        """A judge that raises must surface in report.errors, not be swallowed."""
        from lgd_engine.gate.engine import GateEngine

        class Boom:
            domain = "boom"

            def evaluate(self, ctx):
                raise RuntimeError("judge exploded")

        return GateEngine([Boom()]).evaluate({"change_type": "design_defect"}).to_dict()

    def cli_rc(self, case_path: str, extra_args: List[str] | None = None) -> int:
        argv = [sys.executable, os.path.join(ROOT, "demo1", "change_gate.py")]
        argv += extra_args if extra_args is not None else ["--case", case_path]
        return subprocess.run(argv, capture_output=True, text=True,
                              timeout=120).returncode


# ---------------------------------------------------------------------------
# Mutants — deliberately broken implementations used as negative controls
# ---------------------------------------------------------------------------

class YesManEnv(RealEnv):
    """Everything is fine. Any probe that still passes here measures nothing."""

    def judge510(self, ctx):  # noqa: D102
        return {"verdict": "go", "reasons": [], "evidence": [{"kind": "x", "ref": "y"}]}

    def judge_pm(self, ctx):  # noqa: D102
        return {"verdict": "go", "reasons": [], "evidence": [{"kind": "x", "ref": "y"}]}

    def mcp(self, params):  # noqa: D102
        return {"jsonrpc": "2.0", "id": 1, "result": {"content": [
            {"type": "text", "text": "{}"}]}}

    def openapi_text(self):  # noqa: D102
        return "openapi: 3.1.0\ninfo:\n  title: t\npaths: {}\ncomponents:\n  schemas: {}\n"

    def engine_with_raising_judge(self):  # noqa: D102
        # The defect: a judge exception is swallowed and reported as a clean go.
        return {"verdict": "go", "per_judge": {}, "reasons": [], "evidence": [],
                "law_enforcements": [], "errors": []}

    def cli_rc(self, case_path, extra_args=None):  # noqa: D102
        return 0          # the defect: every case exits 0, the verdict is lost


class InverterEnv(RealEnv):
    """Worse input yields a better verdict — the defect A1 exists to catch."""

    _INV = {"go": "reject", "hold": "hold", "reject": "go"}

    def judge510(self, ctx):  # noqa: D102
        out = dict(super().judge510(ctx))
        out["verdict"] = self._INV.get(out.get("verdict"), "go")
        return out


class NaiveMCPEnv(RealEnv):
    """Ignores the documented {ctx: ...} wrapper — the defect D3 exists to catch."""

    def mcp(self, params):  # noqa: D102
        args = params.get("arguments") or {}
        return {"jsonrpc": "2.0", "id": 1, "result": {"content": [
            {"type": "text", "text": json.dumps(sorted(args), ensure_ascii=False)}]}}


class DenyAllEnv(RealEnv):
    """MCP denies every call, including the ones that must be allowed."""

    def mcp(self, params):  # noqa: D102
        return {"jsonrpc": "2.0", "id": 1,
                "error": {"code": -32003, "message": "denied"}}


class SoftenerEnv(RealEnv):
    """A veto that gets softened to hold — the exact defect class found in S7."""

    def judge510(self, ctx):  # noqa: D102
        out = super().judge510(ctx)
        if out.get("verdict") == "reject":
            out = dict(out, verdict="hold")
        return out


MUTANTS: Dict[str, Callable[[], RealEnv]] = {
    "yesman": YesManEnv,
    "inverter": InverterEnv,
    "naive-mcp": NaiveMCPEnv,
    "denyall": DenyAllEnv,
    "softener": SoftenerEnv,
}


# ---------------------------------------------------------------------------
# Probe registry
# ---------------------------------------------------------------------------

PROBES: List[Dict[str, Any]] = []


def probe(pid: str, family: str, mutant: str, desc: str):
    def deco(fn):
        PROBES.append({"id": pid, "family": family, "mutant": mutant,
                       "desc": desc, "fn": fn})
        return fn
    return deco


def _sev(v: str) -> int:
    return SEVERITY.get(v, -1)


def _rule_ids(out: Dict[str, Any]) -> List[str]:
    return [r.get("rule", "") for r in out.get("reasons", []) or []]


# --- A. 510(k) monotonicity -------------------------------------------------

_AXES = {
    "recall_class": ["none", "class3", "class2", "class1"],
    "safety_impact": ["none", "limited_reversible", "severe_life_threatening"],
    "evidence_sufficiency": ["sufficient", "needs_supplement", "none"],
    "requires_submission": [False, True],
}

_BASE_510 = {
    "device_risk_class": "II",
    "regulatory_path": "510k",
    "change_type": "design_defect",
    "safety_impact": "none",
    "evidence_sufficiency": "sufficient",
    "recall_class": "none",
    "requires_submission": False,
    "predicate_unchanged": True,
    "jurisdiction": "FDA",
    "source_refs": [{"kind": "fda_510k", "ref": "K190204"}],
}


@probe("A1", "monotonicity", "inverter",
       "each 510(k) risk axis is monotone: a worse value never yields a better verdict")
def p_monotone_510(env) -> tuple:
    bad = []
    for axis, values in _AXES.items():
        prev = None
        for v in values:
            ctx = dict(_BASE_510, **{axis: v})
            out = env.judge510(ctx)
            cur = _sev(out.get("verdict"))
            if prev is not None and cur < prev:
                bad.append(f"{axis}={v!r} dropped {prev}->{cur}")
            prev = cur if prev is None else max(prev, cur)
    return (not bad), "; ".join(bad) or "monotone on all four axes"


@probe("A2", "monotonicity", "yesman",
       "a Class 1 recall stays reject across every combination of the other axes")
def p_veto_survives_grid(env) -> tuple:
    bad = []
    grid = [(ct, si, ju) for ct in ("label_correction", "design_defect",
                                    "supplier_substitution")
            for si in ("none", "severe_life_threatening")
            for ju in ("FDA", "NMPA")]
    for ct, si, ju in grid:
        ctx = dict(_BASE_510, change_type=ct, safety_impact=si,
                   jurisdiction=ju, recall_class="class1")
        v = env.judge510(ctx).get("verdict")
        if v != "reject":
            bad.append(f"{ct}/{si}/{ju} -> {v}")
    return (not bad), "; ".join(bad) or f"reject across {len(grid)} combinations"


# --- B. 510(k) fail-closed ---------------------------------------------------

@probe("B1", "fail-closed", "yesman",
       "unknown change_type is never a go (unknown is not a safe default)")
def p_unknown_ct(env) -> tuple:
    ctx = dict(_BASE_510, change_type="quantum_surgery_mode")
    out = env.judge510(ctx)
    return (_sev(out.get("verdict")) >= 1), f"verdict={out.get('verdict')}"


@probe("B2", "fail-closed", "yesman",
       "missing change_type is never a go")
def p_missing_ct(env) -> tuple:
    ctx = dict(_BASE_510)
    ctx.pop("change_type")
    out = env.judge510(ctx)
    return (_sev(out.get("verdict")) >= 1), f"verdict={out.get('verdict')}"


@probe("B3", "fail-closed", "yesman",
       "blank evidence refs do not satisfy law 2 (no evidence = hold, not go)")
def p_blank_refs(env) -> tuple:
    ctx = dict(_BASE_510,
               source_refs=[{"kind": "", "ref": ""}, {"kind": "  ", "ref": "   "}])
    out = env.judge510(ctx)
    return (_sev(out.get("verdict")) >= 1), (
        f"verdict={out.get('verdict')} evidence={len(out.get('evidence') or [])}")


@probe("B4", "fail-closed", "yesman",
       "unknown jurisdiction is never a go")
def p_unknown_jur(env) -> tuple:
    ctx = dict(_BASE_510, jurisdiction="EU-MDR")
    out = env.judge510(ctx)
    return (_sev(out.get("verdict")) >= 1), f"verdict={out.get('verdict')}"


@probe("B5", "fail-closed", "softener",
       "a supplier substitution without equivalence evidence cannot soften a veto")
def p_no_softening(env) -> tuple:
    ctx = dict(_BASE_510, change_type="supplier_substitution",
               equivalence_declared=False, recall_class="class1")
    out = env.judge510(ctx)
    return (out.get("verdict") == "reject"), f"verdict={out.get('verdict')}"


# --- C. postmarket judge -----------------------------------------------------

_BASE_PM = {
    "recall_class": "none",
    "fda_cause_type": "other",
    "harm_severity": "no_harm",
    "distribution_scope": "limited_local",
    "event_report_count": 0,
    "marketing_without_license": False,
    "source_refs": [{"kind": "fda_maude", "ref": "MAUDE-2026-0001"}],
}


@probe("C1", "fail-closed", "yesman",
       "postmarket Class 1 recall is reject")
def p_pm_class1(env) -> tuple:
    out = env.judge_pm(dict(_BASE_PM, recall_class="class1"))
    return (out.get("verdict") == "reject"), f"verdict={out.get('verdict')}"


@probe("C2", "reachability", "yesman",
       "law 2 is reachable in the postmarket judge: zero evidence must produce "
       "verdict=hold AND an L2-EVIDENCED reason on record")
def p_pm_l2_reachable(env) -> tuple:
    ctx = dict(_BASE_PM, source_refs=[])
    out = env.judge_pm(ctx)
    ok = (out.get("verdict") == "hold") and ("L2-EVIDENCED" in _rule_ids(out))
    return ok, f"verdict={out.get('verdict')} rules={_rule_ids(out)}"


@probe("C3", "fail-closed", "yesman",
       "postmarket judgement with an all-blank evidence package is never a go")
def p_pm_blank_refs(env) -> tuple:
    ctx = dict(_BASE_PM, source_refs=[{"kind": "", "ref": ""}])
    out = env.judge_pm(ctx)
    return (_sev(out.get("verdict")) >= 1), (
        f"verdict={out.get('verdict')} evidence={len(out.get('evidence') or [])}")


@probe("C4", "fail-closed", "yesman",
       "unknown postmarket recall_class / cause type is never a go")
def p_pm_unknown_values(env) -> tuple:
    bad = []
    for field, value in (("recall_class", "class9"),
                         ("fda_cause_type", "alien_interference"),
                         ("harm_severity", "mildly_inconvenient")):
        out = env.judge_pm(dict(_BASE_PM, **{field: value}))
        if _sev(out.get("verdict")) < 1:
            bad.append(f"{field}={value} -> {out.get('verdict')}")
    return (not bad), "; ".join(bad) or "all three unknowns held"


@probe("C5", "fail-closed", "yesman",
       "a rule predicate that raises (unparseable event_report_count) is a hold "
       "signal, not a silently swallowed pass")
def p_pm_predicate_raise(env) -> tuple:
    out = env.judge_pm(dict(_BASE_PM, event_report_count="not-a-number"))
    return (_sev(out.get("verdict")) >= 1), f"verdict={out.get('verdict')}"


# --- D. MCP authorization ----------------------------------------------------

@probe("D1", "authorization", "yesman",
       "an undeclared MCP role is denied (role is declared, not decorative)")
def p_mcp_unknown_role(env) -> tuple:
    out = env.mcp({"name": "judge_change", "role": "auditor",
                   "arguments": dict(_BASE_510)})
    return ("error" in out), f"keys={sorted(out)}"


@probe("D2", "authorization", "denyall",
       "the declared read-only role can still call a read-only tool")
def p_mcp_readonly_allowed(env) -> tuple:
    out = env.mcp({"name": "judge_change", "role": "read-only",
                   "arguments": dict(_BASE_510)})
    return ("result" in out), f"keys={sorted(out)}"


@probe("D3", "contract", "naive-mcp",
       "the documented {ctx: {...}} wrapper for judge_postmarket behaves the same "
       "as flat arguments")
def p_mcp_ctx_wrapper(env) -> tuple:
    flat = env.mcp({"name": "judge_postmarket", "role": "read-only",
                    "arguments": dict(_BASE_PM, recall_class="class1")})
    wrap = env.mcp({"name": "judge_postmarket", "role": "read-only",
                    "arguments": {"ctx": dict(_BASE_PM, recall_class="class1")}})
    if "result" not in flat or "result" not in wrap:
        return False, f"flat={sorted(flat)} wrap={sorted(wrap)}"
    a = flat["result"]["content"][0]["text"]
    b = wrap["result"]["content"][0]["text"]
    return (a == b), "wrapped and flat arguments produce the same GateReport"


@probe("D4", "robustness", "yesman",
       "non-object arguments are rejected with a JSON-RPC error, not a traceback")
def p_mcp_bad_args(env) -> tuple:
    try:
        out = env.mcp({"name": "judge_change", "role": "read-only", "arguments": 5})
    except Exception as exc:                      # a crash is the finding
        return False, f"raised {type(exc).__name__}: {exc}"
    return ("error" in out), f"keys={sorted(out)}"


# --- E. engine / CLI surface -------------------------------------------------

@probe("E1", "regression", "yesman",
       "a judge that raises is reported in report.errors and fails safe to reject")
def p_engine_error(env) -> tuple:
    d = env.engine_with_raising_judge()
    ok = (d.get("verdict") == "reject") and bool(d.get("errors"))
    return ok, f"verdict={d.get('verdict')} errors={d.get('errors')}"


@probe("E2", "exit-code", "yesman",
       "CLI exit codes carry the verdict: 0=go 1=hold 2=reject 64=usage")
def p_exit_codes(env) -> tuple:
    cases = [
        ({"change_type": "label_correction", "safety_impact": "none",
          "recall_class": "none", "source_refs": [{"kind": "sop", "ref": "SOP-11"}]}, 0),
        ({"change_type": "design_defect", "recall_class": "class2",
          "source_refs": [{"kind": "fda_510k", "ref": "K190204"}]}, 1),
        ({"change_type": "design_defect", "recall_class": "class1",
          "source_refs": [{"kind": "fda_510k", "ref": "K190204"}]}, 2),
    ]
    bad = []
    tmp = tempfile.mkdtemp(prefix="probe-cli-")
    for i, (ctx, want) in enumerate(cases):
        path = os.path.join(tmp, f"case{i}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ctx, f, ensure_ascii=False)
        rc = env.cli_rc(path)
        if rc != want:
            bad.append(f"{ctx['change_type']}/{ctx['recall_class']}: rc={rc} want {want}")
    usage = env.cli_rc("", extra_args=["--nope"])
    if usage != 64:
        bad.append(f"usage error rc={usage} want 64")
    return (not bad), "; ".join(bad) or "0/1/2/64 as documented"


# --- F. published contract ---------------------------------------------------

@probe("F1", "contract", "yesman",
       "the published change_type enum covers every change type the judge accepts")
def p_contract_enum(env) -> tuple:
    try:
        import yaml
    except ImportError:
        return None, "BLOCKED: PyYAML not installed — contract not checked"
    doc = yaml.safe_load(env.openapi_text())
    enum = set(doc["components"]["schemas"]["ChangeContext"]["properties"]
               ["change_type"].get("enum") or [])
    known = env.known_change_types()
    missing = sorted(known - enum)
    return (not missing), f"missing from contract: {missing}" if missing else \
        f"enum covers all {len(known)} types"


@probe("F2", "contract", "yesman",
       "the published source_refs shape matches what the judges require "
       "(objects with a ref, not bare strings)")
def p_contract_refs(env) -> tuple:
    try:
        import yaml
    except ImportError:
        return None, "BLOCKED: PyYAML not installed — contract not checked"
    doc = yaml.safe_load(env.openapi_text())
    items = doc["components"]["schemas"]["ChangeContext"]["properties"] \
        ["source_refs"].get("items", {})
    ok = items.get("type") == "object" and "ref" in (items.get("required") or [])
    return ok, f"items.type={items.get('type')} required={items.get('required')}"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_suite(env, label: str) -> List[Dict[str, Any]]:
    results = []
    for p in PROBES:
        try:
            outcome = p["fn"](env)
            ok, detail = outcome if isinstance(outcome, tuple) else (bool(outcome), "")
        except Exception as exc:
            ok, detail = False, f"probe raised {type(exc).__name__}: {exc}"
        status = "PASS" if ok is True else ("BLOCKED" if ok is None else "FAIL")
        results.append({"id": p["id"], "family": p["family"], "desc": p["desc"],
                        "status": status, "detail": detail, "suite": label})
        mark = {"PASS": "PASS", "FAIL": "FAIL", "BLOCKED": "BLOCK"}[status]
        print(f"  [{mark:5}] {p['id']:3} {p['desc'][:64]}")
        if status != "PASS":
            print(f"          -> {detail}")
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="adversarial probe harness")
    ap.add_argument("--selfcheck", action="store_true",
                    help="run every probe against its mutant and require it to fail")
    ap.add_argument("--json", default=None, help="write evidence JSON to this path")
    args = ap.parse_args(argv)

    env = RealEnv()
    print(f"redteam_probe — {len(PROBES)} probes over the real gate core")
    print("-" * 78)
    results = run_suite(env, "real")

    failed = [r for r in results if r["status"] == "FAIL"]
    blocked = [r for r in results if r["status"] == "BLOCKED"]
    vacuous: List[str] = []

    if args.selfcheck:
        print("-" * 78)
        print("selfcheck — every probe must FAIL against its declared mutant")
        for name, factory in MUTANTS.items():
            owned = [p for p in PROBES if p["mutant"] == name]
            if not owned:
                continue
            print(f"  mutant {name!r} ({len(owned)} probe(s))")
            mutant_env = factory()
            for p in owned:
                try:
                    outcome = p["fn"](mutant_env)
                    ok, detail = outcome if isinstance(outcome, tuple) else (bool(outcome), "")
                except Exception:
                    ok, detail = False, "raised"
                if ok is True:
                    vacuous.append(f"{p['id']} passes against mutant {name!r} — vacuous")
                    print(f"    [VACUOUS] {p['id']} still passes against {name!r}")
                elif ok is None:
                    vacuous.append(f"{p['id']} could not be exercised against {name!r}")
                    print(f"    [BLOCKED] {p['id']} not exercisable against {name!r}")
                else:
                    print(f"    [ok] {p['id']} fails against {name!r} as intended")

    print("-" * 78)
    print(f"{len(results) - len(failed) - len(blocked)}/{len(results)} probes PASS, "
          f"{len(failed)} FAIL, {len(blocked)} BLOCKED")

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"probes": results, "vacuous": vacuous,
                       "selfcheck": bool(args.selfcheck)}, f,
                      ensure_ascii=False, indent=2)
        print(f"evidence written to {args.json}")

    if failed or vacuous:
        if failed:
            print("FAILED PROBES: " + ", ".join(r["id"] for r in failed))
        if vacuous:
            print("VACUOUS PROBES: " + "; ".join(vacuous))
        return 1
    if args.selfcheck and not vacuous:
        print("SELFCHECK PASS — every probe can fail")
    return 0


if __name__ == "__main__":
    sys.exit(main())
