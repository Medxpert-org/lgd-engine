#!/usr/bin/env python3
"""desanitize_check.py — release-tree desensitization review.

Scans <root> (default: mvp/) for identifiers.toml-shaped value leaks:
  - the reserved identifiers.toml key     (written as put + underscore + code)
  - ORCID-shaped numbers                  XXXX-XXXX-XXXX-XXXX
  - emails                               (example.com/.org/.net are allowlisted placeholders)
  - long bare number strings             >= 12 digits (phone/registration numbers)

Exit 0 = zero non-allowlisted hits. Exit 1 = hits found, listed.
Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules"}
SKIP_SUFFIX = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".zip"}

RESERVED_KEY = re.compile(r"put" + r"_code")               # split: self-clean source
ORCID_PAT = re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]")
EMAIL_PAT = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LONG_NUM_PAT = re.compile(r"\d{12,}")
ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")


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

    hits: list[tuple[str, str]] = []
    allowlisted: list[str] = []
    for f in iter_files(root):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(f.relative_to(root))
        for m in RESERVED_KEY.finditer(text):
            hits.append((rel, f"reserved key {m.group(0)!r}"))
        for m in ORCID_PAT.finditer(text):
            hits.append((rel, f"ORCID-shaped number {m.group(0)}"))
        for m in EMAIL_PAT.finditer(text):
            addr = m.group(0)
            if addr.lower().endswith(ALLOWED_EMAIL_DOMAINS):
                allowlisted.append(f"{rel}: {addr} (allowlisted placeholder)")
            else:
                hits.append((rel, f"email {addr}"))
        for m in LONG_NUM_PAT.finditer(text):
            hits.append((rel, f"long number {m.group(0)}"))

    print("=" * 60)
    print(f"desanitize_check.py  root={root}")
    print("=" * 60)
    if allowlisted:
        print("-- allowlisted placeholders (not leaks) --")
        for a in allowlisted:
            print(f"  {a}")
    if hits:
        print("-- HITS (must be fixed before release) --")
        for rel, note in hits:
            print(f"  {rel}: {note}")
        print(f"RESULT: {len(hits)} hit(s)")
        return 1
    print("RESULT: 0 non-allowlisted leaks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
