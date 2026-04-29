"""BIL API — FastAPI server for NAS Brain Drive.
Accepts captures, ratings, GitHub events, and Ollama vision requests.
Runs on port 8420, volume-mounted to /data/ (maps to /volume1/brain/).
"""
import base64
import json
import os
import uuid
from datetime import datetime

import httpx
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="BIL Brain API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA = os.environ.get("BIL_DATA_DIR", "/data")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")

def _log(msg: str):
    ts = datetime.now().isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    log_path = os.path.join(DATA, "logs", "bil_api.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def _jsonl_append(subdir: str, filename: str, obj: dict):
    path = os.path.join(DATA, subdir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")


@app.get("/status")
def status():
    counts = {}
    for subdir in ["captures", "understood", "ratings", "github", "embeddings", "memory", "digests"]:
        d = os.path.join(DATA, subdir)
        if os.path.isdir(d):
            counts[subdir] = len(os.listdir(d))
        else:
            counts[subdir] = 0
    return {"status": "ok", "data_dir": DATA, "counts": counts}


@app.post("/capture")
async def capture(
    file: UploadFile = File(...),
    source: str = Form("desktop"),
    app_name: str = Form("unknown"),
):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    event_id = f"cap_{ts}_{uuid.uuid4().hex[:6]}"
    ext = os.path.splitext(file.filename or "img.png")[1] or ".png"
    save_path = os.path.join(DATA, "captures", f"{event_id}{ext}")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    meta = {
        "event_id": event_id,
        "ts": datetime.now().isoformat(),
        "source": source,
        "app": app_name,
        "file": save_path,
        "size_bytes": len(content),
    }
    _jsonl_append("logs", "captures.jsonl", meta)
    _log(f"Capture saved: {event_id} ({len(content)} bytes)")
    return {"status": "ok", "event_id": event_id, "file": save_path}


@app.post("/rate")
async def rate(data: dict):
    event_id = data.get("event_id", "")
    rating = data.get("rating", 0)
    dataset = data.get("dataset", "general")
    note = data.get("note", "")

    entry = {
        "ts": datetime.now().isoformat(),
        "event_id": event_id,
        "rating": rating,
        "dataset": dataset,
        "note": note,
    }
    _jsonl_append("ratings", "ratings.jsonl", entry)
    _log(f"Rating: {event_id} = {rating} [{dataset}]")
    return {"status": "ok", "event_id": event_id, "rating": rating}


@app.post("/github")
async def github(data: dict):
    repo = data.get("repo", "")
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
        "stars": data.get("stars", 0),
        "forks": data.get("forks", 0),
        "language": data.get("language", ""),
        "topics": data.get("topics", []),
        "time_on_page": time_on_page,
        "copied_code": copied_code,
        "bookmarked": bookmarked,
        "score": round(score, 4),
    }
    _jsonl_append("github", "github_events.jsonl", event)
    _log(f"GitHub: {repo} score={score}")
    return {"status": "ok", "repo": repo, "score": round(score, 4)}


@app.post("/describe")
async def describe(data: dict):
    image_b64 = data.get("image", "")
    event_id = data.get("event_id", f"desc_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    model = data.get("model", "moondream")

    if not image_b64:
        return JSONResponse({"error": "no image provided"}, status_code=400)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": "Describe what is on this screen in one sentence. Focus on: app name, main content, what the user is doing.",
                    "images": [image_b64],
                    "stream": False,
                },
            )
            description = resp.json().get("response", "").strip()
    except Exception as e:
        _log(f"Ollama error: {e}")
        return JSONResponse({"error": str(e), "event_id": event_id}, status_code=502)

    desc_path = os.path.join(DATA, "understood", f"{event_id}.txt")
    os.makedirs(os.path.dirname(desc_path), exist_ok=True)
    with open(desc_path, "w", encoding="utf-8") as f:
        f.write(description)

    _log(f"Described: {event_id} → {description[:80]}")
    return {"status": "ok", "event_id": event_id, "description": description}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8420)
