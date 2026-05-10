# Preference Engine Repo Spec

This is the practical architecture for turning BIL from a collection of capture tools into a portable preference-engine machine.

## One-Sentence Product

A local-first preference engine that learns from behavior, compresses signals into portable preference state, and lets browsers, AI tools, search engines, clipboard tools, and file organizers ask: "what would David probably prefer here?"

## Three Layers

### 1. Capture Layer

Input adapters. They observe behavior and submit events. They do not own the preference model.

Current pieces:

- Browser plugin: `D:\BIL\browser` and `X:\chrome-plugin`
- Screenshot/rating daemon: `D:\BIL\bil_service.py`
- Hotkey/capture UI: future improved GUI
- SearXNG result observer: browser content script
- Clipboard observer: browser plugin now sends copied browser text

Responsibilities:

- Capture small events.
- Include source metadata: app, URL, title, query, result position, selected text, note, timestamp.
- Stay non-destructive. If the engine is down, the browser/page still works normally.
- Respect privacy controls.

### 2. Preference Engine Core

The product. This should eventually become its own importable package/service.

Current pieces:

- `D:\BIL\behavioral-intelligence-layer-OBS-Plugin-Final-Claude\bil\bil_api.py`
- `D:\BIL\behavioral-intelligence-layer-OBS-Plugin-Final-Claude\bil\bil_models.py`
- `D:\BIL\behavioral-intelligence-layer-OBS-Plugin-Final-Claude\bil\bil_features.py`
- `D:\BIL\behavioral-intelligence-layer-OBS-Plugin-Final-Claude\bil\bil_server.py`

Current capabilities:

- Learns web and clipboard behavior.
- Persists model state to `exports\bil_models.pkl`.
- Replays historical JSONL events into the model on startup.
- Scores candidates through `/bil/decide`.
- Ranks SearXNG result lists through `/bil/rank`.
- Summarizes state through `/bil/summary`.

Target capabilities:

- Convert raw events into fixed-size features/embeddings.
- Cluster repeated preferences into compact centroids.
- Keep raw logs as audit/archive, not as the live memory.
- Maintain small, queryable live state:
  - domain preferences
  - search-intent preferences
  - clipboard/reuse preferences
  - file-organization preferences
  - AI-response preferences
- Provide clear decisions:
  - prioritize
  - consider
  - neutral
  - deprioritize

### 3. Application Layer

Consumers. They ask the preference engine what to do.

Current pieces:

- SearXNG re-ranking in the browser plugin
- Dashboard: `D:\BIL\PREFERENCE_MACHINE_DASHBOARD.html`
- Manual candidate scoring via `/bil/decide`

Near-term consumers:

- Clipboard panel: "show likely useful clips"
- SearXNG: "rank these results for David"
- Browser plugin: "is this a known destination, research mode, or fact lookup?"
- File sorter: "where would David put this?"
- AI adapter: "shape this response to David's preferences"

## Memory Mechanism

Raw event:

```text
screenshot/page/clipboard/search result -> text description/metadata -> features or embedding -> signal -> model update
```

Live memory should not be a giant pile of screenshots. The live memory should be compact:

- model weights
- preference clusters
- centroids
- domain/query summaries
- clipboard snippet patterns

Raw files/logs are audit trail and training history. They can be archived or compressed once their signal is baked into the live model.

## Immediate Refactor Boundary

Do not rebuild everything today. Split conceptually first.

Keep in this repo for now:

- Browser plugin
- BIL server
- Dashboard
- Screenshot service

But treat the future package as:

```text
preference_engine/
  core/
    model_store.py
    event_schema.py
    feature_extractors.py
    decision.py
    clustering.py
  adapters/
    browser.py
    clipboard.py
    screenshot.py
    search.py
  server/
    api.py
  ui/
    dashboard.html
```

## Minimal Event Schema

Every adapter should eventually submit events shaped like:

```json
{
  "ts": "2026-05-10T09:40:00",
  "source": "browser|clipboard|screenshot|file|ai",
  "event_type": "view|copy|paste|search_click|rating|save|open|close",
  "context": {
    "app": "Edge",
    "url": "https://mail.google.com/",
    "title": "Gmail",
    "query": "gmail",
    "position": 7
  },
  "content": {
    "text": "short text preview or description",
    "path": "optional file path"
  },
  "signal": {
    "explicit": null,
    "implicit": 0.5,
    "reason": "clicked result 7 and stayed 180s"
  },
  "privacy": {
    "level": "normal|private|never_store_raw"
  }
}
```

## Current Truth

The system is no longer empty:

- Historical event log has roughly 196 events.
- Startup replay trains the live model from history.
- Current model state is persisted.
- Search click position and skipped results are now captured.
- Clipboard browser-copy events now reach the clipboard model.

The next highest-leverage build is clipboard reuse:

```text
copy -> paste/reuse/save -> predict likely useful snippets -> surface before search
```

## Rule

The preference engine must always be inspectable and correctable. If the user cannot see and edit what it learned, it will feel like surveillance instead of agency.
