# Behavioral Intelligence Layer (BIL)

> A self-hosted preference engine that lives on your network drive, learns from everything you do, and re-ranks search results, files, tabs, and content to match *your* brain — not an ad algorithm's.

Extracted from [FIS (File Intelligence System)](https://github.com/YellowKidokc/file-intelligence-system). BIL is the standalone learning layer — FIS uses it, but so can SearXNG, your browser, your Synology, and anything else on your network.

---

## The Vision

You have a Synology NAS. You have a Cloudflare Tunnel. You have SearXNG running at `search.dlowehomelab.com`. You browse the web, save files, copy text, and open tabs — and none of that knowledge goes anywhere useful.

BIL changes that.

**One central service on your NAS. Every device on your network feeds it signals. It learns your preferences continuously. It re-ranks everything.**

```
YOUR NETWORK (YellowkidNas)
─────────────────────────────────────────────────────────────
  Synology NAS (192.168.1.177)
  │
  ├── BIL Server :8420          ← THE BRAIN
  │   ├── POST /bil/web         ← learns from browser behavior  
  │   ├── POST /bil/rank        ← re-ranks SearXNG results
  │   ├── POST /bil/folder      ← ingests any folder you drop in
  │   └── POST /bil/signal      ← generic signal from any source
  │
  ├── SearXNG :5147             ← privacy search
  ├── Ollama  :11434            ← local LLM (llama3, mistral)
  └── Postgres                  ← event log + embeddings

YOUR DEVICES
─────────────────────────────────────────────────────────────
  Desktop  ──→ browser extension ──→ BIL /bil/web
  Laptop   ──→ browser extension ──→ BIL /bil/web  
  Phone    ──→ search.dlowehomelab.com ──→ SearXNG ──→ BIL /bil/rank
  
  Any folder ──→ `bil ingest /path/to/folder` ──→ BIL learns it
```

---

## What It Does Today

| Capability | Status |
|---|---|
| Learn from web browsing (time, scroll, copy, bookmark) | ✅ Working |
| Re-rank SearXNG search results | ✅ Working |
| Online learning — updates instantly, no retraining | ✅ Working (River) |
| Browser extension (Chrome/Edge, Manifest V3) | ✅ Working |
| JSONL event log (no Postgres required) | ✅ Working |
| Keyword extraction via YAKE | ✅ Working |
| Folder ingestion pipeline (PDF / DOCX / text) | ✅ Working |
| Ollama LLM front-end with digest context + feedback loop | ✅ Working |

## What's Coming (The Pipeline)

| Capability | Priority |
|---|---|
| **Tab order ranking** — BIL scores open tabs by predicted interest | 🔜 Next |
| **Network sync** — preferences sync across all devices via NAS | 🔜 Next |
| Vector embeddings for semantic similarity | 📋 Planned |
| Raindrop.io bookmark signal integration | 📋 Planned |
| Postgres persistent event store | 📋 Planned |

---

## Architecture: The Full Pipeline

```
INPUT SOURCES
─────────────────────────────────────────────────────────────
Browser (any device)     File System (NAS/local)    Manual signal
       │                        │                       │
       │ scroll, copy,          │ watchdog or           │ explicit
       │ time, bookmark         │ CLI ingest            │ thumbs up/down
       ▼                        ▼                       ▼
─────────────────────────────────────────────────────────────
SIGNAL LAYER  (POST /bil/web, /bil/folder, /bil/signal)
─────────────────────────────────────────────────────────────
       │
       ▼
FEATURE EXTRACTION (bil_features.py)
  • domain, keywords (YAKE), word count, time, scroll depth
  • folder: domain code, subject code, confidence, slug
  • content: TF-IDF or sentence embedding
       │
       ▼
─────────────────────────────────────────────────────────────
LEARNING LAYER  (bil_models.py — River online ML)
─────────────────────────────────────────────────────────────
  WebModel       — which pages/domains you engage with
  FileModel      — which files/subjects you actually use  
  ClipboardModel — what you copy and actually paste
  ContentModel   — what content you agree with (0-10 score)
       │
       ▼
─────────────────────────────────────────────────────────────
PREDICTION LAYER  (POST /bil/rank)
─────────────────────────────────────────────────────────────
  Input:  list of items (search results, files, tabs, bookmarks)
  Output: same list re-ranked by predicted personal relevance
  
  final_score = 0.6 × original_score + 0.4 × bil_prediction
       │
       ▼
─────────────────────────────────────────────────────────────
LLM UNDERSTANDING LAYER  (Ollama — coming next)
─────────────────────────────────────────────────────────────
  • "What topics am I most interested in this week?"
  • "Re-rank my open tabs by predicted focus session priority"
  • "What should I read next based on my recent activity?"
  • Reads BIL digest → generates natural language preference summary
  • Feeds summary back into BIL as high-weight signal
```

---

## Quick Start (Run on NAS / Any Machine)

```bash
# 1. Clone
git clone https://github.com/YellowKidokc/behavioral-intelligence-layer
cd behavioral-intelligence-layer

# 2. Install
pip install -r requirements.txt

# 3. Start BIL server
python -m bil.bil_server
# → BIL listening on http://0.0.0.0:8420
# → POST /bil/web   (browser behavioral signals)
# → POST /bil/rank  (re-rank SearXNG results)
```

---

## SearXNG Integration

BIL re-ranks your SearXNG results based on what you actually engage with. Your Cloudflare Worker (or a lightweight Python proxy) sits between your browser and SearXNG:

```
Browser → search.dlowehomelab.com → [proxy worker] → SearXNG → BIL /bil/rank → re-ranked results → Browser
```

Call the rank endpoint:
```bash
curl -X POST http://yellowkidnas:8420/bil/rank \
  -H "Content-Type: application/json" \
  -d '{"results": [ {"url": "...", "title": "...", "content": "...", "engine": "google", "score": 3.2} ]}'
```

Returns the same list with `bil_score` and `final_score` added, sorted best-first.

---

## Configuration

All default endpoints live in two small files — **edit them once for your
network** or override per-invocation with the CLI flags below.

| Where | What |
|---|---|
| `bil/config.py` | Python-side defaults. Reads `BIL_HOST`, `OLLAMA_HOST`, and `OLLAMA_MODEL` from the environment first, then falls back to the constants in the file. |
| `browser/config.js` | Endpoint list the extension's service worker tries in order (first 2xx wins). |

The reference deployment assumes a Synology NAS at `192.168.1.177` running
BIL on `:8420` and Ollama on `:11434`. Change those constants to match your LAN.

CLI overrides (always win over the config file):

- `python -m bil.ingest --host http://my-nas:8420 --path ...`
- `python -m bil.llm_query --bil http://my-nas:8420 --ollama http://my-nas:11434 --model mistral "..."`

---

## Browser Extension

A Manifest V3 extension lives in `browser/`. It works in Chrome and Edge and
passively tracks **time on page, scroll depth, copy events, word count, and
bookmarks**, flushing one signal per tab to the BIL server on close.

**Install (unpacked):**

1. Open `chrome://extensions` (or `edge://extensions`) and enable Developer mode.
2. Edit `browser/config.js` so `BIL_ENDPOINTS` points at your NAS (the default
   is `http://192.168.1.177:8420/bil/web` with a `localhost` fallback).
3. Click **Load unpacked** and select the `browser/` folder from this repo.

Nothing leaves your network — every request targets an IP you control.

---

## Folder Ingestion

Drop any folder in and BIL ingests it in a single pass:

```bash
# On the NAS
python -m bil.ingest --path "/volume1/Research/Physics"
python -m bil.ingest --path "/volume1/Trading/Options"

# From a workstation, pointing at a different host
python -m bil.ingest --path "O:/_Theophysics_v3" --host http://192.168.1.177:8420

# Preview what would be sent without hitting the server
python -m bil.ingest --path ./notes --dry-run
```

For each file it extracts filename, extension, size, modified-days-ago, parent
folder, a content snippet (text / `.md` / `.py` / `.pdf` / `.docx`) and YAKE
keywords, then POSTs a `file_ingest` signal to `/bil/web`. Binary blobs over
50 MB and junk like `.DS_Store`, `Thumbs.db`, `__pycache__`, `.git` are skipped
automatically.

---

## LLM Query

Talk to a local Ollama model with your BIL digest loaded as context:

```bash
# Pull a model (once)
ollama pull llama3

# Ask a question — the latest digest is injected as system context
python -m bil.llm_query "What should I focus on today based on my recent activity?"

# Different model, different host
python -m bil.llm_query "Summarize my week" --model mistral --ollama http://192.168.1.177:11434

# After the reply prints, prompt to POST it back as a high-confidence signal
python -m bil.llm_query "What topic owns my attention?" --feed-back
```

The command prefers the newest file in `exports/bil_digest_*.json`; if none
exists it falls back to `GET /bil/export` on the BIL server. With
`--feed-back`, the reply is re-submitted to `/bil/web` as an `llm_reflection`
signal (`engagement_score=0.9`), closing the loop — the model's understanding
of you becomes another training signal.

---

## Network Drive Deployment (NAS-First Design)

BIL is designed to live on your Synology and serve all your devices:

```
/volume1/BIL/
  ├── bil_events.jsonl      ← all behavioral signals
  ├── exports/
  │   └── bil_digest_2026-04-17.json
  └── models/               ← serialized River models (coming)
```

Set BIL to start automatically in Synology Task Scheduler:
```bash
/usr/local/bin/python3 -m bil.bil_server --port 8420
```

Then point your browser extension at `http://192.168.1.177:8420` and every device on your network feeds the same brain.

---

## Philosophy

Google learns your preferences to sell ads. BIL learns your preferences to serve *you*.

- **No cloud.** Runs on your hardware.
- **No labels.** Learns from implicit behavior — you never rate anything.
- **No retraining.** River updates in real time, one observation at a time.
- **No lock-in.** JSONL event log, open format, you own everything.
- **Composable.** Drop in any folder, any signal, any LLM. It all flows into the same preference core.

---

## Related

- [FIS — File Intelligence System](https://github.com/YellowKidokc/file-intelligence-system) — NLP-powered file classification that uses BIL for learning
- SearXNG running at `search.dlowehomelab.com` (private instance)
- Cloudflare Tunnel → Synology-Nas tunnel for secure remote access
