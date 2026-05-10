"""BIL HTTP server — receives behavioral signals, re-ranks search, clipboard intelligence."""
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from bil.bil_api import BIL
from bil.bil_features import extract_web_features, extract_clipboard_features

GITHUB_EVENTS_LOG = r"D:\BIL\data\github\github_events.jsonl"
EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports"))
EVENTS_LOG = os.path.join(EXPORT_DIR, "bil_events.jsonl")
CLIPBOARD_LOG = os.path.join(EXPORT_DIR, "clipboard_history.jsonl")


class BILHandler(BaseHTTPRequestHandler):
    bil = BIL()
    clipboard_history = []  # Ring buffer of recent clips for prediction

    def do_GET(self):
        parsed = urlparse(self.path)
        p = parsed.path

        if p == "/bil/clipboard/predict":
            self._handle_clipboard_predict(parsed)
        elif p == "/bil/context":
            self._handle_context(parsed)
        elif p == "/bil/summary":
            self._handle_summary(parsed)
        elif p == "/bil/decide":
            self._handle_decide(parsed)
        elif p == "/bil/status":
            self._json_response({
                "status": "ok",
                "models": {name: model.get_summary() for name, model in self.bil.models.items()},
                "clipboard_history_size": len(self.clipboard_history),
                "decision_bands": {
                    "prioritize": "score >= 0.72",
                    "consider": "0.55 - 0.71",
                    "neutral": "0.40 - 0.54",
                    "deprioritize": "score < 0.40",
                },
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
        elif self.path == "/bil/decide":
            self._handle_decide_post(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_web(self, body: bytes):
        """Receive a browser behavioral event and learn from it."""
        data = json.loads(body)
        features, signal = extract_web_features(
            url=data.get("url", ""),
            text=data.get("text_preview") or data.get("title", ""),
            time_on_page=data.get("time_on_page", 0),
            scrolled_bottom=data.get("scrolledBottom", False),
            bookmarked=data.get("bookmarked", False),
            copied=data.get("copied", False),
        )
        if data.get("search_query"):
            features["search_query"] = data.get("search_query", "")
        if data.get("search_result_position") is not None:
            features["search_result_position"] = int(data.get("search_result_position") or 0)
            if features["search_result_position"] > 3 and signal > 0.5:
                signal += 0.1
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
        append_jsonl(CLIPBOARD_LOG, entry)

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

    def _handle_decide(self, parsed):
        """Score one URL/title/snippet and return a decision band."""
        qs = parse_qs(parsed.query)
        data = {
            "url": qs.get("url", [""])[0],
            "title": qs.get("title", [""])[0],
            "content": qs.get("content", [""])[0],
            "engine": qs.get("engine", ["manual"])[0],
            "score": float(qs.get("score", ["1"])[0] or 1),
            "position": int(qs.get("position", ["0"])[0] or 0),
        }
        self._score_candidate(data)

    def _handle_decide_post(self, body: bytes):
        self._score_candidate(json.loads(body))

    def _score_candidate(self, data: dict):
        from bil.bil_features import extract_search_result_features
        features = extract_search_result_features(
            url=data.get("url", ""),
            title=data.get("title", ""),
            snippet=data.get("content", "") or data.get("snippet", ""),
            engine=data.get("engine", "manual"),
            score=float(data.get("score", 1) or 1),
            position=int(data.get("position", 0) or 0),
        )
        decision = self.bil.decide("web", features)
        self._json_response({"candidate": data, "decision": decision})

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

    def _handle_summary(self, parsed):
        qs = parse_qs(parsed.query)
        limit = int(qs.get("limit", ["10"])[0])
        self._json_response(build_summary(self.bil, self.clipboard_history, limit=limit))

    def _handle_context(self, parsed):
        qs = parse_qs(parsed.query)
        limit = int(qs.get("limit", ["8"])[0])
        summary = build_summary(self.bil, self.clipboard_history, limit=limit)
        self._json_response({
            "status": "ok",
            "generated_at": datetime.now().isoformat(),
            "current_mode_guess": infer_mode(summary),
            "working_memory": {
                "recent_clipboard": summary["clipboard"]["recent"],
                "top_domains": summary["domains"]["most_seen"],
                "positive_domains": summary["domains"]["positive"],
                "search_queries": summary["search"]["queries"],
                "keywords": summary["keywords"],
            },
            "open_loops": [
                {
                    "title": "Reload browser extension",
                    "why": "Load the unpacked extension from X:\\chrome-plugin to use the latest search and clipboard signals.",
                    "target": "browser",
                },
                {
                    "title": "Live-test SearXNG ranking",
                    "why": "The re-ranker is implemented, but it needs a real SearXNG query/click test in Edge.",
                    "target": "codex",
                },
                {
                    "title": "Add paste/reuse detection",
                    "why": "Clipboard copy is captured; stronger paste/reuse detection is the next preference signal.",
                    "target": "bil",
                },
                {
                    "title": "Define truth/fruits schemas",
                    "why": "The personal dashboard needs first-pass fields for truthful/deceptive and fruits/coherence scoring.",
                    "target": "dashboard",
                },
            ],
            "suggested_next_actions": [
                "Reload the unpacked extension from X:\\chrome-plugin.",
                "Run one SearXNG search, click the result you actually wanted, then refresh the dashboard.",
                "Use clipboard normally for a day so BIL can learn repeated clips.",
                "Add truth/fruits scoring schema to the personal dashboard next.",
            ],
            "endpoints": {
                "summary": "GET /bil/summary",
                "rank": "POST /bil/rank",
                "decide": "GET/POST /bil/decide",
                "clipboard_predict": "GET /bil/clipboard/predict",
            },
        })

    def _build_summary_deprecated(self, limit):
        events = read_jsonl(EVENTS_LOG, max_lines=5000)
        github_events = read_jsonl(GITHUB_EVENTS_LOG, max_lines=1000)

        model_counts = Counter(e.get("model", "unknown") for e in events)
        domains = Counter()
        positive_domains = Counter()
        negative_domains = Counter()
        queries = Counter()
        positions = []
        keywords = Counter()
        clipboard_counts = Counter()
        clipboard_examples = {}
        signal_by_domain = defaultdict(list)

        for event in events:
            features = event.get("features") or {}
            signal = float(event.get("signal", 0) or 0)
            domain = features.get("domain")
            if domain:
                domains[domain] += 1
                signal_by_domain[domain].append(signal)
                if signal >= 0.5:
                    positive_domains[domain] += 1
                elif signal <= 0.1:
                    negative_domains[domain] += 1
            if features.get("search_query"):
                queries[features["search_query"]] += 1
            if features.get("search_result_position") is not None:
                positions.append(int(features.get("search_result_position") or 0))
            for kw in features.get("top_keywords") or features.get("text_keywords") or []:
                keywords[kw] += 1

        for entry in self.clipboard_history:
            text = (entry.get("text") or "").strip()
            if not text:
                continue
            key = entry.get("hash") or text[:120]
            clipboard_counts[key] += int(entry.get("repeat_count") or 1)
            clipboard_examples[key] = text[:180]

        domain_scores = []
        for domain, signals in signal_by_domain.items():
            avg = sum(signals) / len(signals)
            domain_scores.append({
                "domain": domain,
                "events": len(signals),
                "avg_signal": round(avg, 3),
            })
        domain_scores.sort(key=lambda x: (x["avg_signal"], x["events"]), reverse=True)

        self._json_response({
            "status": "ok",
            "models": {name: model.get_summary() for name, model in self.bil.models.items()},
            "events": {
                "total": len(events),
                "by_model": dict(model_counts),
            },
            "domains": {
                "most_seen": top_pairs(domains, limit),
                "positive": top_pairs(positive_domains, limit),
                "quick_bounce": top_pairs(negative_domains, limit),
                "ranked_by_signal": domain_scores[:limit],
            },
            "search": {
                "queries": top_pairs(queries, limit),
                "clicked_positions": {
                    "count": len(positions),
                    "average": round(sum(positions) / len(positions), 2) if positions else None,
                    "latest": positions[-10:],
                },
            },
            "clipboard": {
                "history_size": len(self.clipboard_history),
                "recent": self.clipboard_history[-limit:][::-1],
                "frequent": [
                    {"name": clipboard_examples.get(key, key), "count": count}
                    for key, count in clipboard_counts.most_common(limit)
                ],
            },
            "keywords": top_pairs(keywords, limit),
            "github": {
                "events": len(github_events),
                "recent": github_events[-limit:][::-1],
            },
        })

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
    BILHandler.clipboard_history = load_clipboard_history()
    replay_historical_events(BILHandler.bil)
    server = HTTPServer(("0.0.0.0", port), BILHandler)
    print(f"BIL server on http://0.0.0.0:{port}")
    print(f"  POST /bil/web          - learn from browser behavior")
    print(f"  POST /bil/clipboard    - learn from clipboard events")
    print(f"  POST /bil/rank         - re-rank SearXNG results")
    print(f"  POST /bil/github       - learn from GitHub repo events")
    print(f"  GET  /bil/summary      - preference machine summary")
    print(f"  GET  /bil/decide       - score one URL/title/snippet")
    print(f"  POST /bil/decide       - score one candidate JSON object")
    print(f"  GET  /bil/clipboard/predict - get clipboard predictions")
    print(f"  GET  /bil/status       - server status + model stats")
    server.serve_forever()


def append_jsonl(path, entry):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def read_jsonl(path, max_lines=1000):
    if not os.path.exists(path):
        return []
    items = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[-max_lines:]:
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def load_clipboard_history():
    return read_jsonl(CLIPBOARD_LOG, max_lines=500)


def top_pairs(counter, limit):
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def build_summary(bil, clipboard_history, limit=10):
    events = read_jsonl(EVENTS_LOG, max_lines=5000)
    github_events = read_jsonl(GITHUB_EVENTS_LOG, max_lines=1000)

    model_counts = Counter(e.get("model", "unknown") for e in events)
    domains = Counter()
    positive_domains = Counter()
    negative_domains = Counter()
    queries = Counter()
    positions = []
    keywords = Counter()
    clipboard_counts = Counter()
    clipboard_examples = {}
    signal_by_domain = defaultdict(list)

    for event in events:
        features = event.get("features") or {}
        signal = float(event.get("signal", 0) or 0)
        domain = features.get("domain")
        if domain:
            domains[domain] += 1
            signal_by_domain[domain].append(signal)
            if signal >= 0.5:
                positive_domains[domain] += 1
            elif signal <= 0.1:
                negative_domains[domain] += 1
        if features.get("search_query"):
            queries[features["search_query"]] += 1
        if features.get("search_result_position") is not None:
            positions.append(int(features.get("search_result_position") or 0))
        for kw in features.get("top_keywords") or features.get("text_keywords") or []:
            keywords[kw] += 1

    for entry in clipboard_history:
        text = (entry.get("text") or "").strip()
        if not text:
            continue
        key = entry.get("hash") or text[:120]
        clipboard_counts[key] += int(entry.get("repeat_count") or 1)
        clipboard_examples[key] = text[:180]

    domain_scores = []
    for domain, signals in signal_by_domain.items():
        avg = sum(signals) / len(signals)
        domain_scores.append({
            "domain": domain,
            "events": len(signals),
            "avg_signal": round(avg, 3),
        })
    domain_scores.sort(key=lambda x: (x["avg_signal"], x["events"]), reverse=True)

    return {
        "status": "ok",
        "models": {name: model.get_summary() for name, model in bil.models.items()},
        "events": {
            "total": len(events),
            "by_model": dict(model_counts),
        },
        "domains": {
            "most_seen": top_pairs(domains, limit),
            "positive": top_pairs(positive_domains, limit),
            "quick_bounce": top_pairs(negative_domains, limit),
            "ranked_by_signal": domain_scores[:limit],
        },
        "search": {
            "queries": top_pairs(queries, limit),
            "clicked_positions": {
                "count": len(positions),
                "average": round(sum(positions) / len(positions), 2) if positions else None,
                "latest": positions[-10:],
            },
        },
        "clipboard": {
            "history_size": len(clipboard_history),
            "recent": clipboard_history[-limit:][::-1],
            "frequent": [
                {"name": clipboard_examples.get(key, key), "count": count}
                for key, count in clipboard_counts.most_common(limit)
            ],
        },
        "keywords": top_pairs(keywords, limit),
        "github": {
            "events": len(github_events),
            "recent": github_events[-limit:][::-1],
        },
    }


def infer_mode(summary):
    recent_clipboard = " ".join(item.get("text", "") for item in summary["clipboard"]["recent"][:3]).lower()
    top_domains = [item["name"] for item in summary["domains"]["most_seen"][:5]]
    keywords = [item["name"].lower() for item in summary["keywords"][:8]]
    haystack = " ".join(top_domains + keywords + [recent_clipboard])

    if any(term in haystack for term in ["github", "code", "api", "plugin", "python", "cloudflare"]):
        return {"mode": "build", "confidence": 0.72}
    if any(term in haystack for term in ["paper", "research", "theophysics", "equation", "youtube"]):
        return {"mode": "research", "confidence": 0.68}
    if any(term in haystack for term in ["gmail", "calendar", "dashboard", "nas"]):
        return {"mode": "admin", "confidence": 0.6}
    return {"mode": "mixed", "confidence": 0.5}


def replay_historical_events(bil):
    events = read_jsonl(EVENTS_LOG, max_lines=10000)
    if not events:
        return
    current_count = sum(model.get_summary().get("event_count", 0) for model in bil.models.values())
    if current_count >= int(len(events) * 0.8):
        return
    replayed = 0
    for event in events:
        model_name = event.get("model")
        features = event.get("features")
        signal = event.get("signal", 0)
        if model_name in bil.models and isinstance(features, dict):
            bil.models[model_name].learn(features, signal)
            replayed += 1
    if replayed and hasattr(bil, "_save_models"):
        bil._save_models()


if __name__ == "__main__":
    start_bil_server()
