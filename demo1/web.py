"""Minimal optional web UI for Demo1 (stdlib http.server, no Flask).

Run:
    python -m demo1.web
Then open http://127.0.0.1:8765
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_MVP = _HERE.parent
if str(_MVP) not in sys.path:
    sys.path.insert(0, str(_MVP))

from lgd_engine.gate import GateEngine                       # noqa: E402
from lgd_engine.judges.judge_510k import Judge510kChange      # noqa: E402


_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>lgd-engine Demo1 · 510(k) Change Gate</title>
<style>
 body{font-family:system-ui,Segoe UI,Helvetica,Arial,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;background:#f7f7f9;color:#222}
 h1{font-size:1.4rem} label{display:block;margin-top:.6rem;font-weight:600}
 input,select,textarea{width:100%;padding:.4rem;margin-top:.2rem;border:1px solid #ccc;border-radius:4px}
 button{margin-top:1rem;background:#2b6cb0;color:#fff;border:0;padding:.6rem 1.2rem;border-radius:4px;cursor:pointer}
 #out{margin-top:1.5rem;white-space:pre-wrap;background:#fff;border:1px solid #ddd;border-radius:6px;padding:1rem}
 .go{color:#1a7f37}.hold{color:#b45309}.reject{color:#b91c1c}
</style></head><body>
<h1>lgd-engine v0.1.0 · Demo1 — 510(k) Change Gate</h1>
<p>Fill in the change context; the gate returns GO / HOLD / REJECT with reason chain.</p>
<form id="f">
 <label>device_risk_class
  <select name="device_risk_class"><option>II</option><option>I</option><option>III</option></select></label>
 <label>regulatory_path
  <select name="regulatory_path"><option>510k</option><option>pma</option><option>nmpa_import</option></select></label>
 <label>change_type
  <select name="change_type">
   <option>label_correction</option><option>label_clarification</option>
   <option>label_expansion</option><option>function_config_change</option>
   <option>process_change_control</option><option>material_nonconforming</option>
   <option>design_defect</option><option>maintenance_execution</option>
  </select></label>
 <label>safety_impact
  <select name="safety_impact"><option>none</option><option>limited_reversible</option><option>severe_life_threatening</option></select></label>
 <label>evidence_sufficiency
  <select name="evidence_sufficiency"><option>sufficient</option><option>needs_supplement</option><option>none</option></select></label>
 <label>recall_class
  <select name="recall_class"><option>none</option><option>class1</option><option>class2</option><option>class3</option></select></label>
 <label>requires_submission <input type="checkbox" name="requires_submission"></label>
 <label>predicate_unchanged <input type="checkbox" name="predicate_unchanged" checked></label>
 <label>device_description <textarea name="device_description" rows="2"></textarea></label>
 <button type="submit">Run gate</button>
</form>
<pre id="out"></pre>
<script>
 document.getElementById('f').addEventListener('submit', async(e)=>{
   e.preventDefault();
   const fd=new FormData(e.target);
   const ctx={};
   fd.forEach((v,k)=>{
     if(k==='requires_submission'||k==='predicate_unchanged') ctx[k]=(v==='on');
     else ctx[k]=v;
   });
   const r=await fetch('/judge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(ctx)});
   document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2);
 });
</script></body></html>
"""


class _H(BaseHTTPRequestHandler):
    def _engine(self):
        e = GateEngine()
        e.register(Judge510kChange())
        return e

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = _HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path != "/judge":
            self.send_response(404); self.end_headers(); return
        n = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n).decode("utf-8")
        ctx = json.loads(raw or "{}")
        rep = self._engine().evaluate(ctx)
        body = json.dumps(rep.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main(host="127.0.0.1", port=8765):
    srv = HTTPServer((host, port), _H)
    print(f"web UI: http://{host}:{port}  (Ctrl+C to stop)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
