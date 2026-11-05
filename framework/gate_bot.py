#!/usr/bin/env python3
"""gate_bot.py — CI-style gate bot for the LGD Engine MVP.

Check sequence (ordered, all must pass):
  1. Offline gold test  -> run mvp/demo1/selftest.py if present
  2. License files      -> release-prep/LICENSE and release-prep/NOTICE exist, non-empty
  3. No plaintext keys  -> scan tree for secret-shaped literals
  4. Manifest syntax    -> every skill.yaml / framework/examples/*.yaml validates
  5. Doc counts         -> every release doc states the same gate count, and the
                           "N stages" / "N domains" claims equal the row counts of
                           framework/ecosystem-map.md / framework/13domains-mapping.md
  6. demo2 suite        -> the 26/26 five-seat claim is re-run, not trusted

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
    # Red team S7 2026-11-04: AWS secret access keys, password assignments and
    # JWTs went through untouched ("no plaintext keys" was narrower than its name).
    re.compile(r"aws_?secret_?access_?key\s*[=:]\s*[^\s\"']{8,}", re.I),
    re.compile(r"\b(?:db_|mysql_)?(?:password|passwd|pwd)\s*[=:]\s*[\"']?[^\s\"'#]{6,}", re.I),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\."),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]"),          # ORCID-shaped
    re.compile(r"put" + r"_code"),                          # identifiers.toml key
]


def check_gold_test(root: Path) -> tuple[bool, str]:
    # One canonical path. A second candidate used to be preferred over the real
    # test, so dropping in demo1/selftest.py with sys.exit(0) turned the gate
    # green (red team S7 2026-11-04).
    shadow = root / "demo1" / "selftest.py"
    if shadow.exists():
        return False, ("demo1/selftest.py exists alongside demo1/test_demo1.py — "
                       "two self-test entry points, one of them can shadow the other; "
                       "keep only demo1/test_demo1.py")
    selftest = root / "demo1" / "test_demo1.py"
    if not selftest.exists():
        return False, "offline gold test not found: demo1/test_demo1.py missing"
    proc = subprocess.run(
        [sys.executable, str(selftest)], cwd=str(root),
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        return False, f"demo1 gold test FAILED (exit {proc.returncode}): " + " | ".join(tail)
    out = proc.stdout or ""
    m = re.search(r"(\d+)/(\d+) cases PASS;\s*(\d+)/(\d+) invariants PASS", out)
    if not m:
        return False, ("demo1 gold test exited 0 but printed no 'N/N cases PASS; N/N "
                       "invariants PASS' summary — a stub can exit 0")
    cases, total = int(m.group(1)), int(m.group(2))
    if cases < 5 or cases != total:
        return False, f"demo1 gold test reported {cases}/{total} cases; expected >=5 and all passing"
    return True, f"demo1 offline gold test PASS ({cases}/{total} cases, {m.group(3)}/{m.group(4)} invariants)"


def check_license_files(root: Path) -> tuple[bool, str]:
    problems = []
    # LICENSE: presence + size + Apache-2.0 text marker (red-team fix: a
    # 150-byte file or a MIT text used to pass the size-only check).
    p = root / "release-prep" / "LICENSE"
    if not p.exists():
        problems.append("missing release-prep/LICENSE")
    elif p.stat().st_size < 100:
        problems.append(f"release-prep/LICENSE suspiciously small ({p.stat().st_size}B)")
    elif b"Apache License" not in p.read_bytes():
        problems.append("release-prep/LICENSE lacks the Apache-2.0 text marker")
    # NOTICE: presence + size (provenance text is project-specific).
    p = root / "release-prep" / "NOTICE"
    if not p.exists():
        problems.append("missing release-prep/NOTICE")
    elif p.stat().st_size < 100:
        problems.append(f"release-prep/NOTICE suspiciously small ({p.stat().st_size}B)")
    if problems:
        return False, "; ".join(problems)
    return True, "LICENSE (Apache-2.0 text) and NOTICE present in release-prep/"


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


def _mini_yaml(text: str) -> dict:
    """Stdlib-only fallback YAML reader: top-level ``key: scalar`` pairs.

    Understands quoted strings, inline comments, null and YAML 1.1 booleans
    (true/yes/on, false/no/off). Lists (``key:\\n  - item``) and other complex
    values are kept as the raw first token so presence checks still work.
    """
    data = {}
    for m in re.finditer(r"^([a-z_][a-z0-9_]*)\s*:\s*(.*)$", text, re.M):
        key, raw = m.group(1), m.group(2).strip()
        raw = raw.split(" #")[0].strip()
        if not raw:
            data[key] = None
        elif (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
            data[key] = raw[1:-1]
        elif raw.lower() in ("true", "yes", "on"):
            data[key] = True
        elif raw.lower() in ("false", "no", "off"):
            data[key] = False
        elif raw.lower() == "null":
            data[key] = None
        else:
            data[key] = raw
    return data


def _yaml_balance(text: str) -> str | None:
    """Cheap structural sanity for the stdlib fallback path.

    Without PyYAML the parser above only reads top-level scalars, so a document
    like ``version: [unclosed`` sailed through as "valid" (red team S7
    2026-11-04). Unbalanced flow collections are now a failure.
    """
    for opener, closer in (("[", "]"), ("{", "}")):
        if text.count(opener) != text.count(closer):
            return f"unbalanced {opener}{closer} in document"
    for line in text.splitlines():
        stripped = line.split(" #")[0].rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        if re.search(r"[:\-]\s*\[\s*$", stripped) or re.search(r"[:\-]\s*\{\s*$", stripped):
            return f"flow collection never closed on line: {stripped[:60]}"
    return None


def load_manifest(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # optional
        try:
            data = yaml.safe_load(text)
        except Exception as exc:
            # A malformed manifest must be a clean FAIL, not a traceback: the
            # gate used to die with an uncaught parser error, which reads as
            # "CI broke" rather than "this file is invalid".
            return None, f"YAML parse error: {type(exc).__name__}: {str(exc).splitlines()[0][:120]}"
        if not isinstance(data, dict):
            return None, "not a mapping"
        return data, None
    except ImportError:
        # Stdlib fallback: top-level key presence + scalar value parsing, but
        # only after the document at least looks structurally sane.
        broken = _yaml_balance(text)
        if broken:
            return None, f"{broken} (PyYAML not installed, stdlib fallback refused)"
        return _mini_yaml(text), None


def check_manifests(root: Path) -> tuple[bool, str]:
    candidates = sorted((root / "framework" / "examples").glob("*.yaml"))
    candidates += sorted((root / "framework").glob("*.yaml"))
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
        entry = data.get("entry")
        entries = entry if isinstance(entry, list) else [entry]
        for one in entries:
            if isinstance(one, str) and (".." in one or one.startswith("/")):
                problems.append(f"{path.name}: entry path traversal / absolute path: '{one}'")
    if problems:
        return False, "manifest problems: " + " ;; ".join(problems)
    return True, f"{len(uniq)} manifest(s) valid: " + ", ".join(p.name for p in uniq)


def count_table_rows(path: Path) -> int:
    """Count numbered rows (``| 1 | ...``) in a markdown table. -1 if unreadable."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return -1
    return sum(1 for line in text.splitlines() if re.match(r"^\|\s*\d+\s*\|", line))


# A number in the README that no file in the tree backs is a claim, not a fact.
# Each entry: (README label, claim pattern, the table that must supply the count).
README_COUNT_CLAIMS = [
    ("stages", r"\*\*(\d+) stages\*\*", "framework/ecosystem-map.md"),
    ("domains", r"\*\*(\d+) domains\*\*", "framework/13domains-mapping.md"),
]


def check_doc_counts(root: Path) -> tuple[bool, str]:
    """Every release document must state the same gate count as the gate runs.

    It used to read README.md only, so llms.txt and release-prep/README.md could
    say 4/4 while README said 5/5 and the gate actually ran 5 (red team S7
    2026-11-04). Three release surfaces, three numbers, no check.
    """
    # count checks statically: the ordered list in main() is the contract
    src = Path(__file__).read_text(encoding="utf-8")
    actual = sum(1 for line in src.splitlines()
                 if re.match(r'\s*\("(\d+)\.[a-z0-9-]+",', line))
    docs = [root / "README.md", root / "llms.txt", root / "release-prep" / "README.md"]
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    problems, notes = [], []
    for d in docs:
        if not d.exists():
            continue
        text = d.read_text(encoding="utf-8", errors="replace")
        rel = d.relative_to(root).as_posix()
        for m in re.finditer(r"(\d+)/(\d+) checks? PASS", text):
            if int(m.group(1)) != actual or int(m.group(2)) != actual:
                problems.append(f"{rel}: says {m.group(1)}/{m.group(2)} checks, gate runs {actual}")
            else:
                notes.append(f"{rel}: {m.group(1)}/{m.group(2)}")
        for m in re.finditer(r"\((\w+) checks?\)", text):
            w = m.group(1).lower()
            n = words.get(w)
            if n is None:
                problems.append(f"{rel}: unparseable count word '{w}'")
            elif n != actual:
                problems.append(f"{rel}: says '{w}' ({n}) checks, gate runs {actual}")
    # The stage/domain counts must still match their source tables.
    readme = root / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        for label, pattern, src in README_COUNT_CLAIMS:
            m = re.search(pattern, text)
            if not m:
                problems.append(f"README has no '**N {label}**' claim to verify")
                continue
            claimed, rows = int(m.group(1)), count_table_rows(root / src)
            if rows < 0:
                problems.append(f"{src} unreadable, cannot verify the {claimed}-{label} claim")
            elif rows != claimed:
                problems.append(f"README claims {claimed} {label} but {src} lists {rows} rows")
            else:
                notes.append(f"{claimed} {label} = {rows} rows")
    if problems:
        return False, "documentation drift: " + "; ".join(problems)
    return True, (f"all release docs agree the gate runs {actual} checks "
                  f"({', '.join(sorted(set(notes)))})")


def check_demo2(root: Path) -> tuple[bool, str]:
    """The five-seat review suite is a documented claim, so the gate runs it."""
    probe = root / "demo2" / "test_demo2.py"
    if not probe.exists():
        return False, "demo2/test_demo2.py missing but README claims 26/26"
    proc = subprocess.run([sys.executable, str(probe)], cwd=str(root),
                          capture_output=True, text=True, timeout=300, errors="replace")
    out = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"(\d+)/(\d+)", out)
    if proc.returncode != 0:
        tail = out.strip().splitlines()[-3:]
        return False, f"demo2 suite FAILED (exit {proc.returncode}): " + " | ".join(tail)
    return True, f"demo2 five-seat suite PASS ({m.group(0) if m else 'n/a'})"


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
        ("5.doc-counts", check_doc_counts(root)),
        ("6.demo2-suite", check_demo2(root)),
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
