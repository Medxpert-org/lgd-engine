#!/usr/bin/env python3
"""security_scan.py — self-check the MVP tree for common security smells.

Scans <root> (default: mvp/) for:
  - hardcoded secret-shaped literals
  - danger-prone calls: eval, exec, os.system, and subprocess in shell mode
  - host absolute paths leaking
  - dependency lock file missing (SBOM recommendation)
  - work-in-progress markers

Exit 0 = no HIGH findings. Exit 1 = >=1 HIGH finding (warnings never fail).
Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules"}
SKIP_SUFFIX = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".zip"}

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{16,}"), "HIGH"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "HIGH"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "HIGH"),
]
DANGEROUS = [
    (re.compile(r"\beval\s*\("), "HIGH"),
    (re.compile(r"\bexec\s*\("), "HIGH"),
    (re.compile(r"os\.system\s*\("), "HIGH"),
    (re.compile(r"shell\s*=\s*True"), "HIGH"),
]
PATH_PATTERNS = [
    (re.compile(r"[A-Za-z]:\\Users\\"), "MEDIUM"),
    (re.compile(r"[A-Za-z]:\\Workbuddy\\"), "MEDIUM"),
    (re.compile(r"/home/[a-z0-9_]+/"), "MEDIUM"),
    (re.compile(r"/Users/[a-zA-Z]+/"), "MEDIUM"),
]
# Work-in-progress marker words are assembled from parts so this scanner
# does not flag its own source file.
TODO_PAT = re.compile(r"\b(" + "TO" + "DO|" + "FIX" + "ME|" + "HAC" + "K|" + "XX" + "X)\b")
LOCK_HINTS = ["requirements.txt", "requirements.lock", "pyproject.toml", "uv.lock", "package-lock.json"]


def iter_files(root: Path):
    import os
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if Path(fn).suffix in SKIP_SUFFIX:
                continue
            yield Path(dirpath) / fn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()
    root = Path(args.root).resolve()

    findings: list[tuple[str, str, str]] = []  # (severity, file, note)
    for f in iter_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(f.relative_to(root))
        for pat, sev in SECRET_PATTERNS:
            for m in pat.finditer(text):
                findings.append((sev, rel, f"secret-shaped literal {m.group(0)[:10]}..."))
        for pat, sev in DANGEROUS:
            for m in pat.finditer(text):
                findings.append((sev, rel, f"dangerous call: {m.group(0)}"))
        for pat, sev in PATH_PATTERNS:
            for m in pat.finditer(text):
                findings.append((sev, rel, f"host absolute path: {m.group(0)}"))
        for m in TODO_PAT.finditer(text):
            findings.append(("LOW", rel, f"marker {m.group(0)}"))

    has_lock = any((root / h).exists() for h in LOCK_HINTS)
    if not has_lock:
        findings.append(("MEDIUM", str(root),
                         "no dependency lock/manifest found -> recommend SBOM + requirements.lock"))

    print("=" * 60)
    print(f"security_scan.py  root={root}")
    print("=" * 60)
    if not findings:
        print("clean: 0 findings")
        return 0
    for sev, rel, note in sorted(findings):
        print(f"[{sev}] {rel}: {note}")
    high = [f for f in findings if f[0] == "HIGH"]
    print("-" * 60)
    print(f"total={len(findings)} high={len(high)}")
    return 1 if high else 0


if __name__ == "__main__":
    sys.exit(main())
