#!/usr/bin/env python3
"""Patch deployer.py to add frontend serving + API proxying."""
import re

with open('/repo/scripts/deployer.py', 'r') as f:
    code = f.read()

# Add imports at the top after existing imports
import_addition = '''
import mimetypes
import io
FRONTEND_DIR = os.path.join(REPO_DIR, "frontend", "dist")
'''

# Add after the DEPLOY_TOKEN line
code = code.replace(
    'DEPLOY_TOKEN = os.environ.get("DEPLOY_TOKEN", "")',
    'DEPLOY_TOKEN = os.environ.get("DEPLOY_TOKEN", "")' + import_addition
)

# Add frontend serving method before the server startup code
frontend_methods = '''
    def _serve_frontend(self):
        """Serve frontend static files with SPA fallback."""
        parsed = urllib.parse.urlparse(self.path)
        url_path = parsed.path.rstrip("/") or "/index.html"
        if url_path == "/":
            url_path = "/index.html"
        
        file_path = os.path.join(FRONTEND_DIR, url_path.lstrip("/"))
        
        # Security: prevent directory traversal
        file_path = os.path.realpath(file_path)
        if not file_path.startswith(os.path.realpath(FRONTEND_DIR)):
            self._json_response(403, {"error": "Forbidden"})
            return
        
        if os.path.isfile(file_path):
            self._send_static_file(file_path)
        else:
            # SPA fallback: serve index.html for client-side routing
            index_path = os.path.join(FRONTEND_DIR, "index.html")
            if os.path.isfile(index_path):
                self._send_static_file(index_path)
            else:
                self._json_response(404, {"error": "Frontend not built"})
    
    def _send_static_file(self, file_path):
        """Send a static file with proper content type."""
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream"
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=3600" if not file_path.endswith(".html") else "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self._json_response(500, {"error": str(e)})
    
    def _proxy_to_backend(self):
        """Proxy request to the backend."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            url = BACKEND_URL + self.path
            req = urllib.request.Request(url, data=body, method=self.command)
            
            # Forward headers
            for key, value in self.headers.items():
                if key.lower() not in ("host", "connection"):
                    req.add_header(key, value)
            
            resp = urllib.request.urlopen(req, timeout=30)
            resp_body = resp.read()
            
            self.send_response(resp.status)
            for key, value in resp.getheaders():
                if key.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            resp_body = e.read()
            self.send_response(e.code)
            for key, value in e.headers.items():
                if key.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as e:
            self._json_response(502, {"error": str(e)})
'''

# Insert before the server startup (look for the if __name__ pattern or HTTPServer)
code = code.replace(
    'if __name__',
    frontend_methods + '\nif __name__'
)

# Now add routing for /api/ and frontend fallback in do_GET
# Find the end of do_GET where it returns 404
# Add before any 404 response at the end of do_GET
old_404_get = '        self._json_response(404, {"error": "Unknown endpoint", "path": path})'
new_404_get = """        # Proxy /api/ to backend
        if path.startswith("/api/") or path.startswith("/api"):
            self._proxy_to_backend()
            return
        # Serve frontend for all other paths
        if os.path.isdir(FRONTEND_DIR):
            self._serve_frontend()
            return
        self._json_response(404, {"error": "Unknown endpoint", "path": path})"""
code = code.replace(old_404_get, new_404_get, 1)

# Also handle POST/PUT for /api/ routes
# Find do_POST and add API proxy at the start
old_post_check = '        if path in ("/deploy/exec", "/exec"):'
new_post_check = """        if path.startswith("/api/") or path.startswith("/api"):
            self._proxy_to_backend()
            return
        if path in ("/deploy/exec", "/exec"):"""
code = code.replace(old_post_check, new_post_check, 1)

with open('/repo/scripts/deployer.py', 'w') as f:
    f.write(code)

print("Deployer patched successfully!")
print(f"Total lines: {len(code.splitlines())}")
