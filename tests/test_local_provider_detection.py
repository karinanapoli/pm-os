import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pm_os.web.local_provider_detection import clear_cache, detect_ollama_models


def test_only_loopback_urls_are_probed():
    clear_cache()
    assert detect_ollama_models("http://example.com:11434") == []
    assert detect_ollama_models("file:///etc/passwd") == []
    assert detect_ollama_models("") == []


def test_unreachable_local_ollama_is_reported_as_unavailable():
    clear_cache()
    assert detect_ollama_models("http://127.0.0.1:9", timeout=0.2) == []


def test_lists_models_from_a_local_ollama():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"models": [{"name": "llama3.2:1b"}, {"name": "qwen2.5:7b"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        clear_cache()
        models = detect_ollama_models(f"http://127.0.0.1:{server.server_port}")
    finally:
        server.shutdown()

    assert models == ["llama3.2:1b", "qwen2.5:7b"]
