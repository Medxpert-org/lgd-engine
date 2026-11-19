"""lgd_engine.cli — console entry point (pyproject: lgd-gate = lgd_engine.cli:main).

Thin CLI over the judgment core. Mirrors demo1.change_gate without depending on
the demo layer; exit codes follow the release-gate convention:
  0=go, 1=hold, 2=reject, 3=tool error, 64=usage error.

`--all DIR` exists because the docs showed `--all` on this entry and it was only
implemented on the demo CLI — a documented command that errored out is a defect
in the doc surface, so the parity is now real (R19).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .gate import GateEngine
from .judges.judge_510k import Judge510kChange
from .judges.judge_postmarket import JudgePostmarket
from .judges.judge_pccp import JudgePccpScope
from .judges.judge_mdr import JudgeMdrSignificance
from .judges.judge_nmpa import JudgeNmpaChangeRegistration

_DOMAINS = {
    "510k": Judge510kChange,
    "postmarket": JudgePostmarket,
    "pccp": JudgePccpScope,
    "mdr": JudgeMdrSignificance,
    "nmpa": JudgeNmpaChangeRegistration,
}
_STRIP_KEYS = ("expected_verdict", "expected_fda_verdict",
               "expected_nmpa_verdict", "_desensitized_from")
RC_USAGE, RC_TOOL_ERROR = 64, 3
_RC = {"go": 0, "hold": 1, "reject": 2}


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:      # argparse exits 2 by default
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        print(f"(usage errors exit {RC_USAGE}, not 2 — 2 means REJECT)", file=sys.stderr)
        raise SystemExit(RC_USAGE)


def _run_one(path: Path, args) -> tuple:
    ctx = json.loads(path.read_text(encoding="utf-8"))
    expected = ctx.get("expected_verdict")
    for k in _STRIP_KEYS:
        ctx.pop(k, None)
    if args.jurisdiction:
        ctx["jurisdiction"] = args.jurisdiction
    eng = GateEngine()
    eng.register(_DOMAINS[args.domain]())
    return eng.evaluate(ctx), expected


def _describe(args) -> int:
    """--template / --fields: describe the input, never judge it (exit 0)."""
    from .templates import blank_template, render_fields, template

    judge = _DOMAINS[args.domain]()
    required = getattr(judge, "REQUIRED_FIELDS", {})
    if args.fields:
        print(render_fields(args.domain, args.corpus))
        return 0
    rec = template(args.domain, args.corpus) or blank_template(args.domain, required)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    where = (f"keys derived from the shipped {args.domain} cases; an empty value is an "
             f"unanswered question, not a finding. `lgd-gate --fields --domain "
             f"{args.domain}` lists the words this judge can classify" if rec and
             set(required) <= set(rec) else
             "no corpus found: keys only; run from the repository root for a derived template")
    print(f"# {args.domain} template — {where}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = _Parser(
        prog="lgd-gate",
        description="LGD Engine judgment core — go / hold / reject from a change context.",
    )
    ap.add_argument("--case", type=str,
                    help="path to a case JSON (change context; expected_* keys are stripped)")
    ap.add_argument("--all", metavar="CASES_DIR",
                    help="run every *.json case in this directory")
    ap.add_argument("--domain", choices=list(_DOMAINS), default="510k",
                    help="judge family to run (default 510k)")
    ap.add_argument("--jurisdiction", choices=["FDA", "NMPA"], default=None,
                    help="override the jurisdiction in the case JSON")
    ap.add_argument("--template", action="store_true",
                    help="print a fillable case record (every required key) instead of judging")
    ap.add_argument("--fields", action="store_true",
                    help="print the values the shipped cases use for each key, instead of judging")
    ap.add_argument("--corpus", default=".", metavar="ROOT",
                    help="repository root holding demo1/cases* (default: .)")
    args = ap.parse_args(argv)

    modes = [bool(args.case), bool(args.all), args.template, args.fields]
    if sum(modes) != 1:
        ap.error("exactly one of --case PATH, --all CASES_DIR, --template, --fields is required")

    if args.template or args.fields:
        return _describe(args)

    if args.all:
        root = Path(args.all)
        if not root.is_dir():
            ap.error(f"--all expects a directory, got {root}")
        cases = sorted(root.glob("*.json"))
        if not cases:
            ap.error(f"no *.json cases under {root}")
        matched = 0
        for c in cases:
            try:
                report, expected = _run_one(c, args)
            except Exception as exc:
                print(f"[ENGINE ERROR] {c.name}: {type(exc).__name__}: {exc}", file=sys.stderr)
                print(f"             exit {RC_TOOL_ERROR} = the tool failed; this is not "
                      f"a verdict.", file=sys.stderr)
                return RC_TOOL_ERROR
            got = report.verdict
            if expected and got == expected:
                matched += 1
            print(f"{c.name}: {got}"
                  + (f" (expected {expected})" if expected else ""))
        print(f"\n[summary] {matched}/{len(cases)} cases match expected verdict "
              f"(domain={args.domain})")
        return 0 if matched == len(cases) else 1

    path = Path(args.case)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    try:
        report, _expected = _run_one(path, args)
    except Exception as exc:
        print(f"[ENGINE ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"             exit {RC_TOOL_ERROR} = the tool failed; this is not a "
              f"verdict.", file=sys.stderr)
        return RC_TOOL_ERROR
    print(report.pretty())
    if getattr(report, "errors", None):
        for e in report.errors:
            print(f"[ENGINE ERROR] {e}", file=sys.stderr)
        print(f"             exit {RC_TOOL_ERROR} = the tool failed; the verdict above "
              f"is fail-safe, not a judgment.", file=sys.stderr)
        return RC_TOOL_ERROR
    return _RC.get(report.verdict, 1)


if __name__ == "__main__":
    raise SystemExit(main())
