"""Minimal structural validator for docs/openapi.yaml (local smoke only).

Checks (stdlib + PyYAML when available; degrades to a text scan if PyYAML
is absent so the zero-third-party MVP still gets a real answer):
  - file parses as YAML
  - openapi version / info present
  - paths /v1/judge (POST) and /v1/decisions (GET) exist with required ops
  - securitySchemes include bearerAuth (TLS/Bearer) and X-API-Key
  - GateReport schema carries verdict/per_judge/reasons/evidence/law_enforcements
Exit code 0 = all checks passed, 1 = any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE / "openapi.yaml"

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        failures.append(msg)


try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

raw = SPEC.read_text(encoding="utf-8")

if yaml is None:
    # Degraded text-scan mode (MVP keeps zero third-party deps at runtime;
    # PyYAML is the project's optional `yaml` extra).
    check("/v1/judge:" in raw, "text scan: /v1/judge path present")
    check("/v1/decisions:" in raw, "text scan: /v1/decisions path present")
    check("bearerAuth:" in raw, "text scan: bearerAuth scheme present")
    check("apiKeyAuth:" in raw, "text scan: apiKeyAuth (X-API-Key) present")
    check("GateReport:" in raw, "text scan: GateReport component present")
else:
    doc = yaml.safe_load(raw)
    check(isinstance(doc, dict), "YAML parses into a mapping")
    check(str(doc.get("openapi", "")).startswith("3.1"), "openapi version is 3.1.x")
    check(bool(doc.get("info", {}).get("title")), "info.title present")

    paths = doc.get("paths", {})
    j = paths.get("/v1/judge", {})
    d = paths.get("/v1/decisions", {})
    check("post" in j, "POST /v1/judge declared")
    check("requestBody" in j.get("post", {}), "POST /v1/judge has requestBody")
    check("200" in j.get("post", {}).get("responses", {}), "POST /v1/judge has 200 response")
    check("get" in d, "GET /v1/decisions declared")
    params = [p.get("name") for p in d.get("get", {}).get("parameters", [])]
    check("limit" in params, "GET /v1/decisions has limit query param")

    sec = doc.get("components", {}).get("securitySchemes", {})
    check("bearerAuth" in sec, "securityScheme: bearerAuth (TLS/Bearer)")
    check(sec.get("apiKeyAuth", {}).get("name") == "X-API-Key", "securityScheme: X-API-Key header")

    schemas = doc.get("components", {}).get("schemas", {})
    gr = schemas.get("GateReport", {})
    props = set(gr.get("properties", {}).keys())
    for key in ("verdict", "per_judge", "reasons", "evidence", "law_enforcements"):
        check(key in props, f"GateReport.{key} present")
    check(set(gr.get("required", [])) >= {"verdict", "per_judge"}, "GateReport required keys sane")

    cv = schemas.get("ChangeContext", {})
    check("change_type" in cv.get("required", []), "ChangeContext requires change_type")

print("-" * 60)
if failures:
    print(f"VALIDATION FAILED: {len(failures)} check(s) failed")
    sys.exit(1)
print("VALIDATION OK — openapi.yaml structurally consistent")
