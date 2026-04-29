"""BIL HTTP server — receives behavioral signals, re-ranks search, clipboard intelligence."""
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from bil.bil_api import BIL
from bil.bil_features import extract_web_features, extract_clipboard_features

GITHUB_EVENTS_LOG = r"D:\BIL\data\github\github_events.jsonl"


class BILHandler(BaseHTTPRequestHandler):
    bil = BIL()
    clipboard_history = []  # In-memory ring buffer of recent clips for prediction

    def do_GET(self):
        parsed = urlparse(self.path)
        p = parsed.path

        if p == "/bil/clipboard/predict":
            self._handle_clipboard_predict(parsed)
        elif p == "/bil/status":
            self._json_response({
                "status": "ok",
                "models": {name: model.get_summary() for name, model in self.bil.models.items()},
                "clipboard_history_size": len(self.clipboard_history),
            })
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if self.path == "/bil/web":
            self._handle_web(body)
        elif self.path == "/bil/clipboard":
            self._handle_clipboard(body)
        elif self.path == "/bil/rank":
            self._handle_rank(body)
        elif self.path == "/bil/github":
            self._handle_github(body)
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

    def _handle_clipboard(self, body: bytes):
        """Receive clipboard event, learn from it, store in history."""
        data = json.loads(body)
        text = data.get("text", "")
        app = data.get("app", "unknown")
        used = data.get("used", False)  # True if this was pasted (positive signal)

        if not text.strip():
            self._json_response({"status": "skipped", "reason": "empty"})
            return

        features = extract_clipboard_features(text, app)
        signal = 1.0 if used else 0.3  # Copy = mild interest, paste = confirmed use

        self.bil.learn("clipboard", features, signal)

        # Store in history ring buffer (max 500)
        entry = {
            "text": text[:500],  # Truncate for memory
            "app": app,
            "ts": datetime.now().isoformat(),
            "keywords": features.get("text_keywords", []),
            "used": used,
            "bil_score": self.bil.predict("clipboard", features),
        }
        self.clipboard_history.append(entry)
        if len(self.clipboard_history) > 500:
            self.clipboard_history = self.clipboard_history[-500:]

        self._json_response({"status": "ok", "score": entry["bil_score"]})

    def _handle_clipboard_predict(self, parsed):
        """Return predicted clipboard items ranked by relevance to current context."""
        qs = parse_qs(parsed.query)
        limit = int(qs.get("limit", ["10"])[0])
        context_app = qs.get("app", [""])[0]

        if not self.clipboard_history:
            self._json_response({"predictions": [], "reason": "no history"})
            return

        # Score each history item against current context
        scored = []
        current_hour = datetime.now().hour
        for entry in self.clipboard_history[-200:]:  # Score recent 200
            context_features = {
                "text_keywords": entry.get("keywords", []),
                "app": context_app or entry.get("app", "unknown"),
                "hour": current_hour,
                "text_length": len(entry.get("text", "")),
            }
            score = self.bil.predict("clipboard", context_features)

            # Boost recently used items slightly
            if entry.get("used"):
                score = min(1.0, score + 0.1)

            scored.append({
                "text": entry["text"],
                "app": entry.get("app", ""),
                "ts": entry.get("ts", ""),
                "score": round(score, 4),
                "keywords": entry.get("keywords", []),
            })

        # Sort by score descending, return top N
        scored.sort(key=lambda x: x["score"], reverse=True)
        self._json_response({"predictions": scored[:limit]})

    def _handle_github(self, body: bytes):
        """Receive a GitHub repo event, score it, log it, and learn from it."""
        data = json.loads(body)
        repo = data.get("repo", "")
        stars = data.get("stars", 0)
        forks = data.get("forks", 0)
        language = data.get("language", "")
        topics = data.get("topics", [])
        time_on_page = int(data.get("time_on_page", 0) or 0)
        copied_code = bool(data.get("copied_code", False))
        bookmarked = bool(data.get("bookmarked", False))

        score = 0.3
        if copied_code:
            score += 0.2
        if bookmarked:
            score += 0.2
        if time_on_page > 60:
            score += 0.1
        if time_on_page > 180:
            score += 0.1
        score = min(score, 1.0)

        event = {
            "ts": datetime.now().isoformat(),
            "repo": repo,
            "stars": stars,
            "forks": forks,
            "language": language,
            "topics": topics,
            "time_on_page": time_on_page,
            "copied_code": copied_code,
            "bookmarked": bookmarked,
            "score": round(score, 4),
        }
        os.makedirs(os.path.dirname(GITHUB_EVENTS_LOG), exist_ok=True)
        with open(GITHUB_EVENTS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

        url = f"https://github.com/{repo}" if repo else "https://github.com/"
        text = " ".join([repo, language, " ".join(topics) if isinstance(topics, list) else str(topics)])
        features, _ = extract_web_features(
            url=url,
            text=text,
            time_on_page=time_on_page,
            scrolled_bottom=False,
            bookmarked=bookmarked,
            copied=copied_code,
        )
        self.bil.learn("web", features, score)

        self._json_response({"status": "ok", "repo": repo, "score": round(score, 4)})

    def _handle_rank(self, body: bytes):
        """Re-rank SearXNG results using BIL web model."""
        from bil.bil_features import extract_search_result_features
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
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(response))
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
    print(f"  POST /bil/web          - learn from browser behavior")
    print(f"  POST /bil/clipboard    - learn from clipboard events")
    print(f"  POST /bil/rank         - re-rank SearXNG results")
    print(f"  POST /bil/github       - learn from GitHub repo events")
    print(f"  GET  /bil/clipboard/predict - get clipboard predictions")
    print(f"  GET  /bil/status       - server status + model stats")
    server.serve_forever()


if __name__ == "__main__":
    start_bil_server()
