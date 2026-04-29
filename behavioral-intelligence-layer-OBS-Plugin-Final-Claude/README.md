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
| Browser extension (Chrome/Edge) | ✅ Working |
| JSONL event log (no Postgres required) | ✅ Working |
| Keyword extraction via YAKE | ✅ Working |

## What's Coming (The Pipeline)

| Capability | Priority |
|---|---|
| **Folder ingestion pipeline** — drop any folder in, BIL learns it | 🔜 Next |
| **Ollama LLM front-end** — natural language preference queries | 🔜 Next |
| **Tab order ranking** — BIL scores open tabs by predicted interest | 🔜 Next |
| **Preference export** — daily JSON digest for AI session context | 🔜 Next |
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

## Browser Extension

Install from `browser/` — works in Chrome and Edge.

Passively tracks:
- Time on page
- Scroll depth (did you read it?)  
- Copy events (did you use the content?)
- Bookmarks (strong positive signal)

Sends a single POST to `http://localhost:8420/bil/web` when you close a tab. **Nothing leaves your network.**

---

## Folder Pipeline (Coming Next)

Drop any folder in — BIL ingests it:

```bash
python -m bil.ingest --path "/volume1/Research/Physics"
python -m bil.ingest --path "/volume1/Trading/Options"
python -m bil.ingest --path "O:\_Theophysics_v3"
```

BIL reads filenames, metadata, and content snippets, extracts keywords, and updates its domain/subject preference models. After ingestion, BIL knows what *kinds* of things matter to you — and can apply that to search ranking, tab sorting, and content scoring.

---

## Ollama LLM Layer (Coming Next)

Run any model locally via Ollama (`llama3`, `mistral`, `phi3`):

```bash
# Pull a model
ollama pull llama3

# BIL feeds it context
python -m bil.llm_query "What should I focus on today based on my recent activity?"
```

The LLM reads BIL's daily digest and your preference models, generates a natural language understanding of your current focus, and that understanding feeds back into BIL as a high-confidence preference signal. **You get AI that knows you, running entirely on your hardware.**

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
