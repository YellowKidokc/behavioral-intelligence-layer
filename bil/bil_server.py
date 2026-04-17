"""BIL HTTP server — receives behavioral signals and re-ranks search results."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from bil.bil_api import BIL
from bil.bil_features import extract_web_features, extract_search_result_features


class BILHandler(BaseHTTPRequestHandler):
    bil = BIL()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        if self.path == "/bil/web":
            self._handle_web(body)
        elif self.path == "/bil/rank":
            self._handle_rank(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_web(self, body: bytes):
        """Receive a browser behavioral event and learn from it."""
        data = json.loads(body)
        features, signal = extract_web_features(
            url=data.get("url", ""),
            text="",
            time_on_page=data.get("time_on_page", 0),
            scrolled_bottom=data.get("scrolledBottom", False),
            bookmarked=data.get("bookmarked", False),
            copied=data.get("copied", False),
        )
        self.bil.learn("web", features, signal)
        self._json_response({"status": "ok"})

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
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def start_bil_server(port: int = 8420):
    server = HTTPServer(("0.0.0.0", port), BILHandler)
    print(f"BIL server on http://0.0.0.0:{port}")
    print("  POST /bil/web   — learn from browser behavior")
    print("  POST /bil/rank  — re-rank SearXNG results")
    server.serve_forever()


if __name__ == "__main__":
    start_bil_server()
