from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .guardian import SCQOSGuardian


def make_handler(guardian: SCQOSGuardian):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SCQOSACSGuardian/0.1.0"

        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/health":
                body = json.dumps({"status": "operational", "guardian": "SCQOS", "acs": "0.1.0"}).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

        def do_POST(self) -> None:
            if self.path != "/acs":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("content-length", "0"))
                if length <= 0 or length > 1_048_576:
                    raise ValueError("invalid body size")
                payload = json.loads(self.rfile.read(length))
                if isinstance(payload, list):
                    result = [guardian.process(item) for item in payload]
                else:
                    result = guardian.process(payload)
                body = json.dumps(result, separators=(",", ":")).encode()
                self.send_response(200)
            except Exception as exc:
                body = json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request", "data": {"reason": type(exc).__name__}}}).encode()
                self.send_response(400)
            self.send_header("content-type", "application/json")
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18888)
    parser.add_argument("--local-scqos", action="store_true", help="use deterministic in-process SCQOS stub for offline tests")
    args = parser.parse_args(argv)
    guardian = SCQOSGuardian(live_scqos=not args.local_scqos)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(guardian))
    print(f"SCQOS ACS Guardian listening on http://{args.host}:{args.port}/acs", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
