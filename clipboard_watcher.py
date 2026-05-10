"""
clipboard_watcher.py
Lightweight Windows clipboard input for the BIL preference engine.

It watches text copied to the system clipboard and sends it to:
  http://localhost:8420/bil/clipboard

This is intentionally small: no global key hooks, no screenshots, no cloud calls.
"""

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib import request

import tkinter as tk


BIL_CLIPBOARD_URL = "http://localhost:8420/bil/clipboard"
LOCAL_LOG = Path(r"D:\BIL\data\clipboard\clipboard_watcher.jsonl")
POLL_SECONDS = 0.75
MAX_TEXT_CHARS = 5000
MIN_TEXT_CHARS = 2


def post_json(url, payload, timeout=2):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def append_jsonl(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def read_clipboard(root):
    try:
        value = root.clipboard_get()
    except Exception:
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()


def main():
    root = tk.Tk()
    root.withdraw()

    last_hash = None
    seen_counts = {}

    print("BIL clipboard watcher running. Press Ctrl+C to stop.")
    while True:
        text = read_clipboard(root)
        if len(text) >= MIN_TEXT_CHARS:
            h = text_hash(text)
            if h != last_hash:
                seen_counts[h] = seen_counts.get(h, 0) + 1
                last_hash = h
                payload = {
                    "text": text[:MAX_TEXT_CHARS],
                    "app": "windows_clipboard",
                    "used": seen_counts[h] > 1,
                    "repeat_count": seen_counts[h],
                    "source": "clipboard_watcher",
                    "hash": h,
                    "ts": datetime.now().isoformat(),
                }
                append_jsonl(LOCAL_LOG, payload)
                try:
                    post_json(BIL_CLIPBOARD_URL, payload)
                except Exception as exc:
                    print(f"BIL clipboard post failed: {exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    os.makedirs(LOCAL_LOG.parent, exist_ok=True)
    main()
