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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO, help="repository to clone")
    ap.add_argument("--branch", default=BRANCH)
    ap.add_argument("--keep", action="store_true", help="do not delete the clone")
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

    # C1 — five tables run offline
    c, o = run(clone, [py, "-m", "lgd_engine.cli", "--all", "demo1/cases_nmpa", "--domain", "nmpa"])
    res.check("C1", "NMPA table 7/7 offline", o, ["7/7 cases match expected verdict"])

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

    # C10 — every rule names the provision it encodes, and no entry is dead air
    c, o = run(clone, [py, "benchmarks/clause_matrix.py"])
    res.rows.append(("C10", "every rule names a LAW / DOCTRINE basis",
                     c == 0 and "with a basis : 60" in o,
                     [l for l in o.splitlines() if l.startswith("with a basis")]))

    # X1 — the guard is real: tamper, expect failure, restore
    page = clone / "demo" / "judge-dossier.html"
    original = page.read_text(encoding="utf-8")
    page.write_text(original + "\n<!-- tamper -->\n", encoding="utf-8")
    c, o = run(clone, [py, "benchmarks/build_demo_page.py", "--check"])
    page.write_text(original, encoding="utf-8")
    res.rows.append(("X1", "tampered page makes --check fail", c != 0, [o.strip().splitlines()[-1] if o.strip() else ""]))

    # X2 — assertion count claimed in the note
    c, o = run(clone, [py, "-m", "unittest", "discover", "-s", "tests"])
    res.check("X2", "suite reports Ran 49 tests", o, ["Ran 49 tests"])

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

    # X4 — corpus size claimed in the note
    cases = [p for d in (clone / "demo1").glob("cases*") if d.is_dir()
             for p in d.glob("*.json")]
    res.rows.append(("X4", f"note claims 30 cases, disk has {len(cases)}", len(cases) == 30, [str(len(cases))]))

    # X5 — evaluation left nothing behind
    after = [ln for ln in run(clone, [GIT, "status", "--porcelain"])[1].splitlines() if ln.strip()]
    # the tamper test restores the file; a byte-identical restore must not show up
    res.rows.append(("X5", "tree still clean after the whole run", len(after) == 0, after))

    print()
    rc = res.report()

    if args.keep:
        print(f"\nclone kept at: {clone}")
    else:
        shutil.rmtree(work, ignore_errors=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
