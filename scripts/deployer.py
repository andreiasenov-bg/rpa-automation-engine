#!/usr/bin/env python3
"""
Lightweight HTTP deployer — runs inside Docker, triggers git pull.

Listens on port 9000. Any POST request runs `git pull` on the
mounted repo volume. uvicorn --reload then picks up file changes.

For Celery worker/beat restarts, POST to /restart-workers.
"""

import http.server
import json
import subprocess
import os
import sys

PORT = 9000
REPO_DIR = "/repo"


def _run(cmd: list[str], cwd: str = REPO_DIR) -> dict:
    """Run a command and return stdout/stderr/returncode."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=60
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


class DeployHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        path = self.path.rstrip("/")

        if path in ("", "/deploy", "/pull"):
            # Git pull
            result = _run(["git", "pull", "origin", "main"])
            self._json_response(200 if result["ok"] else 500, result)

        elif path == "/restart-workers":
            # Touch a file that could trigger celery restart
            # For now, just report that API auto-reloads via uvicorn
            result = {"ok": True, "message": "API auto-reloads via --reload. Celery workers need manual restart."}
            self._json_response(200, result)

        else:
            self._json_response(404, {"error": f"Unknown path: {path}"})

    def do_GET(self):
        path = self.path.rstrip("/")

        if path in ("", "/health", "/status"):
            # Show git status
            status = _run(["git", "status", "--short"])
            log = _run(["git", "log", "--oneline", "-5"])
            branch = _run(["git", "branch", "--show-current"])
            self._json_response(200, {
                "ok": True,
                "branch": branch.get("stdout", "?"),
                "recent_commits": log.get("stdout", ""),
                "dirty_files": status.get("stdout", ""),
            })
        else:
            self._json_response(404, {"error": f"Unknown path: {path}"})

    def _json_response(self, code: int, data: dict):
        body = json.dumps(data, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[deployer] {args[0]}")


if __name__ == "__main__":
    # Configure git safe directory (mounted volume)
    subprocess.run(["git", "config", "--global", "safe.directory", REPO_DIR],
                    capture_output=True)

    # If GITHUB_TOKEN is set, configure credential helper
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        subprocess.run(
            ["git", "config", "--global", "credential.helper",
             f"!f() {{ echo \"password={token}\"; }}; f"],
            capture_output=True,
        )
        print(f"[deployer] GitHub token configured")

    server = http.server.HTTPServer(("0.0.0.0", PORT), DeployHandler)
    print(f"[deployer] Listening on port {PORT}")
    print(f"[deployer] Repo: {REPO_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[deployer] Shutting down")
        server.server_close()
