#!/usr/bin/env python3
"""
Lightweight HTTP deployer — runs inside Docker, triggers git pull.

Listens on port 9000. All POST/PUT endpoints require DEPLOY_TOKEN auth.

POST /deploy        → git pull + health check
POST /commit        → git add + commit + push (body: {"message": "...", "files": [...]})
GET  /status        → git log + branch info
GET  /file?path=... → read file contents
PUT  /file?path=... → write file contents (body = file content)
GET  /ls?path=...   → list directory
"""

import http.server
import json
import subprocess
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import shutil

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



def _check_infrastructure_health() -> dict:
    """Gather host-level health: auto-sync, github, docker, disk."""
    import time as _time
    from datetime import datetime as _dt, timezone as _tz
    result = {}

    # 1. Auto-Sync process check
    try:
        r = subprocess.run(
            ["docker", "run", "--rm", "--pid=host", "alpine",
             "sh", "-c", "ps aux | grep auto-sync.sh | grep -v grep"],
            capture_output=True, text=True, timeout=10)
        lines_out = [l for l in r.stdout.strip().split(chr(10)) if l.strip()]
        is_running = len(lines_out) > 0
        pid = 0
        if is_running:
            parts = lines_out[0].split()
            pid = int(parts[0]) if parts else 0
        result["auto_sync"] = {
            "status": "ok" if is_running else "down",
            "state": "active" if is_running else "inactive",
            "pid": pid,
        }
    except Exception as e:
        result["auto_sync"] = {"status": "down", "error": str(e)}

    # 2. GitHub connectivity
    try:
        start = _time.time()
        r = subprocess.run(
            ["git", "-C", REPO_DIR, "ls-remote", "-q", "--exit-code", "origin", "HEAD"],
            capture_output=True, text=True, timeout=10)
        ms = round((_time.time() - start) * 1000)
        log = subprocess.run(
            ["git", "-C", REPO_DIR, "log", "-1", "--format=%H|%s|%ci"],
            capture_output=True, text=True, timeout=5)
        parts = log.stdout.strip().split("|", 2) if log.stdout.strip() else []
        result["github"] = {
            "status": "ok" if r.returncode == 0 else "down",
            "response_ms": ms,
            "last_commit": parts[0][:8] if parts else "N/A",
            "last_message": parts[1] if len(parts) > 1 else "N/A",
            "last_commit_time": parts[2] if len(parts) > 2 else "N/A",
        }
    except Exception as e:
        result["github"] = {"status": "down", "error": str(e)}

    # 3. Docker containers
    try:
        start = _time.time()
        r = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.State}}"],
            capture_output=True, text=True, timeout=10)
        ms = round((_time.time() - start) * 1000)
        containers = []
        all_running = True
        for line in r.stdout.strip().split(chr(10)):
            if not line:
                continue
            p = line.split("|", 2)
            c = {"name": p[0], "status": p[1] if len(p) > 1 else "?",
                 "state": p[2] if len(p) > 2 else "?"}
            containers.append(c)
            if c["state"] != "running":
                all_running = False
        result["docker"] = {
            "status": "ok" if all_running else "degraded",
            "containers": containers, "total": len(containers),
            "all_healthy": all_running, "response_ms": ms,
        }
    except Exception as e:
        result["docker"] = {"status": "down", "error": str(e)}

    # 4. Disk space
    try:
        usage = shutil.disk_usage(REPO_DIR)
        pct = round(usage.used / usage.total * 100, 1)
        result["disk"] = {
            "status": "ok" if pct < 85 else "degraded" if pct < 95 else "down",
            "total_gb": round(usage.total / (1024**3), 1),
            "used_gb": round(usage.used / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "used_pct": pct,
        }
    except Exception as e:
        result["disk"] = {"status": "down", "error": str(e)}

    result["timestamp"] = _dt.now(_tz.utc).isoformat()
    return result


class DeployHandler(http.server.BaseHTTPRequestHandler):
    def _verify_token(self) -> bool:
        """Verify token from Authorization header OR ?token= query param.

        Returns True if valid, False otherwise.
        """
        if not DEPLOY_TOKEN:
            print("[deployer] WARNING: DEPLOY_TOKEN not set!")
            return False

        # Check Authorization header first
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token == DEPLOY_TOKEN:
                return True

        # Fallback: check ?token= query parameter (avoids CORS preflight)
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        token_param = params.get("token", [None])[0]
        if token_param and token_param == DEPLOY_TOKEN:
            return True

        return False

    def do_POST(self):
        path = self.path.rstrip("/")

        # All POST endpoints require authentication
        if not self._verify_token():
            self._json_response(401, {"error": "Unauthorized: missing or invalid token"})
            return

        if path in ("/deploy/exec", "/exec"):
            # Execute a shell command (for remote debugging)
            body = self._read_body()
            data = json.loads(body) if body else {}
            cmd = data.get("cmd", "")
            if not cmd:
                self._json_response(400, {"error": "Missing 'cmd' in body"})
                return
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=60, cwd=REPO_DIR
                )
                self._json_response(200, {
                    "ok": result.returncode == 0,
                    "stdout": result.stdout[-8000:],
                    "stderr": result.stderr[-4000:],
                    "code": result.returncode,
                })
            except Exception as e:
                self._json_response(500, {"error": str(e)})
            return

        elif path in ("/deploy/restart-self", "/restart-self"):
            # Restart the deployer process (picks up new code)
            self._json_response(200, {"ok": True, "message": "Restarting deployer..."})
            import threading
            def _restart():
                time.sleep(1)
                print("[deployer] Self-restarting...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            threading.Thread(target=_restart, daemon=True).start()
            return

        elif path in ("", "/deploy", "/pull"):
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

        elif path == "/commit":
            # Git add + commit + push
            body = self._read_body()
            data = json.loads(body) if body else {}
            message = data.get("message", "update")
            files = data.get("files", ["."])

            results = {}
            for f in files:
                results[f"add_{f}"] = _run(["git", "add", f])
            results["commit"] = _run(["git", "commit", "-m", message])
            if results["commit"]["ok"]:
                results["push"] = _run(["git", "push", "origin", "main"])
            self._json_response(200, results)

        else:
            self._json_response(404, {"error": f"Unknown path: {path}"})

    def do_PUT(self):
        """Write files — requires auth."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = urllib.parse.parse_qs(parsed.query)

        if not self._verify_token():
            self._json_response(401, {"error": "Unauthorized"})
            return

        if path == "/file":
            file_path = params.get("path", [None])[0]
            if not file_path:
                self._json_response(400, {"error": "Missing ?path= parameter"})
                return
            full_path = os.path.join(REPO_DIR, file_path)
            # Security: prevent path traversal
            if not os.path.realpath(full_path).startswith(os.path.realpath(REPO_DIR)):
                self._json_response(403, {"error": "Path traversal blocked"})
                return
            try:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                content = self._read_body()
                with open(full_path, "w") as f:
                    f.write(content)
                self._json_response(200, {"ok": True, "path": file_path, "size": len(content)})
            except Exception as e:
                self._json_response(500, {"error": str(e)})
        else:
            self._json_response(404, {"error": f"Unknown path: {path}"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = urllib.parse.parse_qs(parsed.query)

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

        elif path == "/file":
            # Read file — requires auth
            if not self._verify_token():
                self._json_response(401, {"error": "Unauthorized"})
                return
            file_path = params.get("path", [None])[0]
            if not file_path:
                self._json_response(400, {"error": "Missing ?path= parameter"})
                return
            full_path = os.path.join(REPO_DIR, file_path)
            if not os.path.realpath(full_path).startswith(os.path.realpath(REPO_DIR)):
                self._json_response(403, {"error": "Path traversal blocked"})
                return
            try:
                with open(full_path, "r") as f:
                    content = f.read()
                self._json_response(200, {"ok": True, "path": file_path, "content": content})
            except FileNotFoundError:
                self._json_response(404, {"error": f"File not found: {file_path}"})
            except Exception as e:
                self._json_response(500, {"error": str(e)})

        elif path == "/ls":
            # List directory — requires auth
            if not self._verify_token():
                self._json_response(401, {"error": "Unauthorized"})
                return
            dir_path = params.get("path", [""])[0]
            full_path = os.path.join(REPO_DIR, dir_path)
            if not os.path.realpath(full_path).startswith(os.path.realpath(REPO_DIR)):
                self._json_response(403, {"error": "Path traversal blocked"})
                return
            try:
                entries = []
                for name in sorted(os.listdir(full_path)):
                    fp = os.path.join(full_path, name)
                    entries.append({
                        "name": name,
                        "type": "dir" if os.path.isdir(fp) else "file",
                        "size": os.path.getsize(fp) if os.path.isfile(fp) else None,
                    })
                self._json_response(200, {"ok": True, "path": dir_path, "entries": entries})
            except Exception as e:
                self._json_response(500, {"error": str(e)})


        elif path in ("/infrastructure-health", "/deploy/infrastructure-health"):
            if not self._verify_token():
                self._json_response(401, {"error": "Unauthorized"})
                return
            health = _check_infrastructure_health()
            self._json_response(200, health)

        else:
            self._json_response(404, {"error": f"Unknown path: {path}"})

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8") if length else ""

    def _json_response(self, code: int, data: dict):
        body = json.dumps(data, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[deployer] {args[0]}")


def _setup_git():
    """Install git if missing (Debian/Ubuntu) and configure credentials."""
    # Ensure git is available
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[deployer] git not found, installing...")
        subprocess.run(["apt-get", "update", "-qq"], capture_output=True)
        subprocess.run(["apt-get", "install", "-y", "-qq", "git", "curl"],
                       capture_output=True)
        print("[deployer] git installed")

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


if __name__ == "__main__":
    _setup_git()

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
