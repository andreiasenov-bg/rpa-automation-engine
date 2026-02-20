with open('/repo/scripts/deployer.py') as f: c=f.read()
ch=0
# Already fixed in previous session, check
if 'Proxy /api/ to backend WITHOUT deploy token' not in c:
 old='    def do_POST(self):\n        path = self.path.rstrip("/")\n\n        # All POST endpoints require authentication\n        if not self._verify_token():\n            self._json_response(401, {"error": "Unauthorized: missing or invalid token"})\n            return\n\n        if path.startswith("/api/") or path.startswith("/api"):\n            self._proxy_to_backend()\n            return'
 new='    def do_POST(self):\n        path = self.path.rstrip("/")\n\n        # Proxy /api/ to backend WITHOUT deploy token (frontend auth is separate)\n        if path.startswith("/api/") or path.startswith("/api"):\n            self._proxy_to_backend()\n            return\n\n        # All other POST endpoints require deploy token authentication\n        if not self._verify_token():\n            self._json_response(401, {"error": "Unauthorized: missing or invalid token"})\n            return'
 if old in c:
  c=c.replace(old,new);ch+=1;print('Fixed do_POST')
 else: print('WARN: do_POST pattern not found')
else: print('do_POST already fixed')

# Add do_DELETE + do_PATCH
if 'def do_DELETE' not in c:
 anchor='    def do_OPTIONS(self):'
 i=c.find(anchor)
 if i>0:
  extra="""
    def do_DELETE(self):
        path = self.path.rstrip("/")
        if path.startswith("/api/") or path.startswith("/api"):
            self._proxy_to_backend()
            return
        self._json_response(405, {"error": "Method not allowed"})

    def do_PATCH(self):
        path = self.path.rstrip("/")
        if path.startswith("/api/") or path.startswith("/api"):
            self._proxy_to_backend()
            return
        self._json_response(405, {"error": "Method not allowed"})

"""
  c=c[:i]+extra+c[i:];ch+=1;print('Added DELETE/PATCH')
else: print('DELETE/PATCH already present')

if ch: open('/repo/scripts/deployer.py','w').write(c)
print('Done, changes:',ch)
