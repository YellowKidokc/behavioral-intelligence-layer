# BIL — Behavioral Intelligence Layer
**A local-first personal intelligence system**
*David Lowe | POF 2828 | April 2026*

---

## What This Is

A privacy-first intelligence layer that sits between you and information. It captures what you interact with — browser activity, screenshots, clipboard, GitHub repos — learns what matters to you, and builds a preference model that gets smarter over time.

**Core loop:**
```
Capture → Understand → Embed → Score → Remember → Synthesize
```

Nothing leaves your network. Runs on a Synology NAS with Docker. Ollama handles vision and language. The BIL preference engine learns from every signal.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  DESKTOP (Windows)                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐│
│  │ Hotkey Capture│  │ Screen Watch │  │ Browser Extension      ││
│  │ Ctrl+Shift+S │  │ Auto every N │  │ Dwell/Scroll/Copy/     ││
│  │ → Screenshot  │  │ min captures │  │ Bookmark/GitHub Parse  ││
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘│
│         │                  │                       │             │
│         └──────────────────┼───────────────────────┘             │
│                            │ POST                                │
└────────────────────────────┼────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  NAS (Synology / Docker)                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐│
│  │ BIL API      │  │ Ollama       │  │ Brain Drive            ││
│  │ :8420        │  │ :11434       │  │ /volume1/brain/        ││
│  │ FastAPI      │  │ Moondream    │  │ captures/ understood/  ││
│  │ Preference   │  │ LLaVA        │  │ ratings/ embeddings/   ││
│  │ Engine       │  │ Llama3       │  │ github/ memory/        ││
│  └──────────────┘  └──────────────┘  └────────────────────────┘│
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ Qdrant       │  │ Infinity     │                             │
│  │ :6333        │  │ :7997        │                             │
│  │ Vector DB    │  │ Embeddings   │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Windows 10/11 desktop
- Synology NAS (or any Linux box with Docker)
- Python 3.10+
- Docker + Portainer (recommended)

### 1. Clone and install desktop deps

```bash
git clone https://github.com/yourusername/bil.git
cd bil
pip install -r requirements.txt
```

### 2. Deploy NAS services via Portainer

Go to **Stacks → Add Stack → name: `bil`** and paste:

```yaml
version: "3.9"
services:
  bil-api:
    image: python:3.11-slim
    container_name: bil-api
    ports:
      - "8420:8420"
    volumes:
      - /volume1/brain:/data
      - /volume1/brain/deploy:/app
    working_dir: /app
    environment:
      - PIL_DATA_DIR=/data
      - OLLAMA_URL=http://YOUR_NAS_IP:11434
    command: >
      bash -c "pip install --no-cache-dir fastapi uvicorn httpx python-multipart -q &&
               uvicorn pil_api:app --host 0.0.0.0 --port 8420"
    restart: unless-stopped

  bil-qdrant:
    image: qdrant/qdrant:latest
    container_name: bil-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - /volume1/brain/embeddings:/qdrant/storage
    restart: unless-stopped

  bil-infinity:
    image: michaelf34/infinity:latest
    container_name: bil-infinity
    ports:
      - "7997:7997"
    volumes:
      - /volume1/brain/models:/app/.cache
    command: v2 --model-name-or-path sentence-transformers/all-MiniLM-L6-v2 --port 7997
    restart: unless-stopped
```

Replace `YOUR_NAS_IP` with your NAS IP address.

### 3. Create the Brain Drive on NAS

```bash
# Via SSH or Portainer console
for dir in models captures understood embeddings ratings knowledge memory digests logs github deploy; do
  mkdir -p /volume1/brain/$dir
done
```

### 4. Copy API server to NAS

```bash
cp nas-deploy/pil_api.py //YOUR_NAS_IP/brain/deploy/
cp nas-deploy/requirements.txt //YOUR_NAS_IP/brain/deploy/
```

### 5. Ensure Ollama has vision models

```bash
ollama pull moondream
ollama pull llava
```

### 6. Configure and run desktop capture

Edit the config at the top of `desktop-capture/hotkey_capture.py`:
```python
BIL_URL  = "http://localhost:8420"         # Local BIL server
NAS_URL  = "http://YOUR_NAS_IP:8420"       # NAS Brain API
OLLAMA_URL = "http://localhost:11434/api/generate"
```

Run:
```bash
python desktop-capture/hotkey_capture.py
```

Press **Ctrl+Shift+S** to capture, rate, and learn.

### 7. Install browser extension

1. Open Chrome → `chrome://extensions/` → Enable Developer Mode
2. Click "Load unpacked" → select `browser/` folder
3. The extension tracks dwell time, scroll depth, copy events, bookmarks, and GitHub repo data
4. All signals POST to BIL on :8420

---

## Folder Structure

```
bil/
├── README.md                        ← this file
├── requirements.txt                 ← Python deps for desktop
├── .env.example                     ← config template
├── .gitignore
│
├── behavioral-intelligence-layer-OBS-Plugin-Final-Claude/
│   └── bil/
│       ├── bil_server.py            ← BIL preference engine API (:8420)
│       ├── bil_models.py            ← River online learning models
│       ├── bil_api.py               ← Core BIL interface
│       └── bil_features.py          ← Feature extraction
│
├── browser/                         ← Chrome extension
│   ├── manifest.json
│   ├── background.js                ← Tab tracking, GitHub parser, signal sender
│   └── content.js                   ← Scroll/copy detection
│
├── desktop-capture/                 ← Desktop capture scripts
│   ├── hotkey_capture.py            ← Ctrl+Shift+S → screenshot → rate → learn
│   ├── watcher.py                   ← Passive screenshot every N minutes
│   └── describe_one.py              ← Send single image to Ollama
│
├── engines/
│   ├── threshold_engine.py          ← Signal threshold scoring
│   └── embeddings/
│       └── text_embedder.py         ← Infinity embedding client
│
├── nas-deploy/                      ← NAS deployment files
│   ├── pil_api.py                   ← FastAPI Brain API server
│   ├── requirements.txt             ← API server deps
│   ├── Dockerfile                   ← Container build
│   ├── docker-compose-pil-api.yml   ← Portainer-ready stack
│   └── deploy.sh                    ← SSH deploy script (alternative)
│
├── data/                            ← Local data (gitignored)
│   ├── captures/                    ← Raw screenshots
│   ├── understood/                  ← Moondream descriptions
│   ├── ratings/                     ← Explicit feedback log
│   ├── github/                      ← GitHub repo events
│   ├── memory/                      ← Topic clusters
│   ├── digests/                     ← Daily synthesis
│   └── logs/                        ← Build + runtime logs
│
├── scripts/
│   └── install.ps1                  ← Windows install script
│
└── ui/
    └── bil-dashboard.html           ← Local dashboard
```

---

## Services & Ports

| Service | Port | Location | Purpose |
|---------|------|----------|---------|
| BIL Preference Engine | 8420 | Desktop | Online learning from behavioral signals |
| Brain API (FastAPI) | 8420 | NAS | Central capture/rate/describe/github API |
| Ollama | 11434 | NAS | Vision (Moondream), Language (Llama3) |
| Qdrant | 6333 | NAS | Vector database for embeddings |
| Infinity | 7997 | NAS | Text embedding service |
| Open WebUI | 8271 | NAS | Chat interface for Ollama models |

---

## API Endpoints (Brain API on NAS)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/capture` | Upload screenshot + metadata |
| POST | `/rate` | Submit thumbs up/down rating |
| POST | `/github` | GitHub repo behavioral signal |
| POST | `/describe` | Send image to Ollama for description |
| GET | `/status` | Service health + data counts |

### BIL Server Endpoints (Desktop)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/bil/web` | Browser behavioral event |
| POST | `/bil/clipboard` | Clipboard event |
| POST | `/bil/github` | GitHub repo event |
| POST | `/bil/rank` | Re-rank SearXNG results |
| GET | `/bil/clipboard/predict` | Ranked clipboard predictions |
| GET | `/bil/status` | Model stats |

---

## Signal Scoring

### GitHub Repo Score
```
base signal = 0.3 (visited)
  +0.2 if copied_code
  +0.2 if bookmarked
  +0.1 if time_on_page > 60s
  +0.1 if time_on_page > 180s
  cap at 1.0
```

### Preference Score Formula
```python
score = (
    0.35 * similarity_to_liked_items
  - 0.25 * similarity_to_disliked_items
  + 0.20 * reuse_count
  + 0.10 * pinned_or_starred
  + 0.10 * recency
)
confidence = min(1.0, nearby_feedback_count / 10)
```

---

## Data Flow

1. **Capture** — Screenshot, clipboard copy, browser dwell, GitHub visit
2. **Understand** — Ollama Moondream describes screenshots in natural language
3. **Embed** — Infinity converts text/descriptions to vectors, stored in Qdrant
4. **Score** — BIL River models score each signal based on learned preferences
5. **Remember** — Events logged to JSONL, vectors stored, topics clustered
6. **Synthesize** — Daily digest summarizes what mattered (Ollama)

---

## Cloudflare Tunnels (Optional)

If you want remote access to NAS services, set up Cloudflare tunnels:

| Subdomain | Routes To |
|-----------|-----------|
| `brain.yourdomain.com` | `http://NAS_IP:8420` |
| `ollama.yourdomain.com` | `http://NAS_IP:11434` |
| `webui.yourdomain.com` | `http://NAS_IP:8271` |

---

## License

Private — not yet published. Contact David Lowe for access.

---

*This is not a dashboard. It's a filter for reality.*
*Build the signal layer first. Everything else compounds from there.*
