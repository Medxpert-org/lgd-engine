#!/usr/bin/env python3
"""pre_release_review.py — the gate a public contribution must pass before release.

Why this exists
---------------
Standards bodies and citation infrastructure do not read intentions. ITU-T takes
a contribution as material that may be redistributed without restriction
(ITU-T A.1 §3.1.6) and wants a software copyright/licensing declaration when
software is submitted (§3.1.7). W3C Community Groups require a CLA and public
archives. Zenodo ignores CITATION.cff whenever a .zenodo.json is present.
FORCE11 asks for unique identification, persistence, accessibility and
specificity — in practice: a resolvable identifier, a machine-readable citation
file, and a specific version.

An outside reader judges us on exactly one thing: can they reach the material,
run it, and verify the claim themselves. So every check below is written against
an *outside* vantage and is allowed to fail.

Checks
------
  links          every URL in review/registry.json resolves and carries its
                 expected marker (a soft-404 or login wall cannot pass)
  outsider       the committed tree is exported and the documented commands are
                 run verbatim in a clean temp dir
  docs-claims    numbers the docs assert match what the tree actually produces
  relative-links file paths the docs point at exist
  citation       CITATION.cff is complete, version-consistent, and has no silent
                 placeholder; a DOI is only allowed if it resolves
  license        LICENSE / pyproject / CITATION agree, and NOTICE exists
  public         the default branch is readable anonymously (no token)
  machine        llms.txt and the JSON/YAML entry points exist and parse

Vantages
--------
A filtered network produces false failures. A host we cannot reach is reported
BLOCKED, never PASS; an entry may carry an out-of-band `external_vantage`
confirmation (method + date + evidence), which is reported as PASS-EXTERNAL so a
reader can see the check was not run from here.

Usage
-----
  python review/pre_release_review.py                 # print table, exit 0/1
  python review/pre_release_review.py --json out.json # also write evidence
  python review/pre_release_review.py --only links
  python review/pre_release_review.py --selftest      # prove each check can fail
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "review" / "registry.json"
UA = "Mozilla/5.0 (compatible; lgd-pre-release-review/1.0; +https://github.com/Medxpert-org/lgd-engine)"
# Some hosts sit behind a WAF that drops bot-shaped User-Agents outright
# (force11.org does: RemoteDisconnected, while curl -A Mozilla gets 200). The
# question this check asks is "can a human open this URL?", so a browser UA is a
# legitimate second transport — and the finding records that it was needed,
# instead of hiding behind an external vantage.
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
TIMEOUT = 30
RETRIES = 4   # a single flake upstream must not decide a release gate

REQUIRED_CFF = ["cff-version", "message", "title", "authors", "version",
                "license", "repository-code"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def finding(fid: str, ok: bool, status: str, detail: str, **extra) -> dict:
    d = {"id": fid, "ok": ok, "status": status, "detail": detail}
    d.update(extra)
    return d


def _request(url: str, follow: bool, ua: str = UA):
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "*/*",
        "Accept-Language": "en,zh;q=0.8",
    })
    if not follow:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        opener = urllib.request.build_opener(NoRedirect)
    else:
        opener = urllib.request.build_opener()
    with opener.open(req, timeout=TIMEOUT) as r:
        raw = r.read(2_000_000)
        enc = (r.headers.get("Content-Encoding") or "").lower()
        if "gzip" in enc:
            import gzip
            raw = gzip.decompress(raw)
        elif "deflate" in enc:
            import zlib
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        return r.status, r.geturl(), raw


def _curl(url: str, follow: bool) -> dict:
    """Fallback transport: some hosts close the urllib TLS session but answer curl."""
    cmd = ["curl", "-sS", "-L" if follow else "", "--compressed",
           "--max-time", str(TIMEOUT), "-A", UA,
           "-w", "\n@@META@@%{http_code} %{url_effective}"]
    cmd = [c for c in cmd if c]
    cmd.append(url)
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT + 10)
    except Exception as e:
        return {"status": 0, "final": url, "body": b"", "err": f"curl: {e}"}
    out = p.stdout
    marker = b"\n@@META@@"
    idx = out.rfind(marker)
    if idx < 0:
        return {"status": 0, "final": url, "body": out,
                "err": (p.stderr or b"").decode("utf-8", "replace")[:200]}
    meta = out[idx + len(marker):].decode("utf-8", "replace").split(" ", 1)
    try:
        code = int(meta[0].strip())
    except Exception:
        code = 0
    final = meta[1].strip() if len(meta) > 1 else url
    return {"status": code, "final": final, "body": out[:idx], "err": ""}


def fetch(url: str, follow: bool = True) -> dict:
    """Return {status, final, body, err, note}. status 0 = could not reach at all."""
    last = {"status": 0, "final": url, "body": b"", "err": "not attempted", "note": ""}
    for attempt in range(RETRIES):
        ua = UA if attempt < RETRIES - 1 else UA_BROWSER
        try:
            status, final, body = _request(url, follow, ua)
            note = "" if ua == UA else "required a browser User-Agent (host blocks bot UAs)"
            return {"status": status, "final": final, "body": body, "err": "", "note": note}
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read(200_000)
            except Exception:
                pass
            # 3xx with follow=False surfaces as HTTPError only for 4xx/5xx
            return {"status": e.code, "final": getattr(e, "url", url),
                    "body": body, "err": f"HTTP {e.code}",
                    "note": "" if ua == UA else "browser User-Agent"}
        except Exception as e:                      # URLError, timeout, reset
            last = {"status": 0, "final": url, "body": b"",
                    "err": f"{type(e).__name__}: {e}"}
            time.sleep(1.5 * (attempt + 1))
    # urllib could not get through; try a different TLS stack before calling it dead
    alt = _curl(url, follow)
    if alt["status"] != 0:
        alt["err"] = (alt["err"] + " [transport: curl]").strip()
        alt["note"] = "curl transport"
        return alt
    last["err"] += f" (curl also failed: {alt['err'][:80]})"
    return last


# A control URL on the same host, owned by nobody in this project. If it is also
# unreachable, the network is down and an unreachable repo URL is a blocked
# vantage, not a broken link. Without this distinction the review reports a
# gateway outage as a defect in our own repository.
VANTAGE_CONTROL_URL = "https://raw.githubusercontent.com/octocat/Hello-World/master/README"
_VANTAGE: dict = {"checked": False, "ok": False, "detail": ""}


def vantage_ok() -> bool:
    if not _VANTAGE["checked"]:
        r = fetch(VANTAGE_CONTROL_URL)
        _VANTAGE["ok"] = (r["status"] == 200)
        _VANTAGE["detail"] = (f"control {VANTAGE_CONTROL_URL} -> HTTP {r['status']}"
                              if _VANTAGE["ok"] else
                              f"control {VANTAGE_CONTROL_URL} unreachable "
                              f"({r['err'][:120]}) — this vantage is blocked")
        _VANTAGE["checked"] = True
    return _VANTAGE["ok"]


def unreachable_status() -> str:
    """What to record when fetch() could not reach a URL at all."""
    return "blocked_by_vantage" if not vantage_ok() else "fail"


def read(path: Path) -> str:
    try:        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# 1. links
# ---------------------------------------------------------------------------
def check_links(root: Path, registry_path: Path | None = None) -> list[dict]:
    reg_path = registry_path or (root / "review" / "registry.json")
    try:
        reg = json.loads(read(reg_path))
    except Exception as e:
        return [finding("links", False, "fail", f"registry unreadable: {e}")]

    entries = []
    for group in ("external_standards", "own_surfaces"):
        for e in reg.get(group, []):
            e = dict(e)
            e["group"] = group
            entries.append(e)

    out = []
    for e in entries:
        url, marker = e["url"], (e.get("marker") or "").strip()
        res = fetch(url, follow=not e.get("doi_only"))
        status, body = res["status"], res["body"].decode("utf-8", "replace")

        if e.get("doi_only"):
            ok = status in (301, 302, 303, 307, 308)
            out.append(finding(
                e["id"], ok, "pass" if ok else ("blocked" if status == 0 else "fail"),
                f"DOI {'resolves' if ok else 'does not resolve'} (HTTP {status})"
                + (f" -> {res['final']}" if ok else f" err={res['err']}"),
                url=url, group=e["group"], why=e.get("why", "")))
            continue

        if status == 0:
            ext = e.get("external_vantage")
            if ext:
                out.append(finding(e["id"], True, "pass_external",
                                   f"unreachable from here ({res['err']}); confirmed "
                                   f"{ext.get('method')} on {ext.get('verified_at')}: "
                                   f"{ext.get('evidence')}",
                                   url=url, group=e["group"], why=e.get("why", "")))
            else:
                out.append(finding(e["id"], False, unreachable_status(),
                                   f"unreachable from this vantage ({res['err']}); "
                                   f"{_VANTAGE['detail']}; not counted as pass",
                                   url=url, group=e["group"],
                                   why=e.get("why", "")))
            continue

        if status in (401, 403):
            out.append(finding(e["id"], False, "blocked_by_target",
                               f"HTTP {status} at {res['final']} (target refuses this "
                               f"client; a browser may still open it)", url=url,
                               group=e["group"], why=e.get("why", "")))
            continue

        if not (200 <= status < 300):
            out.append(finding(e["id"], False, "fail", f"HTTP {status} at {res['final']}",
                               url=url, group=e["group"], why=e.get("why", "")))
            continue

        if e.get("marker_mode") == "pdf":
            is_pdf = body[:5] == "%PDF-" or body[:1024].find(b"%PDF-") >= 0
            out.append(finding(e["id"], is_pdf, "pass" if is_pdf else "fail",
                               f"HTTP {status}, PDF magic {'found' if is_pdf else 'MISSING'} "
                               f"(marker text not searched: binary body)",
                               url=url, group=e["group"], why=e.get("why", "")))
            continue

        if marker and marker.lower() not in body.lower():
            out.append(finding(e["id"], False, "fail",
                               f"HTTP {status} but marker {marker!r} absent — looks like "
                               f"a soft-404 or a wall", url=url, group=e["group"],
                               why=e.get("why", "")))
            continue

        note = res.get("note") or ""
        out.append(finding(e["id"], True, "pass",
                           f"HTTP {status}" + (f", marker {marker!r} found" if marker else "")
                           + (f" ({note})" if note else ""),
                           url=url, group=e["group"], why=e.get("why", "")))
    return out


# ---------------------------------------------------------------------------
# 2. outsider — export the committed tree and run the documented commands
# ---------------------------------------------------------------------------
def export_tree(root: Path, dest: Path, tree: str = "head") -> str:
    if tree == "worktree":
        for item in root.iterdir():
            if item.name in (".git", "__pycache__"):
                continue
            if item.is_dir():
                shutil.copytree(item, dest / item.name,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(item, dest / item.name)
        return "worktree"
    proc = subprocess.run(["git", "-C", str(root), "archive", "--format=tar",
                           "HEAD" if tree == "head" else tree],
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git archive failed: {proc.stderr.decode('utf-8', 'replace')[:300]}")
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tf:
        tf.extractall(dest, filter="data")  # py3.12+: refuse unsafe members
    rev = subprocess.run(["git", "-C", str(root), "rev-parse", "--short",
                          "HEAD" if tree == "head" else tree],
                         capture_output=True, text=True).stdout.strip()
    return f"{'HEAD' if tree == 'head' else tree}@{rev}"


def check_outsider(root: Path, tree: str = "head") -> list[dict]:
    try:
        reg = json.loads(read(root / "review" / "registry.json"))
        steps = reg.get("outsider_steps", [])
    except Exception as e:
        return [finding("outsider", False, "fail", f"steps unreadable: {e}")]
    if not steps:
        return [finding("outsider", False, "fail", "no outsider_steps declared")]

    tmp = Path(tempfile.mkdtemp(prefix="lgd_outsider_"))
    out = []
    try:
        rev = export_tree(root, tmp, tree)
        for s in steps:
            cmd = [sys.executable] + s["cmd"] if s["cmd"][0].endswith(".py") is False else [sys.executable] + s["cmd"]
            proc = subprocess.run(cmd, cwd=str(tmp), capture_output=True, text=True,
                                  timeout=300, errors="replace")
            tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-4:]
            got = "\n".join(tail)
            rc_ok = proc.returncode == s["expect_rc"]
            miss = [m for m in s.get("expect_contains", [])
                    if m.lower() not in ((proc.stdout or "") + (proc.stderr or "")).lower()]
            ok = rc_ok and not miss
            detail = f"rc={proc.returncode} (expect {s['expect_rc']})"
            if miss:
                detail += f", missing {miss}"
            detail += f" | {got[:300]}"
            out.append(finding(s["id"], ok, "pass" if ok else "fail", detail,
                               step=" ".join(s["cmd"]), tree=rev,
                               why=s.get("why", "")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


# ---------------------------------------------------------------------------
# 2b. parity — is the tree an outsider can actually get the tree we reviewed?
# ---------------------------------------------------------------------------
def check_parity(root: Path, ref: str = "origin/main") -> list[dict]:
    """Compare the published tree with the reviewed tree, and run the docs on it.

    A review of a branch nobody can see answers the wrong question. This check
    resolves `ref` (default: the public default branch as this clone last fetched
    it), reports the commit gap, and then runs the same documented commands
    against *that* tree — which is what a stranger gets today.
    """
    out: list[dict] = []
    head = _git(root, "rev-parse", "HEAD")
    base = _git(root, "rev-parse", ref)
    if not head:
        return [finding("parity", False, "blocked", "not a git checkout")]
    if not base:
        return [finding("parity", False, "blocked_by_vantage",
                        f"{ref} is not present in this clone (no network to fetch it); "
                        f"published-vs-reviewed parity is unverified from here")]

    if base == head:
        out.append(finding("parity-sha", True, "pass",
                           f"published tree == reviewed tree ({head[:7]})"))
    else:
        ahead = _git(root, "rev-list", "--count", f"{base}..{head}") or "?"
        out.append(finding("parity-sha", False, "fail",
                           f"{ref} is {ahead} commit(s) behind HEAD ({base[:7]} vs "
                           f"{head[:7]}): the published tree is not the reviewed tree"))

    # What a stranger gets from the published ref, run verbatim.
    steps = []
    try:
        reg = json.loads(read(root / "review" / "registry.json"))
        steps = reg.get("outsider_steps", [])
    except Exception:
        pass
    tmp = Path(tempfile.mkdtemp(prefix="lgd_parity_"))
    try:
        export_tree(root, tmp, ref)
        for s in steps[:3]:            # the quickstart + gold suites; enough to see if it runs
            try:
                proc = subprocess.run([sys.executable] + s["cmd"], cwd=str(tmp),
                                      capture_output=True, text=True, timeout=300,
                                      encoding="utf-8", errors="replace")
                ok = proc.returncode == s.get("expect_rc", 0)
                detail = (f"{ref}: rc={proc.returncode} (expect {s.get('expect_rc', 0)}) | "
                          f"{(proc.stdout or proc.stderr or '').strip().splitlines()[-1][:120]}")
            except Exception as exc:
                ok, detail = False, f"{ref}: could not run ({type(exc).__name__})"
            out.append(finding(f"parity-run:{s['id']}", ok, "pass" if ok else "fail",
                               detail, step=" ".join(s["cmd"])))
    except Exception as exc:
        out.append(finding("parity-export", False, "blocked",
                           f"could not export {ref}: {type(exc).__name__}"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


# ---------------------------------------------------------------------------
# 3. docs-claims
# ---------------------------------------------------------------------------
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def check_docs_claims(root: Path) -> list[dict]:
    readme = read(root / "README.md")
    out = []
    if not readme:
        return [finding("docs-claims", False, "fail", "README.md missing")]

    # how many checks does gate_bot actually run?
    proc = subprocess.run([sys.executable, str(root / "framework" / "gate_bot.py")],
                          cwd=str(root), capture_output=True, text=True, timeout=180,
                          errors="replace")
    actual = len(re.findall(r"^\[(?:PASS|FAIL)\]", proc.stdout or "", re.M))

    m = re.search(r"gate_bot\.py\s*#[^\n]*?\((\w+) checks?\)", readme)
    if not m:
        out.append(finding("readme-gate-count", False, "fail",
                           "README does not state how many checks the gate runs"))
    else:
        word = m.group(1).lower()
        claimed = WORDS.get(word)
        ok = claimed == actual and actual > 0
        out.append(finding("readme-gate-count", ok, "pass" if ok else "fail",
                           f"README says '{word}' ({claimed}); gate_bot runs {actual}"))

    m = re.search(r"gate_bot\.py\*\*:\s*\*\*(\d+)/(\d+) checks PASS\*\*", readme)
    if m:
        ok = (int(m.group(1)) == actual and int(m.group(2)) == actual)
        out.append(finding("readme-gate-evidence", ok, "pass" if ok else "fail",
                           f"evidence says {m.group(1)}/{m.group(2)}; actual {actual}"))

    # every documented self-test count must match a real run
    m = re.search(r"demo1 change-gate gold tests:\s*\*\*(\d+)/(\d+) PASS\*\*", readme)
    if m:
        claimed = f"{m.group(1)}/{m.group(2)}"
        p = subprocess.run([sys.executable, str(root / "demo1" / "test_demo1.py")],
                           cwd=str(root), capture_output=True, text=True, timeout=180,
                           errors="replace")
        hit = re.search(r"(\d+)/(\d+)", (p.stdout or "") + (p.stderr or ""))
        actual = f"{hit.group(1)}/{hit.group(2)}" if hit else "n/a"
        ok = claimed == actual
        out.append(finding("readme-demo1-count", ok, "pass" if ok else "fail",
                           f"README {claimed}, run {actual}"))

    m = re.search(r"demo2 five-seat review:\s*\*\*(\d+)/(\d+) PASS\*\*", readme)
    if m:
        claimed = f"{m.group(1)}/{m.group(2)}"
        p = subprocess.run([sys.executable, str(root / "demo2" / "test_demo2.py")],
                           cwd=str(root), capture_output=True, text=True, timeout=300,
                           errors="replace")
        hit = re.search(r"(\d+)/(\d+)", (p.stdout or "") + (p.stderr or ""))
        actual = f"{hit.group(1)}/{hit.group(2)}" if hit else "n/a"
        ok = claimed == actual
        out.append(finding("readme-demo2-count", ok, "pass" if ok else "fail",
                           f"README {claimed}, run {actual}"))
    return out


# ---------------------------------------------------------------------------
# 4. relative links in the docs
# ---------------------------------------------------------------------------
FILEISH = re.compile(r"^[A-Za-z0-9_.\-/]+\.(py|md|yaml|yml|json|txt|ps1|toml|cff|cfg|sh)$")


def check_relative_links(root: Path) -> list[dict]:
    doc = read(root / "README.md")
    if not doc:
        return [finding("relative-links", False, "fail", "README.md missing")]
    try:
        reg = json.loads(read(root / "review" / "registry.json"))
    except Exception:
        reg = {}
    # Some paths in a README are destinations the reader creates, not files we
    # ship. They must be declared with a reason instead of quietly skipped.
    exceptions = {e["path"]: e.get("why", "") for e in reg.get("relative_link_exceptions", [])}

    refs, missing, excused = set(), [], []
    for code in re.findall(r"`([^`\n]{2,80})`", doc):
        if "://" in code or " " in code or code.startswith("-") or "<" in code:
            continue
        if not FILEISH.match(code) or "*" in code:
            continue
        refs.add(code)
    for r in sorted(refs):
        if (root / r).exists():
            continue
        if r in exceptions:
            excused.append(f"{r} ({exceptions[r]})")
        else:
            missing.append(r)
    ok = not missing
    detail = (f"{len(refs)} referenced path(s) all exist" if ok else
              f"{len(refs)} referenced, missing: {missing}")
    if excused:
        detail += f"; declared non-files: {excused}"
    return [finding("relative-links", ok, "pass" if ok else "fail", detail)]


# ---------------------------------------------------------------------------
# 5. citation metadata
# ---------------------------------------------------------------------------
def check_citation(root: Path) -> list[dict]:
    cff_path = root / "CITATION.cff"
    if not cff_path.exists():
        return [finding("citation", False, "fail", "CITATION.cff missing")]
    text = read(cff_path)
    out = []

    missing = [k for k in REQUIRED_CFF if not re.search(rf"^{re.escape(k)}\s*:", text, re.M)]
    out.append(finding("cff-required", not missing, "pass" if not missing else "fail",
                       "all required keys present" if not missing else f"missing {missing}"))

    py = read(root / "pyproject.toml")
    m_cff = re.search(r"^version:\s*[\"']?([0-9][^\"'\s]*)", text, re.M)
    m_py = re.search(r"^version\s*=\s*[\"']([^\"']+)", py, re.M)
    ok = bool(m_cff and m_py) and m_cff.group(1) == m_py.group(1)
    out.append(finding("cff-version", ok, "pass" if ok else "fail",
                       f"CITATION {m_cff.group(1) if m_cff else None} vs pyproject "
                       f"{m_py.group(1) if m_py else None}"))

    # a DOI may only appear if it resolves
    m = re.search(r"^doi:\s*[\"']?(10\.[^\"'\s]+)", text, re.M)
    if m:
        r = fetch(f"https://doi.org/{m.group(1)}", follow=False)
        ok = r["status"] in (301, 302, 303, 307, 308)
        out.append(finding("cff-doi", ok, "pass" if ok else "fail",
                           f"doi {m.group(1)} http {r['status']} "
                           f"{'resolves' if ok else 'does not resolve'}"))
    else:
        out.append(finding("cff-doi", True, "pass",
                           "no DOI claimed (acceptable before Zenodo mints one)"))

    # a placeholder must be labelled as one, in the same breath
    silent = []
    for line in text.splitlines():
        if re.search(r"placeholder", line, re.I) and not re.search(r"do not cite|not cite|placeholder", line, re.I):
            silent.append(line.strip()[:60])
    for block in re.findall(r"note:\s*[\"'](.+?)[\"']\s*$", text, re.M):
        if "placeholder" in block.lower() and "do not cite" not in block.lower():
            silent.append(block[:60])
    ok = not silent
    out.append(finding("cff-placeholder", ok, "pass" if ok else "fail",
                       "placeholders are labelled 'do not cite'" if ok
                       else f"silent placeholder(s): {silent[:2]}"))

    # Zenodo rule: .zenodo.json makes Zenodo ignore CITATION.cff
    z = root / ".zenodo.json"
    ok = not z.exists()
    out.append(finding("zenodo-precedence", ok, "pass" if ok else "fail",
                       "no .zenodo.json, so CITATION.cff is what Zenodo reads"
                       if ok else ".zenodo.json present — Zenodo will ignore CITATION.cff; "
                                   "keep both in sync or drop one"))
    return out


# ---------------------------------------------------------------------------
# 6. license consistency
# ---------------------------------------------------------------------------
def check_license(root: Path) -> list[dict]:
    out = []
    lic = next((p for p in [root / "LICENSE", root / "release-prep" / "LICENSE"] if p.exists()), None)
    ok = lic is not None and "Apache License" in read(lic)
    out.append(finding("license-text", ok, "pass" if ok else "fail",
                       f"Apache text found in {lic.relative_to(root)}" if ok
                       else "no Apache-2.0 LICENSE text found (root or release-prep)"))
    out.append(finding("notice", (root / "release-prep" / "NOTICE").exists()
                       or (root / "NOTICE").exists(), "pass",
                       "NOTICE present" if ((root / "release-prep" / "NOTICE").exists()
                                            or (root / "NOTICE").exists())
                       else "NOTICE missing"))

    py = read(root / "pyproject.toml")
    cff = read(root / "CITATION.cff")
    py_ok = "Apache-2.0" in py
    cff_ok = re.search(r"^license:\s*Apache-2\.0", cff, re.M) is not None
    ok = py_ok and cff_ok
    out.append(finding("license-agreement", ok, "pass" if ok else "fail",
                       f"pyproject Apache-2.0={py_ok}, CITATION Apache-2.0={cff_ok}"))

    # the README tells readers to look at `LICENSE`; make sure that path resolves
    readme = read(root / "README.md")
    claims_root = re.search(r"see\s+`LICENSE`", readme) is not None
    ok = (not claims_root) or (root / "LICENSE").exists()
    out.append(finding("license-path", ok, "pass" if ok else "fail",
                       "README's `LICENSE` path resolves" if ok
                       else "README points at `LICENSE` but the file is only in release-prep/"))
    return out


# ---------------------------------------------------------------------------
# 7. public visibility (anonymous)
# ---------------------------------------------------------------------------
def check_public(root: Path, url: str | None = None) -> list[dict]:
    reg = {}
    try:
        reg = json.loads(read(root / "review" / "registry.json"))
    except Exception:
        pass
    target = url or "https://raw.githubusercontent.com/Medxpert-org/lgd-engine/main/README.md"
    if not url:
        for e in reg.get("own_surfaces", []):
            if e.get("vantage") == "external_required":
                target = e["url"]
                break
    r = fetch(target)
    body = r["body"].decode("utf-8", "replace")
    if r["status"] == 0:
        ext = None
        for e in reg.get("own_surfaces", []):
            if e["url"] == target:
                ext = e.get("external_vantage")
        if ext:
            return [finding("public-anonymous", True, "pass_external",
                            f"unreachable here; confirmed {ext.get('method')} "
                            f"{ext.get('verified_at')}: {ext.get('evidence')}")]
        return [finding("public-anonymous", False, unreachable_status(),
                        f"cannot reach {target} from this vantage ({r['err']}); "
                        f"{_VANTAGE['detail']}")]
    ok = 200 <= r["status"] < 300 and "LGD Engine" in body
    return [finding("public-anonymous", ok, "pass" if ok else "fail",
                    f"anonymous GET {target} -> HTTP {r['status']}"
                    + ("" if ok else " (not public, or wrong content)"), url=target)]


# ---------------------------------------------------------------------------
# 8. machine-readable entry points
# ---------------------------------------------------------------------------
def check_machine(root: Path) -> list[dict]:
    out = []
    llms = root / "llms.txt"
    text = read(llms)
    # An agent entry point is only useful if it carries a runnable command.
    runnable = bool(re.search(r"python3?\s+-m\s+\S+|python3?\s+\S+\.py", text))
    ok = llms.exists() and len(text.splitlines()) >= 40 and runnable
    out.append(finding("llms-txt", ok, "pass" if ok else "fail",
                       f"{len(text.splitlines())} lines, runnable command={runnable}"
                       if llms.exists() else "llms.txt missing"))

    for rel in (".cursor-plugin/plugin.json", "review/registry.json"):
        p = root / rel
        if not p.exists():
            continue
        try:
            json.loads(read(p))
            out.append(finding(f"json:{rel}", True, "pass", "parses"))
        except Exception as e:
            out.append(finding(f"json:{rel}", False, "fail", f"invalid JSON: {e}"))

    oapi = root / "docs" / "openapi.yaml"
    ok = oapi.exists() and "openapi:" in read(oapi)
    out.append(finding("openapi", ok, "pass" if ok else "fail",
                       "openapi.yaml present" if ok else "docs/openapi.yaml missing/invalid"))
    return out


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
def check_redteam(root: Path) -> list[dict]:
    """Run the adversarial probe harness and require it to be non-vacuous.

    A red-team report that cannot fail is decoration. This check insists on all
    three: every probe passes, the harness proves each probe *can* fail
    (--selfcheck), and a probe count of zero is a failure rather than a pass.
    """
    script = root / "review" / "redteam_probe.py"
    if not script.exists():
        return [finding("redteam", False, "fail", "review/redteam_probe.py missing")]
    try:
        p = subprocess.run([sys.executable, str(script), "--selfcheck"],
                           cwd=str(root), capture_output=True, text=True, timeout=600,
                           encoding="utf-8", errors="replace")
    except Exception as e:
        return [finding("redteam", False, "blocked", f"{type(e).__name__}: {e}")]

    out = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"(\d+)/(\d+) probes PASS", out)
    passed, total = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    vacuous = "VACUOUS PROBES" in out

    ok = p.returncode == 0 and total > 0 and passed == total and not vacuous \
        and "SELFCHECK PASS" in out
    if ok:
        detail = f"{passed}/{total} probes pass, every probe proven able to fail"
    elif total == 0:
        detail = "harness produced no probes (vacuous by construction)"
    elif vacuous:
        detail = "at least one probe passes against its own mutant — measures nothing"
    else:
        detail = f"{passed}/{total} probes pass, rc={p.returncode}"
    return [finding("redteam", ok, "pass" if ok else "fail", detail)]


def check_legal(root: Path) -> list[dict]:
    """The four legal artifacts a standards contribution depends on.

    Each one is presence-of-substance, not presence-of-file: a LICENSE without
    the patent grant, a NOTICE without a holder, a CONTRIBUTING with only an
    outbound licence, and a readiness note whose negative claims declare no
    retrieval scope are all "files that exist and prove nothing".
    """
    out = []
    lic = read(root / "LICENSE")
    out.append(finding("patent-grant", "Grant of Patent License" in lic, 
                       "pass" if "Grant of Patent License" in lic else "fail",
                       "Apache-2.0 §3 patent grant present" if "Grant of Patent License" in lic
                       else "LICENSE has no §3 patent grant — a standards body reads that "
                            "as an unresolved patent position"))

    notice = read(root / "NOTICE")
    has_holder = bool(re.search(r"Copyright\s+\(c\)\s*\d{4}\s+\S+", notice, re.I))
    out.append(finding("notice-holder", has_holder, "pass" if has_holder else "fail",
                       "NOTICE names a copyright holder" if has_holder
                       else "NOTICE has no 'Copyright (c) <year> <holder>' line — ITU-T A.1 "
                            "§3.1.7 wants a copyright and licensing declaration"))

    contrib = read(root / "CONTRIBUTING.md")
    inbound = bool(re.search(r"inbound", contrib, re.I)) and "Apache License 2.0" in contrib
    out.append(finding("inbound-licence", inbound, "pass" if inbound else "fail",
                       "CONTRIBUTING states inbound = outbound licensing" if inbound
                       else "CONTRIBUTING covers the outbound licence only — a third-party PR "
                            "would carry no inbound licence and the redistribution chain breaks"))

    readiness = read(root / "release-prep" / "STANDARDS_CONTRIBUTION_READINESS.md")
    scoped = bool(readiness) and "检索范围" in readiness and "未查" in readiness
    out.append(finding("readiness-scope", scoped, "pass" if scoped else "fail",
                       "readiness note states its retrieval scope and what it did not check"
                       if scoped else "readiness note missing, or its negative claims declare "
                                      "no retrieval scope (anti-pattern 45)"))
    return out


CHECKS = [
    ("links", "Every cited URL resolves and carries its expected text", check_links),
    ("outsider", "The committed tree runs the documented commands verbatim", check_outsider),
    ("docs-claims", "Numbers in the docs match what the tree produces", check_docs_claims),
    ("parity", "The tree an outsider can fetch is the tree this review examined",
     check_parity),
    ("relative-links", "File paths named in the docs exist", check_relative_links),
    ("citation", "Citation metadata is complete and honest", check_citation),
    ("license", "LICENSE / pyproject / CITATION agree", check_license),
    ("legal", "The legal artifacts a standards contribution depends on carry substance",
     check_legal),
    ("public", "The default branch is readable without a token", check_public),
    ("machine", "Agent-facing entry points exist and parse", check_machine),
    ("redteam", "The judgment core survives adversarial probes, and each probe can fail",
     check_redteam),
]


def run(root: Path, only: str | None, tree: str) -> dict:
    results = []
    for cid, title, fn in CHECKS:
        if only and cid != only:
            continue
        try:
            if cid == "outsider":
                fs = fn(root, tree)
            else:
                fs = fn(root)
        except Exception as e:
            fs = [finding(cid, False, "error", f"{type(e).__name__}: {e}")]
        results.append({"id": cid, "title": title, "ok": all(f["ok"] for f in fs),
                        "findings": fs})
    total = sum(len(r["findings"]) for r in results)
    # A blocked finding is not a failure and not a pass. Counting it as a failure
    # turned a proxy outage into "our repo is broken" (2026-11-04), so the three
    # states are counted separately and the verdict says which one won.
    NON_PASS_BLOCKING = ("blocked", "blocked_by_target", "blocked_by_vantage")
    failed = sum(1 for r in results for f in r["findings"]
                 if not f["ok"] and f["status"] not in NON_PASS_BLOCKING)
    blocked = sum(1 for r in results for f in r["findings"]
                  if f["status"] in NON_PASS_BLOCKING)
    verdict = "FAIL" if failed else ("BLOCKED" if blocked else "PASS")
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        # The evidence file is published, so it must not carry the reviewer's
        # local filesystem layout (security_scan flags host paths as MEDIUM, and
        # an outside reader gains nothing from them). Repo-relative only.
        "root": ".",
        "commit": _head_sha(root),
        "branch": _head_branch(root),
        "summary": {"checks": len(results), "findings": total,
                    "failed": failed, "blocked": blocked,
                    "verdict": verdict,
                    "vantage": _VANTAGE["detail"]},
        "checks": results,
    }


def _git(root: Path, *args: str) -> str:
    try:
        p = subprocess.run(["git", "-C", str(root), *args],
                           capture_output=True, text=True, timeout=30)
        return p.stdout.strip() if p.returncode == 0 else ""
    except Exception:
        return ""


def _head_sha(root: Path) -> str:
    return _git(root, "rev-parse", "--short", "HEAD") or "unknown"


def _head_branch(root: Path) -> str:
    return _git(root, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"


def print_report(rep: dict) -> None:
    print("=" * 78)
    print("PRE-RELEASE REVIEW — branch %s @ %s" %
          (rep.get("branch", "?"), rep.get("commit", "?")))
    print("=" * 78)
    for c in rep["checks"]:
        mark = "PASS" if c["ok"] else "FAIL"
        print(f"[{mark}] {c['id']:<15} {c['title']}")
        for f in c["findings"]:
            flag = "  ok " if f["ok"] else "  XX "
            print(f"{flag}{f['id']:<28} {f['status']:<17} {f['detail'][:200]}")
    s = rep["summary"]
    print("-" * 78)
    print(f"{s['checks']} checks, {s['findings']} findings, {s['failed']} failed, "
          f"{s['blocked']} blocked -> {s['verdict']}")


# ---------------------------------------------------------------------------
# selftest — every check must be able to fail
# ---------------------------------------------------------------------------
def _clone(src: Path, dest: Path) -> Path:
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    return dest


def selftest(root: Path) -> int:
    work = Path(tempfile.mkdtemp(prefix="lgd_pr_selftest_"))
    failures = []

    def expect_fail(name, fs):
        bad = [f for f in fs if not f["ok"]]
        print(f"  {'PASS' if bad else 'FAIL'}  {name}: "
              f"{len(bad)} failing finding(s)"
              + (f" — {bad[0]['detail'][:90]}" if bad else "  <-- CHECK CANNOT FAIL"))
        if not bad:
            failures.append(name)

    try:
        # links: a bogus URL and an absent marker must both fail
        bad_reg = work / "bad_registry.json"
        bad_reg.write_text(json.dumps({"external_standards": [
            {"id": "bogus-url", "url": "https://example.invalid/nope",
             "marker": "", "why": "selftest"},
            {"id": "marker-missing", "url": "https://example.com", "marker": "zzz-not-there",
             "why": "selftest"},
        ]}, ensure_ascii=False), encoding="utf-8")
        expect_fail("links/bogus-url", check_links(root, bad_reg))

        # outsider: break a gold test in a copy
        t1 = _clone(root, work / "t_outsider")
        (t1 / "demo1" / "test_demo1.py").write_text(
            "import sys\nprint('0/5')\nsys.exit(1)\n", encoding="utf-8")
        expect_fail("outsider/broken-test", check_outsider(t1, "worktree"))

        # docs-claims: claim four checks while the gate runs five
        t2 = _clone(root, work / "t_claims")
        p = t2 / "README.md"
        p.write_text(re.sub(r"\((\w+) checks\)", "(four checks)", read(p)), encoding="utf-8")
        expect_fail("docs-claims/wrong-count", check_docs_claims(t2))

        # parity: point the published-tree comparison at a commit that is not HEAD
        expect_fail("parity/stale-ref", check_parity(root, "HEAD~3"))

        # relative-links: point at a file that is not there
        t3 = _clone(root, work / "t_rel")
        p = t3 / "README.md"
        p.write_text(read(p) + "\nSee `docs/does_not_exist.py`.\n", encoding="utf-8")
        expect_fail("relative-links/missing-file", check_relative_links(t3))

        # citation: unserialisable title removal and an unresolvable DOI
        t4 = _clone(root, work / "t_cff")
        c = t4 / "CITATION.cff"
        c.write_text(re.sub(r"^title:.*$", "", read(c), flags=re.M), encoding="utf-8")
        expect_fail("citation/no-title", check_citation(t4))
        t5 = _clone(root, work / "t_cff_doi")
        c = t5 / "CITATION.cff"
        c.write_text(read(c) + '\ndoi: "10.5281/zenodo.999999999"\n', encoding="utf-8")
        expect_fail("citation/fake-doi", check_citation(t5))

        # license: disagree with the LICENSE file
        t6 = _clone(root, work / "t_lic")
        py = t6 / "pyproject.toml"
        py.write_text(re.sub(r'license\s*=\s*\{[^}]*\}', 'license = { text = "MIT" }', read(py)),
                      encoding="utf-8")
        expect_fail("license/mismatch", check_license(t6))

        # legal: strip the patent grant from a copy and the check must notice
        t6b = _clone(root, work / "t_legal")
        lic_copy = t6b / "LICENSE"
        lic_copy.write_text(
            re.sub(r"3\. Grant of Patent License.*?(?=\n\s*4\.)", "",
                   read(lic_copy), flags=re.S), encoding="utf-8")
        expect_fail("legal/no-patent-grant", check_legal(t6b))

        # public: a path that is not our repository
        expect_fail("public/nonexistent",
                    check_public(root, "https://raw.githubusercontent.com/Medxpert-org/"
                                       "lgd-engine-does-not-exist/main/README.md"))

        # machine: remove llms.txt
        t7 = _clone(root, work / "t_mach")
        (t7 / "llms.txt").unlink()
        expect_fail("machine/no-llms", check_machine(t7))

        # redteam: sabotage one probe so it can no longer fail against its
        # mutant, and the harness must report a vacuous probe rather than PASS.
        t8 = _clone(root, work / "t_redteam")
        probe = t8 / "review" / "redteam_probe.py"
        probe.write_text(
            read(probe).replace(
                'return (_sev(out.get("verdict")) >= 1), f"verdict={out.get(\'verdict\')}"',
                'return True, "always fine"', 1),
            encoding="utf-8")
        expect_fail("redteam/vacuous-probe", check_redteam(t8))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("-" * 78)
    if failures:
        print(f"SELFTEST FAIL — {len(failures)} check(s) cannot fail: {failures}")
        return 1
    print("SELFTEST PASS — every check produced a failing finding under mutation")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--only", default=None)
    ap.add_argument("--tree", default="head", choices=["head", "worktree"])
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    if args.selftest:
        return selftest(root)

    rep = run(root, args.only, args.tree)
    if not args.quiet:
        print_report(rep)
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        if not args.quiet:
            print(f"evidence written to {out}")
    return 0 if rep["summary"]["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
