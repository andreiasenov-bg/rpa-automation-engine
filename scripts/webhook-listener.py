#!/usr/bin/env python3
"""
Lightweight GitHub webhook listener for auto-deploy.
Listens on port 9000 for push events to main branch.
Runs auto-deploy.sh on each valid push.
"""

import http.server
import json
import subprocess
import os
import sys

PORT = 9000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_SCRIPT = os.path.join(SCRIPT_DIR, "auto-deploy.sh")


class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        # Check if it's a push to main
        ref = payload.get("ref", "")
        if ref == "refs/heads/main":
            print(f"[DEPLOY] Push to main detected, running deploy...")
            subprocess.Popen(
                ["bash", DEPLOY_SCRIPT],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Deploy triggered")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"Ignored push to {ref}".encode())

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Webhook listener active")

    def log_message(self, format, *args):
        print(f"[WEBHOOK] {args[0]}")


if __name__ == "__main__":
    os.chmod(DEPLOY_SCRIPT, 0o755)
    server = http.server.HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    print(f"[WEBHOOK] Listening on port {PORT}...")
    print(f"[WEBHOOK] Deploy script: {DEPLOY_SCRIPT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[WEBHOOK] Shutting down")
        server.server_close()
