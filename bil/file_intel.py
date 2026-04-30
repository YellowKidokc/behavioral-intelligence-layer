"""File intelligence — classify, rename, and sort files via local Ollama.

Powers the /bil/classify, /bil/rename, and /bil/sort endpoints. Talks directly
to Ollama's HTTP API at ``OLLAMA_HOST`` (see ``bil.config``) using moondream
for images and mistral for text. The ``BIL_VISION_MODEL`` and
``BIL_TEXT_MODEL`` env vars override the defaults if you've pulled different
tags.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from bil.config import OLLAMA_HOST

VISION_MODEL = os.environ.get("BIL_VISION_MODEL", "moondream:latest")
TEXT_MODEL = os.environ.get("BIL_TEXT_MODEL", "mistral:latest")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}
DOC_TEXT_EXTS = {".txt", ".md", ".rst", ".log", ".py", ".js", ".ts",
                 ".json", ".yaml", ".yml", ".html", ".css"}
PDF_EXTS = {".pdf"}
DOCX_EXTS = {".docx"}

DESCRIBE_IMAGE_PROMPT = "Describe this image briefly in one sentence."

DESCRIBE_DOCUMENT_PROMPT = """\
Briefly describe what this document is about in one sentence.

FILENAME: {filename}
TEXT (first 2000 chars):
{text}
"""

CLASSIFY_PROMPT = """\
You are a file classifier. Given a description and filename, return a
classification as compact JSON only — no commentary, no code fences.

Categories and their prefixes:
  Physics=P, Trading=T, Finance=F, Research=R, Code=C, Personal=PR, Other=X

Suffixes describe the type:
  DIAG (diagram), CHART, PHOTO, SCAN, DOC, NOTE, CODE, DATA

Required JSON keys:
  category, prefix, suffix, description, suggested_name, confidence

`suggested_name` should be a short snake_case stem (no extension, no prefix,
no suffix — those are added by the caller).
`confidence` is a number between 0 and 1.

Description: {description}
Filename: {filename}
"""


# ---------------------------------------------------------------------------
# Ollama transport
# ---------------------------------------------------------------------------

def _ollama_post(payload: dict, timeout: float = 120.0) -> dict:
    url = OLLAMA_HOST.rstrip("/") + "/api/generate"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ollama_generate(prompt: str, model: str = TEXT_MODEL) -> str:
    data = _ollama_post({"model": model, "prompt": prompt, "stream": False})
    return (data.get("response") or "").strip()


def ollama_vision(image_path: Path, prompt: str = DESCRIBE_IMAGE_PROMPT,
                  model: str = VISION_MODEL) -> str:
    img_b64 = base64.b64encode(Path(image_path).read_bytes()).decode("utf-8")
    data = _ollama_post({
        "model": model,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False,
    })
    return (data.get("response") or "").strip()


# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------

def _file_kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in DOC_TEXT_EXTS or ext in PDF_EXTS or ext in DOCX_EXTS:
        return "document"
    return "other"


def _read_text(path: Path, max_chars: int = 2000) -> str:
    ext = path.suffix.lower()
    if ext in DOC_TEXT_EXTS:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
        except OSError:
            return ""
    if ext in PDF_EXTS:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(path))
            chunks = [(page.extract_text() or "") for page in reader.pages[:3]]
            return "\n".join(chunks)[:max_chars]
        except Exception:
            return ""
    if ext in DOCX_EXTS:
        try:
            import docx  # python-docx
            document = docx.Document(str(path))
            return "\n".join(p.text for p in document.paragraphs[:50])[:max_chars]
        except Exception:
            return ""
    return ""


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_NAME_SAFE = re.compile(r"[^A-Za-z0-9]+")


def _safe_name(name: str) -> str:
    cleaned = _NAME_SAFE.sub("_", name).strip("_")
    return cleaned or "untitled"


def _parse_classification(raw: str, filename: str) -> dict:
    """LLMs love to wrap JSON in commentary or code fences — strip and parse."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", raw.strip(),
                     flags=re.MULTILINE)
    parsed: dict = {}
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = {}
    return {
        "category": parsed.get("category") or "Other",
        "prefix": (parsed.get("prefix") or "X").upper(),
        "suffix": (parsed.get("suffix") or "FILE").upper(),
        "description": parsed.get("description") or "",
        "suggested_name": parsed.get("suggested_name") or Path(filename).stem,
        "confidence": float(parsed.get("confidence") or 0.5),
    }


def classify_file(path: Path) -> dict:
    """Classify one file using moondream (images) + mistral (structuring)."""
    path = Path(path)
    kind = _file_kind(path)
    if kind == "image":
        description = ollama_vision(path)
    elif kind == "document":
        text = _read_text(path)
        description = ollama_generate(
            DESCRIBE_DOCUMENT_PROMPT.format(
                filename=path.name,
                text=text or "(no readable text)",
            ),
        )
    else:
        description = ""

    raw = ollama_generate(
        CLASSIFY_PROMPT.format(
            description=description or "(no description)",
            filename=path.name,
        ),
    )
    info = _parse_classification(raw, path.name)
    if description and not info["description"]:
        info["description"] = description

    stem = _safe_name(info["suggested_name"])
    info["suggested_name"] = (
        f"{info['prefix']}_{stem}_{info['suffix']}{path.suffix.lower()}"
    )
    info["original_path"] = str(path)
    info["kind"] = kind
    return info


# ---------------------------------------------------------------------------
# Rename plan
# ---------------------------------------------------------------------------

_ALREADY_NAMED = re.compile(r"^[A-Z]{1,3}_.+_[A-Z]{2,5}\.[A-Za-z0-9]+$")


def _looks_already_named(path: Path) -> bool:
    return bool(_ALREADY_NAMED.match(path.name))


def _unique_target(target: Path) -> Path:
    if not target.exists():
        return target
    stem, ext = target.stem, target.suffix
    i = 1
    while True:
        candidate = target.with_name(f"{stem}_{i}{ext}")
        if not candidate.exists():
            return candidate
        i += 1


def build_rename_plan(folder: Path, dry_run: bool = True,
                      max_files: int = 200) -> dict:
    """Classify files in ``folder`` (non-recursive) and propose new names.

    With ``dry_run=False`` the renames are executed atomically per-file; an
    existing collision gets a numeric suffix instead of being clobbered.
    """
    folder = Path(folder)
    if not folder.is_dir():
        return {"error": f"not a directory: {folder}"}

    plan: list[dict] = []
    skipped: list[dict] = []
    total = 0
    for entry in sorted(folder.iterdir()):
        if not entry.is_file():
            continue
        total += 1
        if _looks_already_named(entry):
            skipped.append({"old": entry.name, "reason": "already_named"})
            continue
        if len(plan) >= max_files:
            skipped.append({"old": entry.name, "reason": "max_files_reached"})
            continue
        try:
            info = classify_file(entry)
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            skipped.append({"old": entry.name, "reason": f"classify_failed: {exc}"})
            continue
        item = {
            "old": entry.name,
            "new": info["suggested_name"],
            "description": info["description"],
            "confidence": info["confidence"],
        }
        if not dry_run:
            target = _unique_target(entry.with_name(info["suggested_name"]))
            entry.rename(target)
            item["final"] = target.name
        plan.append(item)

    return {
        "plan": plan,
        "stats": {
            "total": total,
            "already_named": sum(1 for s in skipped if s["reason"] == "already_named"),
            "to_rename": len(plan),
            "executed": not dry_run,
        },
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# Sort plan
# ---------------------------------------------------------------------------

def build_sort_plan(input_path: Path, output_path: Path,
                    mode: str = "content", dry_run: bool = True,
                    max_files: int = 200) -> dict:
    """Classify files under ``input_path`` and group them into category
    subdirectories under ``output_path``.

    ``mode`` is accepted for API parity with the upcoming Local-File-Organizer
    fork; only ``"content"`` is wired up so far.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.is_dir():
        return {"error": f"input not a directory: {input_path}"}
    if mode != "content":
        return {"error": f"mode {mode!r} not implemented yet"}

    proposed_tree: dict[str, list[str]] = {}
    operations: list[dict] = []
    seen = 0
    for entry in input_path.rglob("*"):
        if not entry.is_file():
            continue
        if seen >= max_files:
            break
        seen += 1
        try:
            info = classify_file(entry)
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            operations.append({
                "src": str(entry), "error": f"classify_failed: {exc}"
            })
            continue
        category = info["category"]
        target_dir = output_path / category
        target = _unique_target(target_dir / info["suggested_name"])
        proposed_tree.setdefault(category, []).append(target.name)
        operations.append({
            "src": str(entry),
            "dst": str(target),
            "category": category,
            "description": info["description"],
            "confidence": info["confidence"],
        })
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(entry), str(target))

    return {
        "proposed_tree": proposed_tree,
        "operations": operations,
        "stats": {"total": seen, "executed": not dry_run, "mode": mode},
    }
