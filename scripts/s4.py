with open('/repo/scripts/deployer.py') as f: c=f.read()
old='    def _proxy_to_backend(self):'
if old in c:
 i=c.find(old)
 nd=c.find('\n    def ',i+10)
 if nd==-1: nd=c.find('\nif __name__',i+10)
 new="""    def _proxy_to_backend(self):
        try:
            import http.client
            path = self.path
            method = self.command
            cl = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(cl) if cl > 0 else None
            conn = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=30)
            headers = {}
            for key in self.headers:
                lo = key.lower()
                if lo not in ("host", "connection", "transfer-encoding"):
                    headers[key] = self.headers[key]
            headers["Host"] = f"{BACKEND_HOST}:{BACKEND_PORT}"
            headers["X-Forwarded-For"] = self.client_address[0]
            headers["X-Forwarded-Proto"] = "http"
            headers["X-Real-IP"] = self.client_address[0]
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            resp_body = resp.read()
            self.send_response(resp.status)
            for key, val in resp.getheaders():
                lo = key.lower()
                if lo not in ("transfer-encoding", "connection", "server"):
                    self.send_header(key, val)
            for k, v in SECURITY_HEADERS.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp_body)
            conn.close()
        except Exception as e:
            self._json_response(502, {"error": f"Backend proxy error: {str(e)}"})

"""
 if nd>i:
  c=c[:i]+new+c[nd:]
  open('/repo/scripts/deployer.py','w').write(c)
  print('OK: proxy replaced')
 else: print('ERR: next_def not found')
else: print('SKIP: already replaced')
