"""Did fixing one rule quietly flip somebody else's verdict?

Every other benchmark measures *one* version of the engine: absence, spelling,
shortcuts, cost. None of them answers the question a reviewer asks about a
living repository: last release changed fifteen representations of a field and
the input contract behind it -- **which verdicts moved, and which were supposed
to?**

This tool runs two engines over the same case files -- a pinned git ref and the
working tree -- and prints the difference per case:

    python benchmarks/verdict_drift.py --base 28fe22b          # report
    python benchmarks/verdict_drift.py --write                 # regenerate the
                                                               # declared baselines
    python benchmarks/verdict_drift.py --check                 # fail on drift

The declared baselines live in `docs/methods/verdict_drift.json`. A declared row
must reproduce exactly -- same changed set, same unchanged count -- so a later
"harmless" fix that moves a verdict nobody mentioned turns the suite red instead
of shipping. `tests/test_contract.py::TestVerdictDrift` enforces that.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))

from build_demo_page import SUITES                     # noqa: E402  (one suite table)
from lgd_engine.gate import GateEngine                 # noqa: E402

OUT_JSON = ROOT / "docs" / "methods" / "verdict_drift.json"
OUT_MD = ROOT / "docs" / "methods" / "Verdict_Drift.md"

# Same five judges, addressed by domain so a *different* (older) engine can be
# asked for its verdict without this process importing it.
JUDGES = {
    "510k": ("lgd_engine.judges.judge_510k", "Judge510kChange"),
    "postmarket": ("lgd_engine.judges.judge_postmarket", "JudgePostmarket"),
    "pccp": ("lgd_engine.judges.judge_pccp", "JudgePccpScope"),
    "mdr": ("lgd_engine.judges.judge_mdr", "JudgeMdrSignificance"),
    "nmpa": ("lgd_engine.judges.judge_nmpa", "JudgeNmpaChangeRegistration"),
}

# Declared baselines: (git ref, human label, why it is worth pinning).
#
# The #30 row is the instrument's own proof: at that commit seven red-team cases
# still earned `go`, so a run that reports "0 changed" for every ref would be a
# broken tool rather than a clean history. The #44/#45 rows are the anchor for
# this generation: a future fix that flips a shipped case must declare it here,
# because the declared row stops reproducing and the suite goes red.
BASELINES = [
    ("1bc5340", "#30 — before the seven red-team fixes",
     "seven cases still earned go; this row proves the instrument can see a flip"),
    ("28fe22b", "#44 — before representation safety",
     "only spelling was canonicalised: no shipped case was meant to move"),
    ("58c0369", "#45 — representation safety merged",
     "the anchor for this generation: an undeclared flip shows up against this row"),
]

# Child process: import the *base* engine, judge the current case files, print
# verdicts. Inline so the old tree does not need a copy of this file.
CHILD = r'''
import importlib, json, sys
sys.path.insert(0, sys.argv[1])
from lgd_engine.gate import GateEngine
MAP = json.loads(sys.argv[2])
cases = json.load(open(sys.argv[3], encoding="utf-8"))
verdicts, errors = {}, {}
for c in cases:
    try:
        mod, cls = MAP[c["domain"]]
        m = importlib.import_module(mod)
        verdicts[c["file"]] = GateEngine([getattr(m, cls)()]).evaluate(c["ctx"]).to_dict()["verdict"]
    except Exception as exc:
        errors[c["file"]] = "%s: %s" % (type(exc).__name__, exc)
print(json.dumps({"verdicts": verdicts, "errors": errors}))
'''


def load_cases() -> list:
    """The 37 shipped cases, exactly as the demo page loads them."""
    out = []
    for rel, domain, _cls, _label, _juris in SUITES:
        d = ROOT / rel
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            ctx = json.loads(f.read_text(encoding="utf-8"))
            out.append({"domain": domain, "file": f"{rel}/{f.name}",
                        "case_id": ctx.get("case_id") or f.stem, "ctx": ctx})
    return out


def head_verdicts(cases: list) -> dict:
    """Verdicts from the engine in this working tree."""
    out = {}
    for c in cases:
        mod_name, cls_name = JUDGES[c["domain"]]
        mod = __import__(mod_name, fromlist=[cls_name])
        judge = getattr(mod, cls_name)()
        out[c["file"]] = GateEngine([judge]).evaluate(c["ctx"]).to_dict()["verdict"]
    return out


def _git(args: list, timeout: int = 180) -> subprocess.CompletedProcess:
    """Run git even where it is installed as a `.cmd` shim (Windows).

    `subprocess` cannot execute a `.cmd`/`.bat` without a shell, and on Windows
    the first `git` on PATH frequently *is* such a shim. Routing it through
    `cmd /c` keeps this working on both platforms without shell=True.
    """
    exe = shutil.which("git") or "git"
    if exe.lower().endswith((".cmd", ".bat")):
        argv = ["cmd", "/c", exe] + args
    else:
        argv = [exe] + args
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def ref_verdicts(ref: str, cases: list) -> tuple:
    """Verdicts from a pinned ref, run in a throwaway worktree.

    A separate worktree rather than `git archive`: two branches of the same
    repo can be on disk at once, and nothing here can be mistaken for the
    engine under test.
    """
    tmp = Path(tempfile.mkdtemp(prefix="lgd-drift-"))
    try:
        add = _git(["-C", str(ROOT), "worktree", "add", "--detach", str(tmp), ref])
        if add.returncode != 0:
            raise RuntimeError(f"cannot check out {ref}: {add.stderr.strip()[:300]}")
        case_file = tmp / "_cases.json"
        case_file.write_text(json.dumps([{"domain": c["domain"], "file": c["file"],
                                          "ctx": c["ctx"]} for c in cases],
                                        ensure_ascii=False), encoding="utf-8")
        run = subprocess.run([sys.executable, "-c", CHILD, str(tmp),
                              json.dumps(JUDGES), str(case_file)],
                             capture_output=True, text=True, timeout=300, cwd=str(tmp))
        if run.returncode != 0:
            raise RuntimeError(f"base engine failed on {ref}: "
                               f"{(run.stderr or run.stdout).strip()[:400]}")
        payload = json.loads(run.stdout.strip().splitlines()[-1])
        return payload["verdicts"], payload["errors"]
    finally:
        _git(["-C", str(ROOT), "worktree", "remove", "--force", str(tmp)])
        shutil.rmtree(tmp, ignore_errors=True)


def compare(ref: str, cases: list) -> dict:
    """One baseline row: what moved, what did not, what could not be measured."""
    base, errors = ref_verdicts(ref, cases)
    head = head_verdicts(cases)
    changed, same = [], 0
    for c in cases:
        f = c["file"]
        if f in errors:
            continue
        was, now = base.get(f), head.get(f)
        if was == now:
            same += 1
        else:
            changed.append({"file": f, "case_id": c["case_id"],
                            "domain": c["domain"], "base": was, "head": now,
                            "expected": c["ctx"].get("expected_verdict") or ""})
    return {"base": ref, "changed": changed, "unchanged": same, "errors": errors,
            "measured": same + len(changed)}


def build(baselines=BASELINES) -> dict:
    cases = load_cases()
    rows = []
    for ref, label, why in baselines:
        row = compare(ref, cases)
        row.update({"label": label, "why": why})
        rows.append(row)
    return {"_purpose": (
        "Which case verdicts moved between a pinned git ref and the working tree. "
        "Regenerate with `python benchmarks/verdict_drift.py --write`; the test suite "
        "fails if a declared row stops reproducing, so an undeclared verdict flip "
        "cannot ship quietly."),
        "cases": len(cases),
        "baselines": rows}


def render(data: dict) -> tuple:
    md = ["# Verdict drift across releases", "",
          "Which case verdicts moved between a pinned git ref and the working tree.",
          "Regenerate: `python benchmarks/verdict_drift.py --write`; "
          "check: `python benchmarks/verdict_drift.py --check`.", ""]
    for row in data["baselines"]:
        md.append(f"## {row['base']} — {row['label']}")
        md.append("")
        md.append(f"_{row['why']}_")
        md.append("")
        md.append(f"- cases measured: {row['measured']} of {data['cases']}")
        md.append(f"- verdicts unchanged: {row['unchanged']}")
        md.append(f"- verdicts changed: {len(row['changed'])}")
        if row["errors"]:
            md.append(f"- cases the base engine could not judge: {len(row['errors'])} "
                      f"({', '.join(sorted(row['errors'])[:3])}…)")
        if row["changed"]:
            md.append("")
            md.append("| case | domain | before | after | declared expectation |")
            md.append("|---|---|---|---|---|")
            for c in row["changed"]:
                md.append(f"| `{c['case_id']}` | {c['domain']} | {c['base']} | "
                          f"{c['head']} | {c['expected'] or '—'} |")
        else:
            md.append("")
            md.append("No case changed verdict. That is the point of this row: a "
                      "release may change how a field is read without changing what "
                      "any shipped case decides.")
        md.append("")
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n", "\n".join(md) + "\n")


def _strip(row: dict) -> dict:
    return {k: row[k] for k in ("base", "changed", "unchanged", "errors")}


def main() -> int:
    argv = sys.argv[1:]
    if "--base" in argv:
        ref = argv[argv.index("--base") + 1]
        row = compare(ref, load_cases())
        print(f"{ref}: {len(row['changed'])} changed / {row['unchanged']} unchanged"
              + (f" / {len(row['errors'])} unjudgeable" if row["errors"] else ""))
        for c in row["changed"]:
            print(f"  {c['case_id']:<28} {c['base']:>6} -> {c['head']:<6} "
                  f"(expected {c['expected'] or '—'})")
        return 0

    data = build()
    js, md = render(data)

    if "--check" in argv:
        if not OUT_JSON.exists() or not OUT_MD.exists():
            print("FAIL: docs/methods/verdict_drift.json is missing — run "
                  "`python benchmarks/verdict_drift.py --write`")
            return 1
        declared = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        for row in data["baselines"]:
            match = next((d for d in declared["baselines"] if d["base"] == row["base"]), None)
            if match is None:
                print(f"FAIL: no declared baseline for {row['base']}")
                return 1
            if _strip(match) != _strip(row):
                print(f"FAIL: verdicts moved at {row['base']} without being declared "
                      f"({[c['case_id'] for c in row['changed']]})")
                return 1
        print("OK: verdict drift matches the declared baselines")
        return 0

    if "--write" in argv:
        OUT_JSON.write_text(js, encoding="utf-8")
        OUT_MD.write_text(md, encoding="utf-8")
        print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")
        for row in data["baselines"]:
            print(f"  {row['base']}: {len(row['changed'])} changed / "
                  f"{row['unchanged']} unchanged")
        return 0

    print(js)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
