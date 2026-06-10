import http.server
import socketserver
import os

PORT = int(os.environ.get("PORT", 8080))

class DummyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "MUGEN AI Bot is running"}')

print(f"Starting dummy web server on port {PORT} for Render health checks...")
with socketserver.TCPServer(("", PORT), DummyHandler) as httpd:
    httpd.serve_forever()
