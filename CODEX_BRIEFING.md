# Codex Briefing — BIL + Preference Engine + NLP Stack Integration
**POF 2828 | May 3, 2026 | Wire everything together**

---

## Overview

Multiple systems exist that need to be wired into one pipeline. Nothing needs to be rebuilt from scratch. The job is: get each piece running, connect them to Postgres, and make the data flow end to end.

The end state: David hits a hotkey anywhere on his computer → screenshot + context captured → rated via overlay GUI → stored in Postgres → embedded by SBERT → classified by DeBERTa → clustered by HDBSCAN → preference engine learns patterns → feeds back into content prioritization.

---

## System Map

### 1. AI-HUB (Daily Driver)
- **Location:** `D:\GitHub\Physics_of_faith\ai-hub\`
- **Startup:** `C:\Users\lowes\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\AI-HUB-v2\AI-HUB.ahk`
- **What it does:** Launches ClipSync bridge, BetterTTS, HTML panels (clipboard, prompts, research links), sync server
- **Status:** Running daily. This is the shell everything else plugs into.

### 2. BIL (Behavioral Intelligence Layer)
- **Location:** `D:\BIL\`
- **Start script:** `D:\BIL\START_BIL.bat`
- **Service:** `bil_service.py` serves on localhost:8420
- **Config:** `D:\BIL\bil_config.json`
- **What it does:** Preference capture, threshold engine, adaptive confidence, browser extension, capture/rating pipeline
- **Status:** Built but not integrated into AI-HUB startup. Needs to be verified running.

### 3. PIL Capture (Preference Input UI)
- **HTML:** Multiple locations, canonical is `C:\Users\lowes\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\AI-HUB-v2\modules\pil-capture.html`
- **AHK:** `pil_capture.ahk` in same folder — Ctrl+Shift+S takes screenshot, gets Moondream description, pops overlay
- **What it does:** Thumbs up/down + dataset selector + note field. Posts to BIL at localhost:8420
- **Status:** HTML works. AHK hotkey works. May conflict with ShareX hotkey. Needs verification.

### 4. NLP Stack (D:\brain\)
- **Location:** `D:\brain\`
- **Modules:**
  - `01_WHISPER` — speech-to-text (local Whisper model)
  - `02_SBERT` — sentence embeddings (local SBERT model)
  - `03_DEBERTA` — zero-shot classification (local DeBERTa model)
  - `04_HDBSCAN` — clustering (pure math, no model)
  - `05_YOUTUBE` — YouTube API scraper + transcript puller
  - `06_IMAGES` — image classification
  - `07_POSTGRES` — database utilities
  - `08_CLAIMS` — claims extraction
- **Postgres:** 192.168.1.177:2665, database `crawlab_data`, user `root`
- **Credentials:** `D:\brain\.env` (BRAIN_PG_PASSWORD and BRAIN_YOUTUBE_API_KEY)
- **Status:** YouTube scraper working (3,913 videos loaded). Transcript puller working (27 transcripts pulled, getting IP-limited on bulk). SBERT/DeBERTa/HDBSCAN need testing against live data.

### 5. YouTube Transcript Pipeline
- **Scraper:** `D:\brain\05_YOUTUBE\youtube_scraper.py` — WORKING, 3,913 videos in Postgres
- **Transcript puller:** `D:\brain\05_YOUTUBE\transcript_puller.py` — WORKING but needs rate limiting (add 2-3 second sleep between requests to avoid IP blocks)
- **Table:** `youtube_apologetics` in `crawlab_data`
- **Columns added:** transcript, transcript_source, transcript_language, transcript_char_count, transcript_pulled_at
- **Current state:** 27 transcripts pulled, 3,886 remaining. Average transcript ~23,600 chars.

### 6. ClipSync
- **Location:** `D:\ClipSync\`
- **What it does:** Clipboard sync between machines
- **Status:** Needs build verification.

### 7. Math Translation Layer (SEPARATE — already briefed)
- **Location:** `D:\GitHub\Math-Translation-Layer\`
- **Status:** Codex already refactored to standalone engine. CLI working. Browser overlay working. 10/10 tests passing.

---

## Task List (Priority Order)

### Phase 1: Get Everything Running

**Task 1.1: Verify BIL service**
```
cd D:\BIL
python bil_service.py
```
Confirm localhost:8420 responds. Fix any import errors or missing dependencies.

**Task 1.2: Test PIL capture end-to-end**
- Verify Ctrl+Shift+S takes screenshot
- Verify Moondream description runs (or falls back to "Screenshot captured")
- Verify overlay pops up
- Verify rating posts to localhost:8420
- Verify rating appears in `D:\BIL\data\ratings\ratings.jsonl`

**Task 1.3: Test NLP stack modules**
Run each module's TEST.bat:
```
cd D:\brain\02_SBERT && TEST.bat
cd D:\brain\03_DEBERTA && TEST.bat
cd D:\brain\04_HDBSCAN && TEST.bat
```

**Task 1.4: Fix transcript puller rate limiting**
Add a 2-3 second `time.sleep()` between requests in `transcript_puller.py` to avoid IP blocks. Add a `--delay` flag with default 2.

### Phase 2: Wire to Postgres

**Task 2.1: BIL ratings → Postgres**
Currently BIL writes ratings to JSONL files at `D:\BIL\data\ratings\ratings.jsonl`. Add a Postgres write alongside the JSONL write. Create a `preference_ratings` table:
```sql
CREATE TABLE IF NOT EXISTS preference_ratings (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ,
    signal INT,  -- +1 or -1
    dataset VARCHAR(50),
    note TEXT,
    description TEXT,
    file_path TEXT,
    window_title TEXT,
    url TEXT,
    sbert_embedding BYTEA,
    deberta_label TEXT,
    deberta_confidence FLOAT,
    cluster_id INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
Use the same `db_utils.py` from `D:\brain\07_POSTGRES\`.

**Task 2.2: SBERT embeddings on ratings**
When a new rating comes in with a description or note, run SBERT to generate an embedding and store it in the `sbert_embedding` column. This can be async/batched — doesn't need to be real-time.

**Task 2.3: DeBERTa classification on ratings**
Classify each rating's description against the apologetics labels from `D:\brain\03_DEBERTA\config.json`. Store label and confidence.

### Phase 3: Preference Engine

**Task 3.1: Clustering**
Run HDBSCAN on accumulated SBERT embeddings to find preference clusters. What topics does David consistently thumbs-up? What does he thumbs-down?

**Task 3.2: Preference scoring**
Build a simple scoring function: for new content, embed it with SBERT, find nearest cluster, check David's historical signal for that cluster. Output: predicted preference score.

**Task 3.3: Integration with YouTube pipeline**
Use the preference engine to prioritize which YouTube transcripts to process first — transcripts from videos whose titles/descriptions cluster near David's thumbs-up patterns get processed before others.

### Phase 4: Integration & Packaging

**Task 4.1: Add BIL to AI-HUB startup**
Modify `D:\GitHub\Physics_of_faith\ai-hub\AI-HUB.ahk` to also launch BIL service on startup. Same pattern as ClipSync bridge — launch silent, background process.

**Task 4.2: ShareX integration**
If ShareX is the active screenshot tool, wire ShareX's output folder to BIL's capture directory. ShareX can run a custom action on capture — have it trigger the PIL overlay.

**Task 4.3: Docker compose for NLP stack**
Write a `docker-compose.yml` for `D:\brain\` that runs:
- Postgres (or connects to existing at 192.168.1.177:2665)
- BIL service
- SBERT as a service
- DeBERTa as a service
- A scheduler that runs transcript pulling, embedding, classification on a cron

**Task 4.4: ClipSync build verification**
```
cd D:\ClipSync
npm install
npm run build
```
Get it running and verify clipboard sync works.

### Phase 5: Exe packaging
After everything is running and Docker-ized:
- Package BIL service as exe (PyInstaller)
- Package NLP runners as individual exes
- Package CLI tools as exes

---

## Credential Locations
- Postgres: `D:\brain\.env` → BRAIN_PG_PASSWORD
- YouTube API: `D:\brain\.env` → BRAIN_YOUTUBE_API_KEY
- BIL config: `D:\BIL\bil_config.json`
- Postgres config: `D:\brain\07_POSTGRES\config.json`

## Network
- Postgres: 192.168.1.177:2665
- BIL service: localhost:8420
- ClipSync bridge: localhost:3456
- Ollama (if running): localhost:11434

---

## The X Drive

Codex should also explore the X: drive and inventory what's there. It may contain additional projects, data, or tools that should be cataloged and potentially integrated.

---

## What Success Looks Like

David hits Ctrl+Shift+S anywhere on his computer. A screenshot is captured. An overlay appears in the bottom corner. He taps thumbs up, selects "theophysics" as the dataset, types a quick note, hits Enter. The rating flows to Postgres. SBERT embeds the description. DeBERTa classifies it. Over time, the system learns what David cares about and can prioritize content accordingly.

All of this runs locally. No LLM API calls. No cloud dependencies except Postgres on the NAS. The preference engine is David's taste encoded as math.

---

*The pieces are built. Wire them. Test them. Ship them.*
