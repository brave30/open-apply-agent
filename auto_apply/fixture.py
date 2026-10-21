"""Loopback-only simulated application. No real employers, no external resources."""
from contextlib import contextmanager
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import secrets
import hashlib
from .safety import payload_digest
from .catalog import render_application

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def serve(port=0, application_id=None):
    application_html = render_application(application_id) if application_id else (ROOT / "fixtures/application.html").read_text(encoding="utf-8")
    token = secrets.token_urlsafe(32)
    records = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, content_type="text/html; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; form-action 'self'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(body.encode())

        def do_GET(self):
            if self.path == "/apply":
                self.send(200, application_html)
            elif self.path == "/smoke":
                self.send(200, '<!doctype html><h1>Browser inference test</h1><label for="test">Test word</label><input id="test" style="font-size:28px;width:500px" autofocus><p>Type ORCHID into the Test word input.</p>')
            else:
                self.send(404, "Not found")

        def do_POST(self):
            if self.path != "/submit" or not secrets.compare_digest(self.headers.get("x-human-approval", ""), token):
                self.send(403, "Explicit human approval required")
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length > 2_000_000:
                self.send(413, "Too large")
                return
            body = self.rfile.read(length)
            message = BytesParser(policy=default).parsebytes(
                ("Content-Type: " + self.headers.get("Content-Type", "") + "\r\nMIME-Version: 1.0\r\n\r\n").encode() + body)
            record = {}
            parts = []
            for part in message.iter_parts():
                name = part.get_param("name", header="content-disposition")
                data = part.get_payload(decode=True)
                if part.get_filename() is not None:
                    record[name] = {"filename": part.get_filename(), "bytes": len(data)}
                    parts.append({"name": name, "filename": part.get_filename(), "sha256": hashlib.sha256(data).hexdigest()})
                else:
                    record[name] = data.decode()
                    parts.append({"name": name, "value": data.decode().replace("\r\n", "\n").replace("\r", "\n")})
            if not secrets.compare_digest(self.headers.get("x-approved-payload-sha256", ""), payload_digest(parts)):
                self.send(409, "Application differs from the reviewed contents. New approval required.")
                return
            records.append(record)
            self.send(200, '<h1 id="receipt">Synthetic application received</h1>')

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", token, records
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
