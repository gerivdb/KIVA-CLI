#!/usr/bin/env python3
"""
Web UI Dashboard Server - KIVA CLI

Provides a web-based dashboard for monitoring KIVA-CLI operations.
"""

import json
import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Optional, Any


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_html(self.get_index_page())
        elif self.path == "/api/status":
            self.send_json({"status": "ok", "timestamp": time.time()})
        else:
            self.send_error(404)

    def get_index_page(self) -> str:
        return """<!DOCTYPE html><html><head><title>KIVA Dashboard</title>
<style>body{font-family:Arial;margin:20px;background:#1a1a2e;color:#eee}
h1{color:#00ff88}.card{background:#16213e;padding:20px;margin:10px;border-radius:8px}</style>
</head><body><h1>KIVA-CLI Dashboard v0.20.0</h1>
<div class="card"><h2>Status</h2><div id="status">OK</div></div>
<script>setInterval(()=>fetch('/api/status').then(r=>r.json()).then(d=>document.getElementById('status').innerText=JSON.stringify(d)),5000)</script>
</body></html>"""

    def send_html(self, content: str):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(content.encode())

    def send_json(self, data: Any):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass


class DashboardServer:
    def __init__(self, host: str = "localhost", port: int = 9000):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.server = HTTPServer((self.host, self.port), DashboardHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"Dashboard started at http://{self.host}:{self.port}")

    def stop(self):
        if self.server:
            self.server.shutdown()