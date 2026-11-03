#!/usr/bin/env python3
"""gate_bot.py — CI-style gate bot for the LGD Engine MVP.

Check sequence (ordered, all must pass):
  1. Offline gold test  -> run mvp/demo1/selftest.py if present
  2. License files      -> release-prep/LICENSE and release-prep/NOTICE exist, non-empty
  3. No plaintext keys  -> scan tree for secret-shaped literals
  4. Manifest syntax    -> every skill.yaml / framework/examples/*.yaml validates

Exit 0 = PASS. Exit 1 = FAIL, failing items listed on stdout.

Stdlib only. PyYAML optional (fallback: structural key check).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_MANIFEST_FIELDS = [
    "name", "version", "description", "gate_tag",
    "requires_llm", "permissions", "entry", "dependencies",
]
VALID_GATE_TAGS = {"theory-bound", "auxiliary"}
VALID_PERMISSIONS = {"read-only", "suggest", "execute"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules"}
SKIP_SUFFIX = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".zip"}

# Secret-shaped literals. Note: the literal below is split so this scanner
# does not flag its own source code.
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]"),          # ORCID-shaped
    re.compile(r"put" + r"_code"),                          # identifiers.toml key
]


def check_gold_test(root: Path) -> tuple[bool, str]:
    # Accept either contract name used by the Demo1 workstream.
    candidates = [root / "demo1" / "selftest.py", root / "demo1" / "test_demo1.py"]
    selftest = next((c for c in candidates if c.exists()), None)
    if selftest is None:
        names = " / ".join(c.name for c in candidates)
        return False, f"offline gold test not found: demo1/{names} missing (Demo1 workstream pending)"
    proc = subprocess.run(
        [sys.executable, str(selftest)], cwd=str(root),
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        return False, f"demo1 gold test FAILED (exit {proc.returncode}): " + " | ".join(tail)
    return True, "demo1 offline gold test PASS (exit 0)"


def check_license_files(root: Path) -> tuple[bool, str]:
    problems = []
    for fname in ("LICENSE", "NOTICE"):
        p = root / "release-prep" / fname
        if not p.exists():
            problems.append(f"missing release-prep/{fname}")
        elif p.stat().st_size < 100:
            problems.append(f"release-prep/{fname} suspiciously small ({p.stat().st_size}B)")
    if problems:
        return False, "; ".join(problems)
    return True, "LICENSE and NOTICE present in release-prep/"


def scan_files(root: Path):
    for dirpath, dirnames, filenames in os_walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if Path(fn).suffix in SKIP_SUFFIX:
                continue
            yield Path(dirpath) / fn


def os_walk(root: Path):
    import os
    yield from os.walk(root)


def check_no_plaintext_keys(root: Path) -> tuple[bool, str]:
    hits = []
    for f in scan_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                hits.append(f"{f.relative_to(root)}: matched {pat.pattern!r} @ {m.group(0)[:12]}...")
    if hits:
        return False, f"{len(hits)} secret-shaped hit(s): " + " ;; ".join(hits[:5])
    return True, "no plaintext keys / ORCID-shaped literals in tree"


def load_manifest(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # optional
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            return None, "not a mapping"
        return data, None
    except ImportError:
        # Minimal structural fallback: top-level key presence only.
        keys = set(re.findall(r"^([a-z_][a-z0-9_]*)\s*:", text, re.M))
        fake = {k: True for k in keys}
        return fake, None


def check_manifests(root: Path) -> tuple[bool, str]:
    candidates = sorted((root / "framework" / "examples").glob("*.yaml"))
    candidates += sorted(root.glob("**/skill.yaml"))
    candidates = [c for c in candidates if c not in candidates[:0]]  # de-dup below
    seen, uniq = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    if not uniq:
        return False, "no skill manifest files found"
    problems = []
    for path in uniq:
        data, err = load_manifest(path)
        if err:
            problems.append(f"{path.name}: {err}")
            continue
        for field in REQUIRED_MANIFEST_FIELDS:
            if field not in data:
                problems.append(f"{path.name}: missing required field '{field}'")
        if "gate_tag" in data and str(data.get("gate_tag")) not in VALID_GATE_TAGS:
            problems.append(f"{path.name}: bad gate_tag '{data.get('gate_tag')}'")
        if "permissions" in data and str(data.get("permissions")) not in VALID_PERMISSIONS:
            problems.append(f"{path.name}: bad permissions '{data.get('permissions')}'")
    if problems:
        return False, "manifest problems: " + " ;; ".join(problems)
    return True, f"{len(uniq)} manifest(s) valid: " + ", ".join(p.name for p in uniq)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent),
                    help="mvp root directory (default: parent of framework/)")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    checks = [
        ("1.offline-gold-test", check_gold_test(root)),
        ("2.license-files", check_license_files(root)),
        ("3.no-plaintext-keys", check_no_plaintext_keys(root)),
        ("4.manifest-syntax", check_manifests(root)),
    ]
    failed = [name for name, (ok, _) in checks if not ok]
    print("=" * 60)
    print(f"gate_bot.py  root={root}")
    print("=" * 60)
    for name, (ok, msg) in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {msg}")
    print("=" * 60)
    if failed:
        print(f"RESULT: FAIL ({len(failed)} red: {', '.join(failed)})")
        return 1
    print("RESULT: PASS (all green)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
