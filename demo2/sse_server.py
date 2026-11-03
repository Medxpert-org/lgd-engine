"""sse_server.py — minimal Server-Sent Events push layer over demo2/events.jsonl.

Mode ④ (SSE event stream) of the 7 integration modes — BETA EXAMPLE.

Honest status: events.jsonl is the append-only event log Demo2 already writes
(one JSON object per seat action; see demo2/events.py). This server is a thin
*incremental push* layer: on connect it replays existing lines, then tails the
file and forwards newly appended lines as SSE `event:` frames. It is NOT a
production service — no auth, no backpressure, local loopback only. stdlib
only (zero third-party deps).

Run:
    python -m demo2.sse_server                 # 127.0.0.1:8770
    python -m demo2.sse_server --port 8770

Smoke client (stdlib):
    python demo2/sse_server.py --smoke
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_LOG = HERE / "events.jsonl"

# The six event types emitted by demo2/events.py EventLog.VALID_TYPES.
EVENT_TYPES = ("POSTED", "COMMENTED", "HOLDED", "VOTED", "FINALIZED", "DECISION_LOGGED")


def _tail_events(path: Path, stop: threading.Event, interval: float = 0.5):
    """Yield event dicts: replay existing content once, then follow new appends."""
    pos = 0
    while not stop.is_set():
        if not path.exists():
            stop.wait(interval)
            continue
        with open(path, "r", encoding="utf-8") as f:
            f.seek(pos)
            lines = f.readlines()
            pos = f.tell()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
        stop.wait(interval)


class _H(BaseHTTPRequestHandler):
    log_path = DEFAULT_LOG  # overridden in main()

    def do_GET(self):
        if self.path not in ("/events/stream", "/events"):
            body = b"not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        stop = threading.Event()
        try:
            for ev in _tail_events(self.log_path, stop):
                etype = ev.get("type", "message")
                payload = json.dumps(ev, ensure_ascii=False)
                # SSE frame: "event:<type>\ndata:<json>\n\n"
                self.wfile.write(f"event: {etype}\ndata: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client closed the stream (browser tab closed, smoke client got what
            # it came for). Windows reports this as ConnectionAbortedError
            # (WinError 10053), not BrokenPipeError — catching only the POSIX
            # pair printed a traceback that looked like a server fault.
            pass
        finally:
            stop.set()

    def log_message(self, fmt, *args):  # quieter console
        sys.stderr.write(f"[sse] {self.address_string()} {fmt % args}\n")


class _QuietServer(ThreadingHTTPServer):
    """Threading server that treats a client hang-up as an event, not a fault.

    An SSE stream is meant to be abandoned: a browser tab closes, and the smoke
    client exits as soon as it has seen the six event types. CPython surfaces
    that as ConnectionResetError / ConnectionAbortedError (Windows: 10054 /
    10053) and socketserver's default ``handle_error`` prints a full traceback
    that reads like a server crash — the check passes while the log says FAIL.
    Only those three types are silenced; every other exception still reaches
    the default handler.
    """

    daemon_threads = True

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def smoke_client(host: str, port: int, want_types: int = 6, timeout: float = 10.0) -> int:
    """Connect to /events/stream, collect event types until all six seen or timeout."""
    import socket

    want = set(EVENT_TYPES)
    got: set[str] = set()
    buf = ""
    deadline = time.time() + timeout

    sock = socket.create_connection((host, port), timeout=timeout)
    sock.settimeout(1.0)
    request = (
        f"GET /events/stream HTTP/1.1\r\nHost: {host}:{port}\r\n"
        "Accept: text/event-stream\r\nConnection: close\r\n\r\n"
    )
    sock.sendall(request.encode("utf-8"))

    print(f"[smoke] connected to http://{host}:{port}/events/stream")
    try:
        while time.time() < deadline and got < want:
            try:
                chunk = sock.recv(65535).decode("utf-8", errors="replace")
            except socket.timeout:
                continue
            if not chunk:
                break
            buf += chunk
            while "\n\n" in buf:
                frame, buf = buf.split("\n\n", 1)
                etype = None
                for line in frame.split("\n"):
                    if line.startswith("event: "):
                        etype = line[len("event: "):].strip()
                    if line.startswith("data: "):
                        try:
                            ev = json.loads(line[len("data: "):])
                        except json.JSONDecodeError:
                            continue
                        t = ev.get("type")
                        if t:
                            got.add(t)
                if etype:
                    print(f"[smoke] event frame received: event: {etype}")
    finally:
        sock.close()

    missing = want - got
    print("-" * 60)
    print(f"[smoke] received types ({len(got)}/{len(want)}): {sorted(got)}")
    if missing:
        print(f"[smoke] MISSING: {sorted(missing)}")
        if not got:
            print("[smoke] The event log is empty — generate events first:")
        elif "HOLDED" in missing:
            print("[smoke] HOLDED only appears on a hold path — also run:")
        else:
            print("[smoke] Regenerate the missing event types, then retry:")
        print("        python -m demo2.session --case demo2/case_gate_report.json --auto")
        print("        python -m demo2.session --case demo2/case_gate_report_critical.json --auto")
        return 1
    print("[smoke] ALL SIX event types received (POSTED/COMMENTED/HOLDED/VOTED/FINALIZED/DECISION_LOGGED)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    ap.add_argument("--smoke", action="store_true",
                    help="run the stdlib smoke client against a running server")
    args = ap.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")
        print(f"[sse] created empty event log {log_path} — run demo2 first to populate events")
    _H.log_path = log_path

    if args.smoke:
        # Self-hosted smoke: start the server in a thread, stream, then exit.
        # (R4 role test 2026-11-03: --smoke used to expect an externally running
        # server, which made the documented one-liner fail for a fresh clone.)
        srv = _QuietServer((args.host, args.port), _H)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            rc = smoke_client(args.host, args.port)
        finally:
            srv.shutdown()
            srv.server_close()
        return rc

    srv = _QuietServer((args.host, args.port), _H)
    print(f"SSE server: http://{args.host}:{args.port}/events/stream  (tail {log_path})  Ctrl+C to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
