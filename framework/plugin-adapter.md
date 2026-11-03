# Plugin Adapter Pattern — v1.0 draft

Three extension points, all open-for-extension / closed-for-modification. The core
`lgd.gate` aggregation never changes when you add a new AI host, a new judge, or a new skill.

---

## 1. Extension point A — new AI host = insert one adapter

All adapters implement the same Provider interface. Two transports ship as templates:

### 1.1 stdio adapter (local, one process)

```python
# lgd/adapters/my_host_stdio.py  (template)
from lgd.adapters.base import ProviderAdapter

class MyHostStdio(ProviderAdapter):
    name = "my-host"
    transport = "stdio"

    def read_message(self):
        # one line per JSON-RPC request on stdin
        line = input()
        return self._parse_json(line)

    def write_message(self, obj: dict) -> None:
        print(self._to_json(obj), flush=True)

    def call_judge(self, ctx: dict) -> dict:
        # delegates to the same core every host uses
        from lgd.gate import aggregate
        return aggregate(ctx)          # <- shared judgment core, unchanged
```

### 1.2 streamable-HTTP adapter (remote host, e.g. Qwen Node runtime)

```python
# lgd/adapters/my_host_http.py  (template)
from fastapi import FastAPI, Request
from lgd.adapters.base import ProviderAdapter

class MyHostHttp(ProviderAdapter):
    name = "my-host"
    transport = "streamable-http"

    def build_app(self) -> FastAPI:
        app = FastAPI()

        @app.post("/mcp")
        async def handle(req: Request):
            api_key = req.headers.get("X-API-Key", "")
            if not self._auth(api_key):
                return {"error": "unauthorized"}          # RBAC gate before any work
            ctx = await req.json()
            from lgd.gate import aggregate
            return aggregate(ctx)

        return app
```

Discovery rule: drop the file under `lgd/adapters/` + register it in the adapter registry;
`skill.list` exposes it to every AI host through the same MCP tools. No core edit.

## 2. Extension point B — new judge = register one DomainJudge

Core interface (mirrors `lgd/judges/base.py` from the engine workstream):

```python
# lgd/judges/base.py  (contract, reference)
from abc import ABC, abstractmethod

class DomainJudge(ABC):
    domain: str

    @abstractmethod
    def evaluate(self, ctx: dict) -> dict:
        """Return {"verdict": "go|hold|reject", "reasons": [...], "citations": [...]}."""

    def on_internal_error(self, exc: Exception) -> dict:
        # fail closed: never fake "go" — degrade to "hold" with reason logged
        return {"verdict": "hold", "reasons": [f"{self.domain} degraded: {exc}"], "citations": []}
```

To add the 14th domain: create `lgd/judges/my_domain.py` subclassing `DomainJudge`, add
one manifest line, and it enters the router. Existing 13 judges are untouched — open/closed.

## 3. Extension point C — new skill = ship one skill.yaml

See `skill-manifest-spec.md`. Install-time discovery: read manifest → index into the
skill directory SSOT → `skill.list` surfaces it.

## 4. Open/closed landing map

| Change you need | File(s) you add | File(s) you must NOT modify |
|---|---|---|
| Support a new AI host | `lgd/adapters/<host>_<transport>.py` | `lgd/gate.py`, existing adapters |
| Add a new judgment domain | `lgd/judges/<domain>.py` + manifest | `lgd/judges/base.py`, router core |
| Add a new capability | `skills/<name>/skill.yaml` + entry module | core gate aggregation |
