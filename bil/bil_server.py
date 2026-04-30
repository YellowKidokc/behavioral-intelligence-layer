"""BIL HTTP server — receives behavioral signals and re-ranks search results."""
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from bil.bil_api import BIL
from bil.bil_features import extract_web_features, extract_search_result_features


class BILHandler(BaseHTTPRequestHandler):
    bil = BIL()
    started_at = time.time()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        if self.path == "/bil/web":
            self._handle_web(body)
        elif self.path == "/bil/rank":
            self._handle_rank(body)
        elif self.path == "/bil/classify":
            self._handle_classify(body)
        elif self.path == "/bil/rename":
            self._handle_rename(body)
        elif self.path == "/bil/sort":
            self._handle_sort(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/bil/export":
            self._handle_export()
        elif self.path == "/bil/status":
            self._handle_status()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_web(self, body: bytes):
        """Receive a browser behavioral event and learn from it."""
        data = json.loads(body)
        features, signal = extract_web_features(
            url=data.get("url", ""),
            text=data.get("text", ""),
            time_on_page=data.get("time_on_page", 0),
            scroll_depth=data.get("scroll_depth", 0.0),
            bookmarked=data.get("bookmarked", False),
            copy_count=data.get("copy_count", 0),
            word_count=data.get("word_count"),
        )
        self.bil.learn("web", features, signal)
        self._json_response({"status": "ok", "signal": round(signal, 4)})

    def _handle_export(self):
        """Return today's digest as JSON (also writes it to disk)."""
        from datetime import datetime
        path = self.bil.export_daily()
        digest = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "models": {name: model.get_summary()
                       for name, model in self.bil.models.items()},
            "export_path": path,
        }
        self._json_response(digest)

    def _handle_status(self):
        """Lightweight liveness + per-model event counts."""
        self._json_response({
            "status": "ok",
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "models": {name: model.get_summary()
                       for name, model in self.bil.models.items()},
        })

    def _handle_classify(self, body: bytes):
        """Classify a single file via Ollama (moondream/mistral)."""
        from bil.file_intel import classify_file
        try:
            data = json.loads(body) if body else {}
            target = Path(data.get("path", "")).expanduser()
            if not target.exists() or not target.is_file():
                self._json_response({"error": f"file not found: {target}"}, status=404)
                return
            self._json_response(classify_file(target))
        except Exception as exc:
            self._json_response({"error": str(exc)}, status=500)

    def _handle_rename(self, body: bytes):
        """Generate (and optionally execute) a rename plan for a folder."""
        from bil.file_intel import build_rename_plan
        try:
            data = json.loads(body) if body else {}
            folder = Path(data.get("path", "")).expanduser()
            dry_run = bool(data.get("dry_run", True))
            max_files = int(data.get("max_files", 200))
            self._json_response(
                build_rename_plan(folder, dry_run=dry_run, max_files=max_files),
            )
        except Exception as exc:
            self._json_response({"error": str(exc)}, status=500)

    def _handle_sort(self, body: bytes):
        """Group files into category subfolders under output_path."""
        from bil.file_intel import build_sort_plan
        try:
            data = json.loads(body) if body else {}
            input_path = Path(data.get("input_path", "")).expanduser()
            output_path = Path(data.get("output_path", "")).expanduser()
            mode = data.get("mode", "content")
            dry_run = bool(data.get("dry_run", True))
            max_files = int(data.get("max_files", 200))
            self._json_response(
                build_sort_plan(input_path, output_path, mode=mode,
                                dry_run=dry_run, max_files=max_files),
            )
        except Exception as exc:
            self._json_response({"error": str(exc)}, status=500)

    def _handle_rank(self, body: bytes):
        """Re-rank SearXNG results using BIL web model.

        Input:  { "results": [ { url, title, content, engine, score } ] }
        Output: { "results": [ same items sorted by final_score desc ] }
        """
        data = json.loads(body)
        results = data.get("results", [])
        scored = []
        for i, r in enumerate(results):
            features = extract_search_result_features(
                url=r.get("url", ""),
                title=r.get("title", ""),
                snippet=r.get("content", ""),
                engine=r.get("engine", ""),
                score=r.get("score", 0.0),
                position=i,
            )
            bil_score = self.bil.predict("web", features)
            scored.append({**r, "bil_score": round(bil_score, 4)})

        max_score = max((r.get("score", 1) for r in results), default=1) or 1
        for r in scored:
            norm = r.get("score", 0) / max_score
            r["final_score"] = round(0.6 * norm + 0.4 * r["bil_score"], 4)

        scored.sort(key=lambda r: r["final_score"], reverse=True)
        self._json_response({"results": scored})

    def _json_response(self, data: dict, status: int = 200):
        response = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def start_bil_server(port: int = 8420):
    server = HTTPServer(("0.0.0.0", port), BILHandler)
    print(f"BIL server on http://0.0.0.0:{port}")
    print("  POST /bil/web      — learn from browser behavior")
    print("  POST /bil/rank     — re-rank SearXNG results")
    print("  POST /bil/classify — classify a single file (moondream/mistral)")
    print("  POST /bil/rename   — propose (or execute) a folder rename plan")
    print("  POST /bil/sort     — group files into category subfolders")
    print("  GET  /bil/export   — daily digest JSON")
    print("  GET  /bil/status   — uptime + per-model event counts")
    server.serve_forever()


if __name__ == "__main__":
    start_bil_server()
