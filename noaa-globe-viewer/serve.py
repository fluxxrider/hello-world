#!/usr/bin/env python3
"""Static server + caching proxy for the GOES-19 globe viewer.

Serves this directory at http://localhost:8000/ and forwards requests under
/noaa/ to the NOAA STAR CDN, caching responses on disk under .cache/ so
scrubbing the timeline doesn't re-download frames. Timestamped frame files
never change and are cached forever; the directory listing is cached briefly.

Usage:  python3 serve.py [port]
"""

import hashlib
import http.server
import pathlib
import socketserver
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
CDN = "https://cdn.star.nesdis.noaa.gov/GOES19/ABI/FD/GEOCOLOR/"
LISTING_TTL = 60  # seconds


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/noaa" or self.path.startswith("/noaa/"):
            self.proxy(self.path[len("/noaa"):].lstrip("/"))
        else:
            super().do_GET()

    def proxy(self, rel):
        if ".." in rel:
            self.send_error(400)
            return
        is_listing = rel == "" or rel.endswith("/")
        CACHE.mkdir(exist_ok=True)
        cache_file = CACHE / (hashlib.sha256(rel.encode()).hexdigest()[:24]
                              + ("_listing.html" if is_listing else "_" + rel.replace("/", "_")))

        body = None
        if cache_file.exists():
            fresh = (not is_listing) or (time.time() - cache_file.stat().st_mtime < LISTING_TTL)
            if fresh:
                body = cache_file.read_bytes()

        if body is None:
            req = urllib.request.Request(CDN + rel, headers={"User-Agent": "goes-globe-viewer/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read()
                cache_file.write_bytes(body)
            except urllib.error.HTTPError as e:
                self.send_error(e.code, f"CDN returned {e.code} for {rel!r}")
                return
            except OSError as e:
                self.send_error(502, f"Cannot reach NOAA CDN: {e}")
                return

        ctype = "text/html; charset=utf-8" if is_listing else "image/jpeg"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if is_listing else "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"GOES-19 globe viewer:  http://localhost:{port}/   (Ctrl-C to stop)")
    print(f"Proxying /noaa/* -> {CDN}  (cache: {CACHE})")
    with Server(("", port), Handler) as srv:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
