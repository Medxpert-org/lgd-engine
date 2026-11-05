# Release checklist — v0.1.0

Why this file exists: the repository had **0 tags, 0 releases and no software
DOI** while the README presented it as a citable artifact. A release is not a
mood; it is a sequence of steps that either happened or did not. Each line
below is checkable, and the ones blocked on a human account say so instead of
being quietly skipped.

## 1. Before the tag (do in this order)

- [ ] `python framework/gate_bot.py` → exit 0, **5/5** checks (includes
      `readme-counts`). A release whose own gate is red is not a release.
- [ ] `python security/security_scan.py` → `clean: 0 findings`
- [ ] `python demo1/test_demo1.py` → 5/5 · `python demo2/test_demo2.py` → 26/26
- [ ] `python docs/validate_openapi.py` → 17/17 (install the `yaml` extra;
      the stdlib-only run reports `5/17 text-scan only` and must not be quoted
      as full validation)
- [ ] `python security/prompt_injection_defense.py` → `[summary] 6/6`
- [ ] `python lgd_engine/mcp_smoke.py` → SMOKE: PASS
- [ ] SSE smoke after generating both event paths → 6/6, no traceback
- [ ] `CHANGELOG.md` has the version's section, and nothing under it is
      described as done when it is not

## 2. Tag and GitHub Release

```bash
git checkout main && git pull
git tag -a v0.1.0 -m "LGD Engine v0.1.0 — theory-bound change gate (MVP)"
git push origin v0.1.0
gh release create v0.1.0 --title "v0.1.0 — theory-bound change gate (MVP)" \
  --notes-file release-prep/RELEASE_NOTES_v0.1.0.md
```

- [ ] Tag is annotated and points at a commit that is on `main`
- [ ] Release notes state the MVP boundary (what the gate does **not** judge)
- [ ] `CITATION.cff` `date-released` is filled with the tag date

## 3. Software DOI (Zenodo) — **blocked on the maintainer's account**

None of this can be done from the repository side; the webhook lives in the
maintainer's Zenodo account. Until it is on, the repo legitimately has no
software DOI, and `CITATION.cff` must **not** carry a fabricated one.

1. Sign in to Zenodo with the GitHub account that owns this repository.
2. Settings → GitHub → flip the repository **on** (Zenodo then reads its
   `.zenodo.json`, and archives every future release).
3. Create the GitHub Release (step 2). Zenodo archives it and mints a DOI.
4. Copy the **concept DOI** and the **version DOI** from the Zenodo record.
5. Add to `CITATION.cff`:
   ```yaml
   doi: "10.5281/zenodo.<version>"
   identifiers:
     - type: doi
       value: "10.5281/zenodo.<concept>"
       description: "Concept DOI (all versions)"
   ```
6. Update `README.md` (DOI badge) and `llms.txt` in the same commit.

- [ ] Zenodo webhook on (maintainer)
- [ ] Release archived (check the Zenodo record's file list, not just "success")
- [ ] DOI resolves: `curl -sI https://doi.org/10.5281/zenodo.<id>` → 302
- [ ] `CITATION.cff` updated and validated (`cffconvert` or GitHub's renderer)

## 4. After the DOI exists

- [ ] `README.md` badge and "cite this" line point at the DOI, not the repo URL
- [ ] The Zenodo record's title/authors match `CITATION.cff` (drift between the
      two is what reviewers notice first)
- [ ] `CHANGELOG.md` links the release
- [ ] A receipt is filed in the release channel saying which of the above ran
      and which did not

## Open item carried by this checklist

The README refers to a **14-link** ecosystem caliber while
`framework/ecosystem-map.md` binds **11** links. The 14-link document is not in
this repository or in the theory repository. If it is published, link it from
the README and add the mapping; until then the README states 14 as external and
does not restate the list.
