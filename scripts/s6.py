with open('/repo/scripts/deployer.py') as f: c=f.read()
ch=0

# 6a: Add WebSocket proxy method before "if __name__"
if '_proxy_websocket' not in c:
 mi=c.find('\nif __name__')
 if mi>0:
  ws="""
    def _proxy_websocket(self):
        try:
            import socket as _s, select as _sel
            bs = _s.socket(_s.AF_INET, _s.SOCK_STREAM)
            bs.settimeout(5)
            bs.connect((BACKEND_HOST, BACKEND_PORT))
            req = f"{self.command} {self.path} HTTP/1.1\\r\\n"
            bs.sendall(req.encode())
            for key in self.headers:
                if key.lower() != "host":
                    bs.sendall(f"{key}: {self.headers[key]}\\r\\n".encode())
            bs.sendall(f"Host: {BACKEND_HOST}:{BACKEND_PORT}\\r\\n\\r\\n".encode())
            bs.settimeout(10)
            rd = b""
            while b"\\r\\n\\r\\n" not in rd:
                ch2 = bs.recv(4096)
                if not ch2: break
                rd += ch2
            he = rd.find(b"\\r\\n\\r\\n")
            if he > 0:
                self.wfile.write(rd[:he+4])
                self.wfile.flush()
                rest = rd[he+4:]
                if rest: self.wfile.write(rest); self.wfile.flush()
            cs = self.request
            bs.setblocking(False); cs.setblocking(False)
            socks = [cs, bs]
            while socks:
                r, _, e = _sel.select(socks, [], socks, 30)
                if e: break
                if not r: continue
                for s2 in r:
                    try:
                        d = s2.recv(65536)
                        if not d: raise ConnectionError()
                        (bs if s2 is cs else cs).sendall(d)
                    except: socks = []; break
            bs.close()
        except Exception as e:
            try: self._json_response(502, {"error": f"WebSocket error: {str(e)}"})
            except: pass

"""
  # Find last method in class (before if __name__)
  last_def = c.rfind('\n    def ', 0, mi)
  next_after = c.find('\n\n', last_def+10)
  if next_after == -1 or next_after > mi: next_after = mi
  # Actually just insert before if __name__
  c = c[:mi] + ws + c[mi:]
  ch += 1; print('Added WebSocket proxy')

# 6b: Add WebSocket detection in do_GET
if 'websocket' not in c.lower() or 'Upgrade' not in c:
 dg=c.find('    def do_GET(self):')
 if dg>0:
  nl=c.index('\n',dg)+1
  # Find first real code line
  while c[nl]=='\n': nl+=1
  ws_det="""        # WebSocket upgrade
        if self.headers.get("Upgrade","").lower() == "websocket" or self.path.startswith("/ws"):
            self._proxy_websocket()
            return

        # /api/ GET without deploy token
        if self.path.startswith("/api/") or self.path.rstrip("/").startswith("/api"):
            self._proxy_to_backend()
            return

"""
  c=c[:nl]+ws_det+c[nl:]
  ch+=1;print('Added WS detect + /api/ GET fix in do_GET')

# 6c: Improve do_OPTIONS
old_opt='    def do_OPTIONS(self):'
if old_opt in c:
 oi=c.find(old_opt)
 nd=c.find('\n    def ',oi+10)
 if nd==-1: nd=c.find('\nif __name__',oi+10)
 new_opt="""    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Deploy-Token, X-Requested-With")
        self.send_header("Access-Control-Max-Age", "86400")
        for k, v in SECURITY_HEADERS.items(): self.send_header(k, v)
        self.end_headers()

"""
 if nd>oi:
  c=c[:oi]+new_opt+c[nd:]
  ch+=1;print('Improved do_OPTIONS')

# 6d: Add error handler
if 'def handle_one_request' not in c:
 lm=c.find('    def log_message(')
 if lm>0:
  eh="""    def handle_one_request(self):
        try: super().handle_one_request()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError): pass
        except Exception:
            try: self._json_response(500, {"error": "Internal server error"})
            except: pass

"""
  c=c[:lm]+eh+c[lm:]
  ch+=1;print('Added error handler')

# 6e: Improve _json_response with security headers
old_jr='    def _json_response(self, code: int, data: dict):'
if old_jr in c and 'SECURITY_HEADERS' not in c[c.find(old_jr):c.find(old_jr)+300]:
 ji=c.find(old_jr)
 nd2=c.find('\n    def ',ji+10)
 new_jr="""    def _json_response(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in SECURITY_HEADERS.items(): self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

"""
 if nd2>ji:
  c=c[:ji]+new_jr+c[nd2:]
  ch+=1;print('Improved _json_response')

# 6f: Ensure ThreadingHTTPServer
if 'ThreadingHTTPServer' not in c and 'http.server.HTTPServer((' in c:
 c=c.replace('http.server.HTTPServer((','http.server.ThreadingHTTPServer((')
 ch+=1;print('ThreadingHTTPServer')

# 6g: Add graceful shutdown
if 'signal.signal' not in c:
 mi2=c.find('\nif __name__')
 if mi2>0:
  sig="""
import signal
def _graceful_shutdown(signum, frame):
    print(f"[deployer] Signal {signum}, shutting down..."); __import__('sys').exit(0)
signal.signal(signal.SIGTERM, _graceful_shutdown)
signal.signal(signal.SIGINT, _graceful_shutdown)

"""
  c=c[:mi2]+sig+c[mi2:]
  ch+=1;print('Added signal handlers')

if ch:
 open('/repo/scripts/deployer.py','w').write(c)
print(f'Done: {ch} changes')
