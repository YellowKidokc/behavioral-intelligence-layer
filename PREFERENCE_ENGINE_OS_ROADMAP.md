# Preference Engine OS Roadmap

This note preserves the larger browser/preference-engine vision while keeping the build practical.

## Core Thesis

The preference engine should become a portable intention layer: not just memory about a person, but a learned interface for how that person searches, saves, reads, works, organizes, and decides.

The goal is not surveillance. The goal is control: the user can see what is learned, correct it, delete it, export it, and carry it to any browser, AI model, computer, or workflow.

## Build Now

These are practical enough to wire into the current BIL browser plugin and local engine.

- Search result learning:
  - Track query text.
  - Track which result position was clicked.
  - Treat skipped results above the clicked result as weak negative examples.
  - Treat long dwell time, copy, bookmark, and no quick back-out as positive examples.
  - Learn repeated query fixes, such as adding `site:` filters or excluding result types.

- SearXNG ranking:
  - Re-rank visible results after page load.
  - Add a small BIL badge so the user can see the preference layer is active.
  - Keep failure harmless: if BIL is down, normal SearXNG still loads.

- Clipboard preference:
  - Track copied text from browser pages.
  - Learn copied versus pasted/reused/saved snippets.
  - Build a local clipboard prediction endpoint.
  - Promote useful recurring snippets and deprioritize one-off junk.

- Decision endpoints:
  - `/bil/decide` for one candidate URL/title/snippet.
  - `/bil/rank` for search result lists.
  - Decision bands: prioritize, consider, neutral, deprioritize.

- Persistence:
  - Save learned models between runs.
  - Save event logs and model summaries.
  - Avoid starting from zero every reboot.

## Soon

These extend the same mechanism once the first loop is reliable.

- Search intent modes:
  - Fact lookup: wants one answer quickly.
  - Research mode: wants several sources and breadth.
  - Known destination: wants the actual site, such as Gmail, not app stores or SEO pages.

- Personal navigation:
  - Time-of-day autocomplete.
  - Repeated site chains, such as Gmail -> Drive -> NAS -> Cloudflare.
  - Per-domain zoom/reader-mode preferences.

- Reading memory:
  - Detect already-read articles.
  - Remember scroll position and reading queue.
  - Auto-save articles opened then abandoned for later.

- Annoyance profile:
  - Dismiss repeated popups/cookie/newsletter modals.
  - Quiet notification rules based on actual dismissal/click behavior.

- File/download routing:
  - Sort downloads by file type, source, and prior behavior.
  - Detect duplicates.
  - Open files immediately only when history suggests the user usually does.

## Bigger OS Layer

This is the larger portable preference system.

- App-agnostic preference profile:
  - Browser, clipboard, files, windows, AI prompts, search, model choice, writing tone.
  - Portable export/import.
  - Local-first by default.

- AI interface adapter:
  - Make Gemini, Claude, Codex, or local models feel more consistent by applying the user's learned preferences.
  - Shape prompt depth, formatting, directness, risk tolerance, and source preferences.

- Workspace layout:
  - Restore window positions, tab clusters, and work modes.
  - Project-aware default app layout.

- Personal ranking everywhere:
  - Search results.
  - Clipboard snippets.
  - Files.
  - Notes.
  - AI-generated options.
  - YouTube/videos/articles.

## Control Rules

The preference engine must feel like a superpower, not surveillance.

- Show what was learned.
- Let the user correct it.
- Let the user delete it.
- Let the user pause collection per site/app.
- Keep private domains private.
- Never break the normal page if BIL is offline.

## Current Implementation Notes

- Canonical plugin copy: `X:\chrome-plugin`
- Original BIL repo: `D:\BIL`
- BIL service: `http://localhost:8420`
- Search ranking endpoint: `POST /bil/rank`
- Candidate scoring endpoint: `GET/POST /bil/decide`
- Browser learning endpoint: `POST /bil/web`
- Clipboard learning endpoint: `POST /bil/clipboard`

Current practical loop:

```text
Search query -> visible results -> click position -> skipped result negatives
-> clicked page dwell/copy/bookmark -> persistent BIL model
-> future SearXNG re-ranking
```

Next practical loop:

```text
Copy text -> observe paste/reuse/save behavior -> predict useful snippets
-> surface likely clips before the user searches for them
```
