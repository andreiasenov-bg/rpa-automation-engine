with open('/repo/scripts/deployer.py') as f: c=f.read()
old='    def _serve_frontend(self):'
if old in c:
 i=c.find(old)
 # Find the method after _send_static_file (or _proxy or _setup_git)
 # We need to replace both _serve_frontend AND _send_static_file
 nd=i+10
 # Skip past _send_static_file method too
 nd=c.find('\n    def _send_static_file',i+10)
 if nd>0:
  nd=c.find('\n    def ',nd+10)
 else:
  nd=c.find('\n    def ',i+10)
 if nd==-1: nd=c.find('\nif __name__',i+10)
 new="""    def _serve_frontend(self):
        parsed = __import__('urllib.parse',fromlist=['urlparse']).urlparse(self.path)
        url_path = parsed.path.lstrip("/")
        if not url_path or url_path.endswith("/"): url_path = "index.html"
        file_path = os.path.realpath(os.path.join(FRONTEND_DIR, url_path))
        if not file_path.startswith(os.path.realpath(FRONTEND_DIR)):
            self._json_response(403, {"error": "Forbidden"}); return
        if not os.path.isfile(file_path):
            file_path = os.path.join(FRONTEND_DIR, "index.html")
        if not os.path.isfile(file_path):
            self._json_response(404, {"error": "Not found"}); return
        self._send_static_file(file_path)

    def _send_static_file(self, file_path):
        MT = {".html":"text/html;charset=utf-8",".js":"application/javascript;charset=utf-8",
              ".css":"text/css;charset=utf-8",".json":"application/json;charset=utf-8",
              ".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".gif":"image/gif",
              ".svg":"image/svg+xml",".ico":"image/x-icon",".woff":"font/woff",
              ".woff2":"font/woff2",".ttf":"font/ttf",".map":"application/json",
              ".webp":"image/webp",".txt":"text/plain;charset=utf-8"}
        try:
            ext = os.path.splitext(file_path)[1].lower()
            ct = MT.get(ext, "application/octet-stream")
            with open(file_path, "rb") as f: content = f.read()
            import hashlib as hl
            etag = hl.md5(content).hexdigest()
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304); self.end_headers(); return
            use_gz = False
            ae = self.headers.get("Accept-Encoding", "")
            comp = ext in (".html",".js",".css",".json",".svg",".txt",".map")
            if "gzip" in ae and comp and len(content) > 1024:
                import gzip as gz
                compressed = gz.compress(content, compresslevel=6)
                if len(compressed) < len(content): content = compressed; use_gz = True
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("ETag", etag)
            if "/assets/" in file_path and ext != ".html":
                self.send_header("Cache-Control", f"public, max-age={STATIC_CACHE_MAX_AGE}, immutable")
            elif ext == ".html":
                self.send_header("Cache-Control", "no-cache, must-revalidate")
            else:
                self.send_header("Cache-Control", "public, max-age=3600")
            if use_gz: self.send_header("Content-Encoding", "gzip")
            for k, v in SECURITY_HEADERS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._json_response(500, {"error": f"Static file error: {str(e)}"})

"""
 if nd>i:
  c=c[:i]+new+c[nd:]
  open('/repo/scripts/deployer.py','w').write(c)
  print('OK: frontend serving replaced')
 else: print('ERR: nd not found')
else: print('SKIP')
