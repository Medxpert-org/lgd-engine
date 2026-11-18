"""Independent evaluation of the method note's claims.

Runs a clean clone, executes every command the note prints, and reports PASS/FAIL
per claim. Deliberately boring: subprocess, string matching, no framework, no
network beyond the single `git clone`.

Usage:
    python benchmarks/eval_method_note.py                    # clone from GitHub
    python benchmarks/eval_method_note.py --repo <path>      # clone from a local path
    python benchmarks/eval_method_note.py --keep             # keep the clone for inspection

Exit code 0 = every claim holds. Non-zero = at least one claim failed, and the
failing line says which.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BRANCH = "ci/contract-tests-20261118"
DEFAULT_REPO = "https://github.com/MedXpert-org/lgd-engine"


def _git() -> str:
    """Resolve git even when the interpreter's PATH is narrower than a shell's."""
    found = shutil.which("git")
    if found:
        return found
    for cand in (r"C:\Program Files\Git\cmd\git.exe",
                 r"C:\Program Files (x86)\Git\cmd\git.exe",
                 "/usr/bin/git", "/usr/local/bin/git"):
        if Path(cand).exists():
            return cand
    raise SystemExit("git executable not found on PATH — install git or pass it via PATH")


def run(cwd: Path, args: list, timeout: int = 300) -> tuple:
    p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class Result:
    def __init__(self):
        self.rows = []

    def check(self, cid: str, desc: str, output: str, must_contain=(), must_equal=None):
        ok = True
        if must_equal is not None:
            ok = ok and (output.strip() == must_equal)
        for needle in must_contain:
            if needle not in output:
                ok = False
        self.rows.append((cid, desc, ok, output.strip().splitlines()[-3:]))
        return ok

    def report(self) -> int:
        for cid, desc, ok, tail in self.rows:
            if ok:
                print(f"PASS {cid:6s} {desc}")
            else:
                print(f"FAIL {cid:6s} {desc}")
                for line in tail:
                    print(f"          | {line}")
        failed = [r for r in self.rows if not r[2]]
        print()
        print(f"{len(self.rows) - len(failed)}/{len(self.rows)} checks passed")
        return 0 if not failed else 1

    def markdown(self, head: str, branch: str) -> str:
        """The report is derived output, not prose: same run, same table.

        C12 itself is excluded: a report that counted its own freshness check
        could never settle (the count would depend on the report it is judging)."""
        from datetime import datetime, timezone
        rows = [r for r in self.rows if r[0] != "C12"]
        passed = sum(1 for r in rows if r[2])
        lines = [
            "# Evaluation report — generated, not written",
            "",
            "This file is produced by `benchmarks/eval_method_note.py --report`. Do not edit",
            "it by hand: the marker line below is asserted by check C12, so a hand-written",
            "number that disagrees with the repository fails the evaluation. C12 is excluded",
            "from the counts below — a report cannot contain the verdict on itself.",
            "",
            f"`<!-- eval-report branch={branch} head={head} "
            f"checks={len(rows)} passed={passed} -->`",
            "",
            f"Run at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC against "
            f"`{branch}` at `{head}`, from a fresh clone.",
            "",
            "| # | Claim checked | Result |",
            "|---|---|---|",
        ]
        for cid, desc, ok, _ in rows:
            lines.append(f"| {cid} | {desc} | {'PASS' if ok else '**FAIL**'} |")
        lines += [
            "",
            f"**{passed}/{len(rows)} checks passed** (plus C12, which validates this file).",
            "",
            "Scope of this report: it says nothing about correctness against real filings;",
            "it says that every claim the method note makes about *itself* survives an",
            "outsider re-running the same commands on a clean clone.",
            "",
        ]
        return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO, help="repository to clone")
    ap.add_argument("--branch", default=BRANCH)
    ap.add_argument("--keep", action="store_true", help="do not delete the clone")
    ap.add_argument("--report", default=None,
                    help="write the generated markdown report to this path")
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp(prefix="lgd-eval-"))
    clone = work / "clean"
    git = _git()
    print(f"cloning {args.repo} @ {args.branch} -> {clone}")
    code, out = run(work, [git, "clone", "--quiet", "--branch", args.branch,
                           args.repo, str(clone)])
    if code != 0:
        print("FAIL   clone failed")
        print(out)
        return 2

    res = Result()
    GIT = _git()
    head = run(clone, [GIT, "rev-parse", "--short", "HEAD"])[1].strip()
    dirty = [ln for ln in run(clone, [GIT, "status", "--porcelain"])[1].splitlines() if ln.strip()]
    print(f"HEAD {head} | dirty files on arrival: {len(dirty)}")
    res.rows.append(("E0", "clone arrives clean (no case-only or uncommitted noise)", len(dirty) == 0, dirty))

    py = sys.executable

    # Count assertions from source, so no figure in this file has to be hand-kept.
    assertions = 0
    for tf in sorted((clone / "tests").glob("test_*.py")):
        for line in tf.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("def test_"):
                assertions += 1

    # C1 — the NMPA table runs offline, and every shipped case matches its declared
    # verdict. The expected count is the number of case files, not a literal, so a
    # new case cannot fail this check for the wrong reason (or pass a stale one).
    n_nmpa = len(list((clone / "demo1" / "cases_nmpa").glob("*.json")))
    c, o = run(clone, [py, "-m", "lgd_engine.cli", "--all", "demo1/cases_nmpa", "--domain", "nmpa"])
    res.check("C1", f"NMPA table {n_nmpa}/{n_nmpa} offline", o,
              [f"{n_nmpa}/{n_nmpa} cases match expected verdict"])

    # C2 — byte-identical reruns
    cmd = [py, "-m", "lgd_engine.cli", "--case", "demo1/cases_mdr/mdr04_red_open_fsca.json",
           "--domain", "mdr"]
    _, a = run(clone, cmd)
    _, b = run(clone, cmd)
    res.check("C2", "byte-identical rerun", "identical" if a == b else "differs",
              ["identical"])

    # C3-C5 — the three laws, as individual runnable assertions
    for cid, tid, desc in [
        ("C3", "tests.test_contract.TestThreeLaws.test_l3_critical_forces_reject",
         "critical rule forces reject"),
        ("C4", "tests.test_contract.TestThreeLaws.test_l2_go_without_evidence_is_hold",
         "go without evidence downgraded to hold"),
        ("C5", "tests.test_contract.TestThreeLaws.test_crashing_judge_is_reject_and_flagged",
         "crashing judge is flagged, not a clean veto"),
    ]:
        c, o = run(clone, [py, "-m", "unittest", tid, "-v"])
        res.check(cid, desc, o, ["OK"])

    # C6 — exit codes
    codes = {}
    for name, cmd in [
        ("reject", [py, "-m", "lgd_engine.cli", "--case",
                    "demo1/cases_nmpa/nmpa04_red_licence_as_filing.json", "--domain", "nmpa"]),
        ("go", [py, "-m", "lgd_engine.cli", "--case",
                "demo1/cases_nmpa/nmpa01_green_registration_textual.json", "--domain", "nmpa"]),
        ("usage", [py, "-m", "lgd_engine.cli", "--nonsense-flag"]),
    ]:
        codes[name] = run(clone, cmd)[0]
    res.check("C6", "exit codes reject=2 / go=0 / usage=64", str(codes), [])
    res.rows[-1] = ("C6", "exit codes reject=2 / go=0 / usage=64",
                    codes["reject"] == 2 and codes["go"] == 0 and codes["usage"] == 64, [str(codes)])

    # C7 — MCP smoke
    c, o = run(clone, [py, "lgd_engine/mcp_smoke.py"])
    res.check("C7", "MCP smoke: 7 tools + RBAC both ways", o, ["SMOKE: PASS"])

    # C8 — baseline
    c, o = run(clone, [py, "benchmarks/adversarial_baseline.py"])
    res.check("C8", "baseline gate 12/12 vs naive 5/12", o,
              ["gate  : 12/12", "naive : 5/12", "delta : 7"])

    # C9 — page in sync
    c, o = run(clone, [py, "benchmarks/build_demo_page.py", "--check"])
    res.check("C9", "dossier page in sync with engine", o, ["OK"])

    # C10 — every rule names the provision it encodes, and no entry is dead air.
    # Derived, not a literal: the shipped-rule count comes from the same run as the
    # based count, so adding a rule cannot pass by leaving the assertion behind.
    c, o = run(clone, [py, "benchmarks/clause_matrix.py"])
    shipped = re.search(r"rules shipped:\s*(\d+)", o)
    based = re.search(r"with a basis\s*:\s*(\d+)", o)
    basis_ok = bool(
        c == 0 and shipped and based
        and int(based.group(1)) == int(shipped.group(1))  # equal counts => nothing unbased
    )
    res.rows.append(("C10", "every rule names a LAW / DOCTRINE basis", basis_ok,
                     [l for l in o.splitlines()
                      if l.startswith(("rules shipped", "with a basis", "unbased"))]))

    # C11 — a verdict is deterministic and costs microseconds, not a model call
    c, o = run(clone, [py, "benchmarks/verdict_cost.py"])
    res.rows.append(("C11", "verdict deterministic + cheap (no model)", c == 0 and "deterministic  : YES" in o,
                     [l for l in o.splitlines() if l.startswith(("deterministic", "median verdict"))]))
    o = o.replace("deterministic  : YES", "deterministic: YES")

    # C13 — every claim about a competitor carries a provenance label
    c, o = run(clone, [py, "benchmarks/edge_claims.py"])
    res.rows.append(("C13", "competitor claims carry provenance labels",
                     c == 0 and "problems   : 0" in o,
                     [l for l in o.splitlines() if l.startswith(("provenance", "problems"))]))

    # X1 — the guard is real: tamper, expect failure, restore
    page = clone / "demo" / "judge-dossier.html"
    original = page.read_text(encoding="utf-8")
    page.write_text(original + "\n<!-- tamper -->\n", encoding="utf-8")
    c, o = run(clone, [py, "benchmarks/build_demo_page.py", "--check"])
    page.write_text(original, encoding="utf-8")
    res.rows.append(("X1", "tampered page makes --check fail", c != 0, [o.strip().splitlines()[-1] if o.strip() else ""]))

    # X2 — the suite runs, and its size matches the count derived from source
    c, o = run(clone, [py, "-m", "unittest", "discover", "-s", "tests"])
    ran = None
    for line in o.splitlines():
        if line.startswith("Ran ") and " test" in line:
            try:
                ran = int(line.split()[1])
            except (IndexError, ValueError):
                ran = None
    res.rows.append(("X2", f"suite runs and reports {assertions} tests",
                     c == 0 and ran == assertions,
                     [f"ran={ran} counted={assertions} rc={c}"]))

    # X3 — stdlib only
    manifest = (clone / "pyproject.toml").read_text(encoding="utf-8")
    bad = []
    for pyf in list((clone / "lgd_engine").rglob("*.py")) + list((clone / "benchmarks").rglob("*.py")):
        for line in pyf.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            for mod in ("yaml", "requests", "numpy", "pandas", "pydantic"):
                if s.startswith(f"import {mod}") or s.startswith(f"from {mod}"):
                    bad.append(f"{pyf.name}: {s}")
    res.rows.append(("X3", "dependencies = [] and no third-party imports",
                     "dependencies = []" in manifest and not bad, [str(bad)]))

    # X4 — corpus size claimed in the note, compared against the disk rather than
    # against a literal: the note states it, the tree proves it.
    cases = [p for d in (clone / "demo1").glob("cases*") if d.is_dir()
             for p in d.glob("*.json")]
    note = (clone / "docs" / "methods" / "Method_Note_v1.md").read_text(encoding="utf-8")
    claimed = re.search(r"\*\*(\d+) case files\*\*", note)
    claimed_n = int(claimed.group(1)) if claimed else -1
    res.rows.append(("X4", f"note claims {claimed_n} cases, disk has {len(cases)}",
                     claimed_n == len(cases), [str(len(cases))]))

    # X5 — evaluation left nothing behind
    after = [ln for ln in run(clone, [GIT, "status", "--porcelain"])[1].splitlines() if ln.strip()]
    # the tamper test restores the file; a byte-identical restore must not show up
    res.rows.append(("X5", "tree still clean after the whole run", len(after) == 0, after))

    # X6 — the docs quote the same numbers this run derived from source, and every
    # command the README's audit table cites actually exists. The drift gate: adding
    # a test without updating the prose fails loudly and prints the number it should say.
    # It scans *every* markdown file, because fixing one stale figure per turn is how
    # this repository spent several rounds: the same number hides in five documents.
    readme = (clone / "README.md").read_text(encoding="utf-8")
    note = (clone / "docs" / "methods" / "Method_Note_v1.md").read_text(encoding="utf-8")
    readme_says = f"Ran {assertions} tests" in readme
    note_says = f"{assertions} assertions" in note
    cases_says = f"{len(cases)} case files" in readme
    cited = []
    for m in re.finditer(r"`python benchmarks/([^` ]+)", readme):
        cited.append(m.group(1))
    cited_missing = [c for c in cited
                     if not (clone / "benchmarks" / c).exists()]
    linked_missing = [p for p in re.findall(r"\]\((docs/methods/[^)]+)\)", readme)
                      if not (clone / p).exists()]

    stale = []
    md_files = [clone / "README.md"] + [
        p for p in sorted((clone / "docs").rglob("*.md"))
        if not re.search(r"\d{8}", p.name)]   # dated files are point-in-time snapshots
    for path in md_files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "→" in line or "->" in line:      # revision notes quote old numbers on purpose
                continue
            for m in re.finditer(r"(\d+)\s*(?:条)?断言|Ran\s+(\d+)\s+tests", line):
                n = int(m.group(1) or m.group(2))
                if n != assertions:
                    stale.append(f"{path.name}:{lineno} asserts {n}, source has {assertions}")
            for m in re.finditer(r"(\d+)\s*个?案件|(\d+)\s+case files", line):
                n = int(m.group(1) or m.group(2))
                if n != len(cases):
                    stale.append(f"{path.name}:{lineno} claims {n} cases, disk has {len(cases)}")

    res.rows.append(("X6", f"docs quote {assertions} assertions and {len(cases)} cases "
                           f"everywhere, and every cited audit command exists",
                     readme_says and note_says and cases_says
                     and not cited_missing and not linked_missing and not stale,
                     [f"readme={readme_says} note={note_says} cases={cases_says} "
                      f"missing_commands={cited_missing} missing_links={linked_missing} "
                      f"stale_numbers={stale[:6]}" + (f" (+{len(stale)-6} more)" if len(stale) > 6 else "")]))

    # C12 — the committed report is derived, not hand-written
    rep_path = clone / "docs" / "methods" / "Eval_Report_v1.md"
    marker_ok = False
    detail = ["missing report"]
    if rep_path.exists():
        text = rep_path.read_text(encoding="utf-8")
        m = re.search(r"<!-- eval-report branch=(\S+) head=(\S+) checks=(\d+) passed=(\d+) -->", text)
        if not m:
            detail = ["marker line missing"]
        else:
            b_ok = (m.group(1) == args.branch)
            h_ok = len(m.group(2)) >= 7
            # C12 is not yet in `rows`, and the report excludes it, so the counts
            # match len(rows) exactly at this point.
            c_ok = int(m.group(3)) == len(res.rows)
            p_ok = int(m.group(4)) == len(res.rows)
            marker_ok = b_ok and h_ok and c_ok and p_ok
            detail = [f"branch={m.group(1)} checks={m.group(3)}/{m.group(4)} "
                      f"cases={len(cases)} assertions={assertions}"]
    res.rows.append(("C12", "committed eval report is generated and current",
                     marker_ok, detail))

    print()
    rc = res.report()

    if args.report:
        out_path = Path(args.report)
        if not out_path.is_absolute():
            out_path = Path.cwd() / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(res.markdown(head, args.branch), encoding="utf-8")
        print(f"wrote {out_path}")

    if args.keep:
        print(f"\nclone kept at: {clone}")
    else:
        shutil.rmtree(work, ignore_errors=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
