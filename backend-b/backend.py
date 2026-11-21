import json, os, hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer

NAME = os.environ.get("BACKEND", "A")
PORT = int(os.environ.get("PORT", "3001"))

class Handler(BaseHTTPRequestHandler):
    def send_it(self, code, body, ctype="application/json", extra=None):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Backend", NAME)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.path == "/":
            self.send_it(200, f"<h1>Backend {NAME} is running</h1>", "text/html")
        elif self.path == "/api/status":
            self.send_it(200, json.dumps({"backend": NAME, "status": "ok"}),
                         extra={"Cache-Control": "no-store"})
        elif self.path == "/api/info":
            # Caching demo (Step 6): same content on every backend, so same ETag
            body = json.dumps({"info": "this content rarely changes"})
            etag = '"' + hashlib.md5(body.encode()).hexdigest() + '"'
            if self.headers.get("If-None-Match") == etag:
                self.send_it(304, "", extra={"ETag": etag, "Cache-Control": "max-age=60"})
            else:
                self.send_it(200, body, extra={"ETag": etag, "Cache-Control": "max-age=60"})
        else:
            self.send_it(404, json.dumps({"error": "not found"}))

HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
