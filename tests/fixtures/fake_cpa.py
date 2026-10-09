#!/usr/bin/env python3
"""Minimal local CPA fixture for executor integration tests."""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: fake_cpa.py <port> <token>", file=sys.stderr)
        return 2
    port = int(sys.argv[1])
    expected = sys.argv[2]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/v1/models":
                self.send_response(404)
                self.end_headers()
                return
            auth = self.headers.get("Authorization", "")
            if auth != "Bearer " + expected:
                self.send_response(401)
                self.end_headers()
                return
            body = json.dumps({"data": []}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = HTTPServer(("127.0.0.1", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

