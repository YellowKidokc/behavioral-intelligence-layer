"""Ollama front-end for BIL.

Reads the latest BIL digest (either from the exports directory or from a
running server), sends it to a local Ollama model as context, and streams the
response to stdout. Optionally feeds the LLM's reply back into BIL as a
high-confidence ``llm_reflection`` signal.

Usage:
    python -m bil.llm_query "What should I focus on today?"
    python -m bil.llm_query "Summarize my week" --model mistral --feed-back
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from bil.config import BIL_HOST as DEFAULT_BIL
from bil.config import OLLAMA_HOST as DEFAULT_OLLAMA
from bil.config import OLLAMA_MODEL as DEFAULT_MODEL

DEFAULT_EXPORTS = Path("exports")

SYSTEM_PROMPT = (
    "You are a personal focus assistant. You have access to a digest of the "
    "user's recent digital behavior — pages visited, files accessed, content "
    "copied. Answer questions about their focus, interests, and priorities. "
    "Be concise and specific."
)


# ---------------------------------------------------------------------------
# Digest loading
# ---------------------------------------------------------------------------

def latest_digest_from_disk(exports: Path) -> Optional[dict]:
    if not exports.exists():
        return None
    candidates = sorted(exports.glob("bil_digest_*.json"))
    if not candidates:
        return None
    try:
        return json.loads(candidates[-1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def digest_from_server(host: str, timeout: float = 5.0) -> Optional[dict]:
    url = host.rstrip("/") + "/bil/export"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
        return None
    return None


def load_digest(exports: Path, host: str) -> dict:
    """Prefer the local export file; fall back to asking the server."""
    digest = latest_digest_from_disk(exports)
    if digest is not None:
        return digest
    digest = digest_from_server(host)
    if digest is not None:
        return digest
    return {"note": "no digest available yet — browse a bit or run bil.ingest first"}


def summarize_digest(digest: dict, max_chars: int = 4000) -> str:
    """Trim the raw digest to something an LLM can chew on."""
    try:
        text = json.dumps(digest, indent=2, default=str)
    except TypeError:
        text = str(digest)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

def ollama_stream(ollama_host: str, model: str, system: str, user: str) -> str:
    """POST to /api/generate with stream=True, print chunks, return full text."""
    url = ollama_host.rstrip("/") + "/api/generate"
    body = json.dumps({
        "model": model,
        "system": system,
        "prompt": user,
        "stream": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    collected: list[str] = []
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw in resp:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                piece = chunk.get("response", "")
                if piece:
                    sys.stdout.write(piece)
                    sys.stdout.flush()
                    collected.append(piece)
                if chunk.get("done"):
                    break
    except urllib.error.URLError as err:
        print(f"\n[bil.llm_query] could not reach Ollama at {ollama_host}: {err}",
              file=sys.stderr)
        return ""
    sys.stdout.write("\n")
    return "".join(collected)


# ---------------------------------------------------------------------------
# Feedback loop
# ---------------------------------------------------------------------------

def post_reflection(bil_host: str, text: str, query: str) -> bool:
    url = bil_host.rstrip("/") + "/bil/web"
    payload = json.dumps({
        "source": "llm_reflection",
        "query": query,
        "text": text,
        "engagement_score": 0.9,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Query Ollama with BIL digest as context")
    parser.add_argument("query", nargs="+", help="Natural-language question")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--ollama", default=DEFAULT_OLLAMA,
                        help=f"Ollama base URL (default: {DEFAULT_OLLAMA})")
    parser.add_argument("--bil", default=DEFAULT_BIL,
                        help=f"BIL base URL (default: {DEFAULT_BIL})")
    parser.add_argument("--exports", default=str(DEFAULT_EXPORTS),
                        help="Path to local exports/ dir")
    parser.add_argument("--feed-back", action="store_true",
                        help="After the reply, ask whether to POST it back to BIL")
    args = parser.parse_args(argv)

    query = " ".join(args.query).strip()
    digest = load_digest(Path(args.exports), args.bil)

    user_message = (
        "DIGEST OF RECENT BEHAVIOR:\n"
        f"{summarize_digest(digest)}\n\n"
        "USER QUERY:\n"
        f"{query}"
    )

    reply = ollama_stream(args.ollama, args.model, SYSTEM_PROMPT, user_message)

    if args.feed_back and reply:
        try:
            answer = input("\nFeed this back into BIL? [y/N] ").strip().lower()
        except EOFError:
            answer = ""
        if answer in {"y", "yes"}:
            ok = post_reflection(args.bil, reply, query)
            print("Reflection stored." if ok else "Failed to POST reflection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
