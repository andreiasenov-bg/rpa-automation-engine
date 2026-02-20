import re

with open('/repo/scripts/deployer.py', 'r') as f:
    content = f.read()

old = '    def do_POST(self):\n        path = self.path.rstrip("/")\n\n        # All POST endpoints require authentication\n        if not self._verify_token():\n            self._json_response(401, {"error": "Unauthorized: missing or invalid token"})\n            return\n\n        if path.startswith("/api/") or path.startswith("/api"):\n            self._proxy_to_backend()\n            return'

new = '    def do_POST(self):\n        path = self.path.rstrip("/")\n\n        # Proxy /api/ to backend WITHOUT deploy token (frontend uses its own auth)\n        if path.startswith("/api/") or path.startswith("/api"):\n            self._proxy_to_backend()\n            return\n\n        # All other POST endpoints require deploy token\n        if not self._verify_token():\n            self._json_response(401, {"error": "Unauthorized: missing or invalid token"})\n            return'

if old in content:
    content = content.replace(old, new)
    with open('/repo/scripts/deployer.py', 'w') as f:
        f.write(content)
    print('FIXED')
else:
    print('NOT FOUND')
    idx = content.find('def do_POST')
    print(repr(content[idx:idx+350]))
