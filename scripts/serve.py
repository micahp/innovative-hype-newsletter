#!/usr/bin/env python3
"""serve.py — static server for web/ + the manual card-verdict API.

Micah 2026-08-27: grading the cards stays MANUAL. Each card on the pipeline
page gets good/bad buttons; POST /api/verdict appends the verdict to
card_verdicts.jsonl and GET /api/verdicts returns the latest verdict per
card so the page can show its saved state. Verdicts are a LOG: nothing
reads them into prompts or rankings unless he says so.

Usage: python3 scripts/serve.py [port]   (default 8099, same as serve.sh)
"""
import json
import os
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "web")
VERDICTS = os.path.join(REPO, "card_verdicts.jsonl")
_lock = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB, **kwargs)

    def log_message(self, fmt, *args):
        # Static hits are noise; API calls are the interesting surface.
        if args and "/api/" in str(args[0]):
            super().log_message(fmt, *args)

    def _read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/verdicts":
            latest = {}
            try:
                with open(VERDICTS) as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                        except ValueError:
                            continue
                        latest[r.get("narrative", "")] = r
            except FileNotFoundError:
                pass
            self._json({"verdicts": latest})
            return
        super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/verdict":
            self.send_error(404)
            return
        try:
            row = json.loads(self._read_body())
            narrative = str(row["narrative"]).strip()
            verdict = str(row["verdict"]).strip()
            if not narrative:
                raise ValueError("empty narrative")
            if verdict not in ("good", "bad", "clear"):
                raise ValueError("verdict must be good, bad or clear")
        except Exception:
            self._json({"ok": False, "error": "need JSON {narrative, verdict: good|bad|clear}"},
                       status=400)
            return
        rec = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "narrative": narrative,
            "verdict": verdict,
            "grade": str(row.get("grade") or "")[:8],
            "kicker": str(row.get("kicker") or "")[:80],
        }
        with _lock:
            with open(VERDICTS, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._json({"ok": True})


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"serving web/ + verdict API on http://localhost:{port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
