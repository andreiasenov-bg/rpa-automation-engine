#!/usr/bin/env python3
"""
Lightweight HTTP deployer — runs inside Docker, triggers git pull.

Listens on port 9000. POST /deploy runs `git pull`, waits for
uvicorn reload, then runs system health checks automatically.

POST /deploy  → git pull + health check
GET  /status  → git log + branch info
GET  /health  → deployer alive check
"""

import http.server
import json
import subprocess
import os
import time
import urllib.request
import urllib.error

PORT = 9000
REPO_DIR = "/repo"
BACKEND_URL = "http://backend:8000"
# Deployer authentication token (required)
DEPLOY_TOKEN = os.environ.get("DEPLOY_TOKEN", "")
# Auth token is fetched on-demand for health checks
_AUTH_CACHE = {"token": None, "expires": 0}


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


def _get_auth_token() -> str:
    """Get a fresh JWT token for system-check calls."""
    now = time.time()
    if _AUTH_CACHE["token"] and _AUTH_CACHE["expires"] > now:
        return _AUTH_CACHE["token"]

    try:
        data = json.dumps({
            "email": os.environ.get("ADMIN_EMAIL", "admin@rpa-engine.com"),
            "password": os.environ.get("ADMIN_PASSWORD", "admin123!"),
        }).encode()
        req = urllib.request.Request(
            f"{BACKEND_URL}/api/v1/auth/login",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            _AUTH_CACHE["token"] = body.get("access_token", "")
            _AUTH_CACHE["expires"] = now + 3600  # cache for 1h
            return _AUTH_CACHE["token"]
    except Exception as e:
        print(f"[deployer] Auth failed: {e}")
        return ""


def _run_health_check() -> dict:
    """Call the backend system-check endpoint after deploy."""
    token = _get_auth_token()
    if not token:
        return {"ok": False, "error": "Could not authenticate for health check"}

    try:
        req = urllib.request.Request(
            f"{BACKEND_URL}/api/v1/system-check/",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": f"Health check failed: {e}"}


def _wait_for_reload(max_wait: int = 15) -> bool:
    """Wait for uvicorn to reload after file changes."""
    for i in range(max_wait):
        try:
            req = urllib.request.Request(f"{BACKEND_URL}/api/v1/health/")
            with urllib.request.urlopen(req, timeout=3):
                if i > 0:
                    print(f"[deployer] Backend back up after {i}s")
                return True
        except Exception:
            time.sleep(1)
    return False


def _restart_celery() -> dict:
    """Restart celery-beat and celery-worker via docker compose.

    Unlike the API (which uses --reload), Celery workers don't auto-detect
    code changes.  We need to restart them explicitly after a deploy.
    """
    results = {}
    for service in ("celery-beat", "celery-worker"):
        print(f"[deployer] Restarting {service}...")
        r = _run(["docker", "compose", "restart", service], cwd=REPO_DIR)
        results[service] = r
        if r["ok"]:
            print(f"[deployer] {service} restarted OK")
        else:
            print(f"[deployer] {service} restart FAILED: {r.get('stderr', r.get('error', '?'))}")
    return results


class DeployHandler(http.server.BaseHTTPRequestHandler):
    def _verify_token(self) -> bool:
        """Verify Authorization: Bearer <DEPLOY_TOKEN> header.

        Returns True if valid, False otherwise.
        """
        if not DEPLOY_TOKEN:
            print("[deployer] WARNING: DEPLOY_TOKEN not set!")
            return False

        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False

        token = auth_header[7:]  # Remove "Bearer " prefix
        return token == DEPLOY_TOKEN

    def do_POST(self):
        path = self.path.rstrip("/")

        # All POST endpoints require authentication
        if not self._verify_token():
            self._json_response(401, {"error": "Unauthorized: missing or invalid token"})
            return

        if path in ("", "/deploy", "/pull"):
            # Step 1: Git pull
            pull_result = _run(["git", "pull", "origin", "main"])
            if not pull_result["ok"]:
                self._json_response(500, {
                    "step": "git_pull",
                    "result": pull_result,
                })
                return

            # Step 2: Restart Celery workers (they don't auto-reload)
            celery_results = _restart_celery()

            # Step 3: Wait for uvicorn to reload
            print("[deployer] Waiting for uvicorn reload...")
            time.sleep(2)  # Give uvicorn time to detect changes
            backend_up = _wait_for_reload()

            # Step 4: Run health check
            health = {}
            if backend_up:
                print("[deployer] Running post-deploy health check...")
                health = _run_health_check()
            else:
                health = {"status": "unknown", "issues": ["Backend didn't respond after reload"]}

            self._json_response(200, {
                "deploy": pull_result,
                "celery_restart": celery_results,
                "backend_reloaded": backend_up,
                "health_check": health,
            })

        elif path == "/health-check":
            # Manual health check trigger (no git pull)
            health = _run_health_check()
            self._json_response(200, health)

        elif path == "/restart-workers":
            celery_results = _restart_celery()
            self._json_response(200, {
                "ok": True,
                "celery_restart": celery_results,
            })

        else:
            self._json_response(404, {"error": f"Unknown path: {path}"})

    def do_GET(self):
        path = self.path.rstrip("/")

        if path in ("", "/health", "/status"):
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
    subprocess.run(["git", "config", "--global", "safe.directory", REPO_DIR],
                    capture_output=True)

    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        subprocess.run(
            ["git", "config", "--global", "credential.helper",
             f"!f() {{ echo \"password={token}\"; }}; f"],
            capture_output=True,
        )
        print("[deployer] GitHub token configured")

    server = http.server.HTTPServer(("0.0.0.0", PORT), DeployHandler)
    print(f"[deployer] Listening on port {PORT}")
    print(f"[deployer] Repo: {REPO_DIR}")
    print(f"[deployer] POST /deploy = git pull + health check")
    print(f"[deployer] POST /health-check = health check only")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[deployer] Shutting down")
        server.server_close()
