# Dockerfile — lgd-engine MVP container (local smoke, stdlib only, NOT published).
# Base image python:3.11-alpine was verified cached locally on the authoring
# machine (docker images, 2026-11-03) so this build needs no Docker Hub pull.
FROM python:3.11-alpine

WORKDIR /app
COPY . /app
ENV PYTHONUNBUFFERED=1
EXPOSE 8765

# One-shot in-container verdict smoke (goes to the container log), then serve
# the demo1 stdlib web handler on 0.0.0.0:8765 so the published port is usable.
# demo1/web.py's handler itself is reused — no new web code is introduced.
CMD python -c "import sys; sys.path.insert(0,'/app'); \
from lgd_engine.gate import GateEngine; \
from lgd_engine.judges.judge_510k import Judge510kChange; \
_r=GateEngine([Judge510kChange()]).evaluate({'change_type':'material_nonconforming','safety_impact':'none','recall_class':'none','predicate_unchanged':True,'evidence_sufficiency':'needs_supplement'}); \
_d=_r.to_dict(); print('SMOKE verdict='+_d['verdict']+' reasons='+str(len(_d['reasons']))+' evidence='+str(len(_d['evidence']))); \
from http.server import HTTPServer; from demo1.web import _H; \
HTTPServer(('0.0.0.0',8765),_H).serve_forever()"
