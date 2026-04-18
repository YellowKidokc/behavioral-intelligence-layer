"""Folder ingestion pipeline for BIL.

Walks a directory tree, extracts lightweight metadata (and a content snippet
for text-like files), and POSTs one signal per file to the BIL server so the
models can learn what topics and file types the user cares about before any
browsing has happened.

Usage:
    python -m bil.ingest --path "/volume1/Research/Physics"
    python -m bil.ingest --path "O:/_Theophysics_v3" --host http://localhost:8420
    python -m bil.ingest --path . --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

# File-size ceiling for "read a content snippet" and for ingestion at all.
MAX_SNIPPET_BYTES = 2000
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB

TEXTUAL_EXTS = {".txt", ".md", ".py", ".rst", ".json", ".yaml", ".yml",
                ".csv", ".tsv", ".log", ".ini", ".toml", ".html", ".htm",
                ".js", ".ts", ".tsx", ".jsx", ".css", ".go", ".rs", ".java",
                ".c", ".h", ".cpp", ".hpp", ".sh", ".sql"}
PDF_EXTS = {".pdf"}
DOCX_EXTS = {".docx"}

SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_DIRS = {"__pycache__", ".git", ".hg", ".svn", "node_modules",
             ".venv", "venv", ".mypy_cache", ".pytest_cache", ".idea",
             ".vscode"}

DEFAULT_HOST = "http://192.168.1.177:8420"


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------

def _read_text_snippet(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return f.read(MAX_SNIPPET_BYTES)
    except Exception:
        return ""


def _read_pdf_snippet(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
        text_parts: list[str] = []
        for page in reader.pages[:3]:
            text_parts.append(page.extract_text() or "")
            if sum(len(p) for p in text_parts) >= MAX_SNIPPET_BYTES:
                break
        return ("\n".join(text_parts))[:MAX_SNIPPET_BYTES]
    except Exception:
        return ""


def _read_docx_snippet(path: Path) -> str:
    try:
        import docx  # python-docx
    except ImportError:
        return ""
    try:
        document = docx.Document(str(path))
        collected: list[str] = []
        total = 0
        for para in document.paragraphs:
            collected.append(para.text)
            total += len(para.text)
            if total >= MAX_SNIPPET_BYTES:
                break
        return ("\n".join(collected))[:MAX_SNIPPET_BYTES]
    except Exception:
        return ""


def read_snippet(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in TEXTUAL_EXTS:
        return _read_text_snippet(path)
    if ext in PDF_EXTS:
        return _read_pdf_snippet(path)
    if ext in DOCX_EXTS:
        return _read_docx_snippet(path)
    return ""


def extract_keywords(text: str, top: int = 5) -> list[str]:
    if not text.strip():
        return []
    try:
        import yake
    except ImportError:
        return []
    try:
        extractor = yake.KeywordExtractor(lan="en", n=2, top=top)
        return [kw for kw, _score in extractor.extract_keywords(text)]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Signal construction
# ---------------------------------------------------------------------------

@dataclass
class FileSignal:
    source: str
    path: str
    filename: str
    extension: str
    folder: str
    size_bytes: int
    modified_days_ago: int
    snippet: str
    keywords: list
    engagement_score: float


def engagement_score(modified_days_ago: int, size_bytes: int, extension: str) -> float:
    base = 0.5
    if modified_days_ago < 7:
        base += 0.3
    elif modified_days_ago < 30:
        base += 0.15
    if size_bytes > 100_000:
        base += 0.1
    if extension in {".pdf", ".py", ".md"}:
        base += 0.1
    return min(base, 1.0)


def build_signal(path: Path) -> Optional[FileSignal]:
    try:
        stat = path.stat()
    except OSError:
        return None
    size = stat.st_size
    if size > MAX_FILE_BYTES:
        return None
    modified = datetime.fromtimestamp(stat.st_mtime)
    days_ago = max(0, (datetime.now() - modified).days)
    snippet = read_snippet(path)
    ext = path.suffix.lower()
    return FileSignal(
        source="file_ingest",
        path=str(path),
        filename=path.name,
        extension=ext,
        folder=path.parent.name,
        size_bytes=size,
        modified_days_ago=days_ago,
        snippet=snippet[:200],
        keywords=extract_keywords(snippet),
        engagement_score=round(engagement_score(days_ago, size, ext), 3),
    )


# ---------------------------------------------------------------------------
# Walking / transport
# ---------------------------------------------------------------------------

def iter_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in _walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if name in SKIP_NAMES:
                continue
            yield Path(current) / name


def _walk(root: Path):
    # Thin wrapper so tests can monkeypatch; mirrors os.walk's contract.
    import os
    for current, dirs, files in os.walk(root):
        yield current, dirs, files


def post_signal(host: str, signal: FileSignal, timeout: float = 5.0) -> bool:
    url = host.rstrip("/") + "/bil/web"
    payload = json.dumps(asdict(signal)).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a folder into BIL")
    parser.add_argument("--path", required=True, help="Folder to ingest (recursive)")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"BIL server base URL (default: {DEFAULT_HOST})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print signals instead of POSTing")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.exists() or not root.is_dir():
        print(f"[bil.ingest] path not found or not a directory: {root}", file=sys.stderr)
        return 2

    # First pass: count so the progress line is informative.
    files = list(iter_files(root))
    total = len(files)
    print(f"Ingesting {total} files from {root}...")

    sent = 0
    failed = 0
    started = time.time()
    for i, path in enumerate(files, 1):
        signal = build_signal(path)
        if signal is None:
            continue
        if args.dry_run:
            print(json.dumps(asdict(signal), default=str))
            sent += 1
        else:
            if post_signal(args.host, signal):
                sent += 1
            else:
                failed += 1
        if i % 50 == 0 or i == total:
            elapsed = time.time() - started
            print(f"  [{i}/{total}] sent={sent} failed={failed} "
                  f"({elapsed:.1f}s elapsed)")

    print(f"Sent {sent} signals. BIL now knows your file library.")
    if failed:
        print(f"({failed} signals failed to POST — is the BIL server up at {args.host}?)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
