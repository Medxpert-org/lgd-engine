#!/usr/bin/env python3
"""build_report.py — render review/report.html from the evidence JSON.

The report is generated, not written by hand: every number in it comes from
review/evidence/pre_release_latest.json, so the page cannot drift from the run.
It is a single self-contained file (no CDN, no web font, no JS dependency) so it
opens from an email attachment or behind a filtered network.
"""
from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "review" / "evidence" / "pre_release_latest.json"
PROBE_EVIDENCE = ROOT / "review" / "evidence" / "redteam_after.json"
OUT = ROOT / "review" / "report.html"

STATUS_CLASS = {
    "pass": "ok", "pass_external": "ok-ext", "fail": "bad",
    "blocked": "warn", "blocked_by_target": "warn", "error": "bad",
}

# Findings from the two independent seats. Kept here as data so the page and the
# markdown review cannot disagree about what is fixed.
REDTEAM = [
    ("R1", "Fail-open: an unclassified change_type returned GO with 0 reasons and an empty evidence package",
     "fixed", "unknown/missing change type → hold (R-MAJ-06); blank refs are not evidence; 3 invariants"),
    ("R2", "Verdict softening: per_judge HOLD while the aggregate said REJECT",
     "fixed", "a major rule can escalate but never soften a veto; invariant veto-not-softened"),
    ("R3", "A judge exception printed REJECT and exited 2, exactly like a real veto",
     "fixed", "report.errors + exit 3 for tool failure, 64 for usage; REJECT still exits 2"),
    ("R4", "Gate could be turned green: stub demo1/selftest.py, or a sys.exit(0) test",
     "fixed", "one canonical test path; shadow file fails; summary must report N/N cases and N/N invariants"),
    ("R5", "'No plaintext keys' was narrower than its name (AWS secret, db_password, JWT)",
     "fixed", "patterns added and verified red"),
    ("R6", "Malformed YAML passed when PyYAML was absent — the CI-realistic path",
     "fixed", "stdlib fallback refuses unbalanced collections; malformed files now FAIL cleanly instead of crashing"),
    ("R7", "entry as a list bypassed the traversal check",
     "fixed", "list entries are checked; verified red"),
    ("R8", "Three release surfaces, three gate counts (5/5 vs 4/4 vs 5)",
     "fixed", "one check reads all three docs; all now say 6/6"),
    ("R9", "'7-dimension review closed, no open high-severity findings' with no artifact in the tree",
     "fixed", "claim removed from README/llms.txt/release-prep; replaced by a pointer to this review"),
    ("R10", "README said zero-evidence go is 'rejected'; the code downgrades to hold",
     "fixed", "prose now matches law 2 and the implementation"),
    ("R11", "CI did not run the suites the docs said were 'enforced in CI'",
     "fixed", "OpenAPI, injection/security and SSE smoke added to the workflow; demo2 moved into gate_bot"),
    ("R12", "Predicate inversion: predicate_unchanged=false (the worse direction) scored better than true",
     "fixed", "new R-MAJ-08-predicate-changed; probe A1 sweeps the axis from four base change types"),
    ("R13", "postmarket L2-EVIDENCED was unreachable dead code — that domain's law was decorative",
     "fixed", "branch restructured so law 2 fires and appears in the reason chain; probe C2"),
    ("R14", "MCP role was read, logged and quoted in denials, then never consulted; the documented {ctx:…} wrapper was ignored; non-object arguments were judged",
     "fixed", "declared ROLE_TOOLS table failing closed, wrapper honoured, -32602 on bad arguments; probes D1/D3/D4"),
    ("R15", "Published contract drifted from code: enum missing supplier_substitution, source_refs typed as strings, six dead mvp/ paths, an example naming a domain and rule that do not exist",
     "fixed", "contract corrected; docs/validate_openapi.py 20/20 holds contract and code in lockstep; probes F1/F2"),
    ("R16", "Inverted evidence axis: evidence_sufficiency=none returned go while needs_supplement held",
     "fixed", "R-MAJ-03 covers both values; probe A1"),
    ("R17", "A raising rule predicate was swallowed (except: pass) — fail open; unknown enum values and a Class 2 recall outside maintenance_execution also rode out as go",
     "fixed", "predicate errors hold; every enumerated axis holds on an unknown value; R-MAJ-07; probes C3/C4/C5/E2"),
]

OUTSIDER = [
    ("pip install \"lgd-engine[yaml]\" 404s (not on PyPI)", "fixed"),
    ("Gate count disagreed across three release docs (4/4 vs 5/5)", "fixed"),
    ("No prerequisites section anywhere", "fixed"),
    ("SSE smoke documented as 'self-hosts, asserts, exits' with no precondition", "fixed"),
    ("demo1/test_ecosystem.py produced 6/6 that nobody documented", "fixed"),
    ("Usage errors exited 2, indistinguishable from REJECT", "fixed"),
    ("lgd-gate console has no --all while the docs show it", "open"),
    ("Docker / docker compose / npm smoke documented but never verified here", "not-verified"),
    ("Portal page does not mention this repository", "open"),
]


def esc(s: str) -> str:
    return html.escape(str(s))


def chip(status: str) -> str:
    cls = STATUS_CLASS.get(status, "warn")
    label = {"ok": "PASS", "ok-ext": "PASS*", "bad": "FAIL",
             "warn": "BLOCKED", "error": "ERROR"}[cls]
    return f'<span class="chip {cls}">{label}</span>'


def main() -> int:
    rep = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    s = rep["summary"]
    checks = rep["checks"]
    total = s["findings"]

    link_rows = []
    for c in checks:
        for f in c["findings"]:
            if "url" in f:
                link_rows.append(f)

    klasses = {"ok": 0, "ok-ext": 0, "bad": 0, "warn": 0}
    for f in link_rows:
        klasses[STATUS_CLASS.get(f["status"], "warn")] += 1

    def rows(items, cols):
        out = []
        for it in items:
            tds = "".join(f"<td>{esc(x) if i == 0 else x}</td>" for i, x in enumerate(it))
            out.append(f"<tr>{tds}</tr>")
        return "\n".join(out)

    rt_rows = []
    for rid, what, st, fix in REDTEAM:
        badge = ('<span class="chip ok">FIXED</span>' if st == "fixed"
                 else '<span class="chip bad">OPEN</span>')
        rt_rows.append(f"<tr><td class=mono>{rid}</td><td>{esc(what)}</td><td>{badge}</td>"
                       f"<td class=note>{esc(fix)}</td></tr>")
    os_rows = []
    for what, st in OUTSIDER:
        badge = ('<span class="chip ok">FIXED</span>' if st == "fixed"
                 else ('<span class="chip warn">NOT VERIFIED</span>' if st == "not-verified"
                       else '<span class="chip bad">OPEN</span>'))
        os_rows.append(f"<tr><td>{esc(what)}</td><td>{badge}</td></tr>")

    # Probe matrix — straight from the harness's own evidence file, grouped by
    # the property family each probe belongs to.
    probe_rows, probe_families = [], {}
    try:
        pe = json.loads(PROBE_EVIDENCE.read_text(encoding="utf-8"))
        for p in pe.get("probes", []):
            fam = p.get("family", "other")
            probe_families[fam] = probe_families.get(fam, 0) + 1
            badge = ('<span class="chip ok">PASS</span>' if p["status"] == "PASS"
                     else ('<span class="chip warn">BLOCKED</span>' if p["status"] == "BLOCKED"
                           else '<span class="chip bad">FAIL</span>'))
            probe_rows.append(f"<tr><td class=mono>{esc(p['id'])}</td><td class=mono>{esc(fam)}</td>"
                              f"<td>{esc(p['desc'])}</td><td>{badge}</td>"
                              f"<td class=note>{esc(p.get('detail',''))[:120]}</td></tr>")
    except Exception:
        pass

    check_rows = []
    for c in checks:
        badge = '<span class="chip ok">PASS</span>' if c["ok"] else '<span class="chip bad">FAIL</span>'
        n = len(c["findings"])
        bad = sum(1 for f in c["findings"] if not f["ok"])
        check_rows.append(f"<tr><td class=mono>{esc(c['id'])}</td><td>{esc(c['title'])}</td>"
                          f"<td>{badge}</td><td class=num>{n - bad}/{n}</td></tr>")

    link_html = "\n".join(
        f'<tr><td class=mono>{esc(f["id"])}</td><td>{chip(f["status"])}</td>'
        f'<td><a href="{esc(f.get("url",""))}" target="_blank" rel="noopener">{esc(f.get("url",""))}</a></td>'
        f'<td class=note>{esc(f["detail"])}</td></tr>'
        for f in sorted(link_rows, key=lambda x: (x.get("group") != "external_standards", x["id"]))
    )

    # Two verdicts, and they are different questions:
    #   machine — did every automated check pass on this commit?
    #   release — is the world able to see it? (branch, DOI, CLA)
    # The page must not collapse them into one green tick.
    machine = s.get("verdict", "FAIL")
    machine_cls = {"PASS": "ok", "BLOCKED": "warn", "FAIL": "bad"}.get(machine, "bad")
    open_rt = [r for r in REDTEAM if r[2] != "fixed"]
    when = rep["generated_at"]
    machine_text = {
        "PASS": "every automated check passed on this commit",
        "BLOCKED": "every automated check that ran passed, but at least one vantage "
                   "could not be reached — that is not a pass, and the page says so",
        "FAIL": "at least one automated check failed on this commit",
    }.get(machine, "the run did not produce a verdict")

    # "Pushed" and "merged" are different answers, and the page must not flatten
    # them into "the fixes are still only on this branch" — that sentence was true
    # before the push and became a lie the moment it landed on the remote.
    _parity = {f["id"]: f for c in checks if c["id"] == "parity" for f in c["findings"]}
    _pushed, _sha = _parity.get("parity-pushed"), _parity.get("parity-sha")
    if _pushed and _pushed["ok"] and _sha and not _sha["ok"]:
        # Quote the two findings rather than paraphrasing them: "pushed" here may
        # rest on this clone's cache when the remote was unreachable, and a reader
        # deserves to see which of the two answers they are being given.
        release_reasons = (f"the commit is on its branch but not merged ({_sha['detail']}). "
                           f"Push status per this run: {_pushed['detail']}. There is also no "
                           f"DOI or tag yet, and no CLA/DCO record for a standards contribution")
    else:
        release_reasons = ("the fixes are not on a ref a stranger can fetch, there is no DOI or "
                           "tag yet, and there is no CLA/DCO record for a standards contribution")

    # Every finding that is not a pass, with its own sentence. A check-level
    # FAIL badge without this is a verdict nobody can act on.
    blocking = [(c["id"], f["id"], f["detail"], f["status"])
                for c in checks for f in c["findings"] if not f["ok"]]
    blocking_html = "\n".join(
        f'<tr><td class=mono>{esc(cid)}</td><td class=mono>{esc(fid)}</td>'
        f'<td>{chip(status)}</td><td>{esc(detail)}</td></tr>'
        for cid, fid, detail, status in blocking) or \
        '<tr><td colspan=4 class=note>none — every finding on this commit is a pass</td></tr>'

    # Probe count comes from the redteam check's own finding, not from a constant.
    probe_n = 0
    for c in checks:
        if c["id"] == "redteam":
            for f in c["findings"]:
                m = re.search(r"(\d+)/\d+ probes", f.get("detail", ""))
                if m:
                    probe_n = int(m.group(1))

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pre-release review — lgd-engine</title>
<style>
:root{{
  --ink:#15181d; --muted:#5b6472; --line:#e3e7ee; --bg:#f7f8fa; --card:#fff;
  --ok:#0f7b4f; --okbg:#e7f6ee; --bad:#b4232b; --badbg:#fdeced;
  --warn:#8a5a00; --warnbg:#fdf3e0; --accent:#1f4fd8;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue","Noto Sans SC",sans-serif;}}
.wrap{{max-width:1080px;margin:0 auto;padding:40px 24px 72px}}
header{{border-bottom:1px solid var(--line);padding-bottom:20px;margin-bottom:28px}}
.eyebrow{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}
h1{{font-size:30px;line-height:1.25;margin:8px 0 10px;letter-spacing:-.01em}}
.sub{{color:var(--muted);font-size:14px}}
.verdict{{display:flex;gap:16px;align-items:center;margin:26px 0 8px;padding:18px 20px;
 border:1px solid var(--line);border-left:5px solid var(--bad);background:var(--card);border-radius:10px}}
.verdict b{{font-size:19px;color:var(--bad);letter-spacing:.02em}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:22px 0 34px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
.card .n{{font-size:26px;font-weight:650;letter-spacing:-.02em}}
.card .k{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}
h2{{font-size:18px;margin:38px 0 12px;letter-spacing:-.01em}}
h2 .hint{{font-size:13px;color:var(--muted);font-weight:400;margin-left:8px}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
 border-radius:10px;overflow:hidden;font-size:14px}}
th{{text-align:left;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);
 background:#fbfcfd;padding:10px 12px;border-bottom:1px solid var(--line);font-weight:600}}
td{{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}}
tr:last-child td{{border-bottom:none}}
.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.note{{color:var(--muted);font-size:13px}}
a{{color:var(--accent);text-decoration:none;word-break:break-all}}
a:hover{{text-decoration:underline}}
.chip{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:650;
 letter-spacing:.04em;white-space:nowrap}}
.chip.ok{{background:var(--okbg);color:var(--ok)}}
.chip.bad{{background:var(--badbg);color:var(--bad)}}
.chip.warn{{background:var(--warnbg);color:var(--warn)}}
ul{{margin:10px 0 0;padding-left:20px}} li{{margin:6px 0}}
footer{{margin-top:44px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;background:#eef1f6;
 padding:1px 5px;border-radius:4px}}
@media print{{body{{background:#fff}} .card,table{{break-inside:avoid}}}}
</style></head><body><div class="wrap">

<header>
  <div class="eyebrow">Pre-release review · generated {esc(when)}</div>
  <h1>lgd-engine — can an outside reader reach it, run it, and verify it?</h1>
  <div class="sub">Repository <span class="mono">Medxpert-org/lgd-engine</span> · branch
  <span class="mono">fix/s6-review-20261104</span> · commit <span class="mono">{esc(rep.get("commit",""))}</span></div>
</header>

<div class="verdict">
  <span class="chip {machine_cls}" style="font-size:14px;padding:6px 12px">MACHINE · {esc(machine)}</span>
  <div><b>{esc(machine)}</b> — {esc(machine_text)}. {s["failed"]} failing finding(s),
  {s["blocked"]} blocked vantage(s), {total} findings across {s["checks"]} automated checks.
  <br><b>RELEASE · BLOCKED</b> — not because of the code: {esc(release_reasons)}.
  {len(open_rt)} red-team item(s) still open.</div>
</div>

<div class="cards">
  <div class="card"><div class="n">{s["checks"]}</div><div class="k">automated checks</div></div>
  <div class="card"><div class="n">{total}</div><div class="k">findings</div></div>
  <div class="card"><div class="n">{klasses["ok"] + klasses["ok-ext"]}/{len(link_rows)}</div><div class="k">links reachable</div></div>
  <div class="card"><div class="n">{probe_n}</div><div class="k">adversarial probes</div></div>
  <div class="card"><div class="n">{sum(1 for r in REDTEAM if r[2]=="fixed")}/{len(REDTEAM)}</div><div class="k">red-team items closed</div></div>
</div>

<h2>1. Automated checks<span class="hint">exit code 1 on any failure; <code>--selftest</code> proves each can fail</span></h2>
<table><thead><tr><th>Check</th><th>What it tests</th><th>Result</th><th class=num>Findings</th></tr></thead>
<tbody>
{chr(10).join(check_rows)}
</tbody></table>

<h3>Everything that is not a pass on this commit</h3>
<table><thead><tr><th>Check</th><th>Finding</th><th>Status</th><th>What was observed</th></tr></thead>
<tbody>
{blocking_html}
</tbody></table>

<h2>2. Cited sources — every one fetched, not remembered<span class="hint">marker text must appear in the body, so a soft-404 cannot pass</span></h2>
<table><thead><tr><th>Source</th><th>Status</th><th>URL</th><th>What was observed</th></tr></thead>
<tbody>
{link_html}
</tbody></table>

<h2>3. Red team — two rounds, and what came of them<span class="hint">S7: an independent seat told to distrust the author · 2026-11-04: an executable probe harness</span></h2>
<table><thead><tr><th>#</th><th>Finding</th><th>Status</th><th>Resolution</th></tr></thead>
<tbody>
{chr(10).join(rt_rows)}
</tbody></table>

<h2>4. Probe matrix — the executable half of the red team<span class="hint">{probe_n} probes · {esc(", ".join(f"{k} {v}" for k, v in sorted(probe_families.items())))}</span></h2>
<table><thead><tr><th>#</th><th>Family</th><th>Property under test</th><th>Result</th><th>What was observed</th></tr></thead>
<tbody>
{chr(10).join(probe_rows) if probe_rows else '<tr><td colspan=5 class=note>probe evidence not available for this run</td></tr>'}
</tbody></table>

<h2>5. Outsider test — a stranger following only the docs<span class="hint">18 gaps reported; those acted on are listed</span></h2>
<table><thead><tr><th>Gap</th><th>Status</th></tr></thead>
<tbody>
{chr(10).join(os_rows)}
</tbody></table>

<h2>6. Why this is the gate</h2>
<ul>
<li><b>ITU-T A.1 §3.1.6</b> — material submitted as a contribution is presumed to carry no
distribution restrictions; §3.1.7 requires a software copyright and licensing declaration.</li>
<li><b>W3C Community Groups</b> — participation requires the CLA; contributions are recorded publicly
(preferably as pull requests).</li>
<li><b>Zenodo</b> — a <code>.zenodo.json</code> silently overrides <code>CITATION.cff</code> for the release archive.</li>
<li><b>FORCE11</b> — unique identification, persistence, accessibility, specificity: a citation without a
resolvable identifier fails the principle, so <code>CITATION.cff</code> carries no DOI until Zenodo mints one.</li>
</ul>

<footer>
Generated by <span class="mono">review/build_report.py</span> from
<span class="mono">review/evidence/pre_release_latest.json</span>, which names the
commit the review examined (<span class="mono">{esc(rep.get("commit",""))}</span>) —
the commit that stores this page is necessarily one later. Re-run:
<code>python review/pre_release_review.py --json review/evidence/pre_release_latest.json &amp;&amp; python review/build_report.py</code>.
This page is self-contained: no CDN, no web font, no JavaScript.
</footer>
</div></body></html>
"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(doc)} bytes) at {time.strftime('%H:%M:%S')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
