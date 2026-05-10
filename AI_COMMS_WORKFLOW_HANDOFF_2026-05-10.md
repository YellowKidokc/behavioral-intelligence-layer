# AI Comms Workflow Handoff - 2026-05-10

## Message For Other AI Helpers

David wants to pause feature expansion and stabilize the current BIL / preference-engine layer before starting another build chain.

Primary owner for coordination: Codex.

Do not create a new dashboard product. Do not replace BIL. Do not fork the architecture unless David explicitly asks.

Before doing anything else, read the universal workflow preamble:

- `D:\BIL\UNIVERSAL_AI_WORKFLOW_PREAMBLE.md`

## Current Working Architecture

BIL is the building machine.

Cloudflare dashboard is only the visible control surface.

Mini PC through Cloudflare Tunnel is the private worker arm.

Theophysics comms handoffs become the first vector memory source.

Synology NAS becomes long-term cold storage for daily snapshots.

## What Was Completed Today

1. BIL API and context layer
   - BIL is running locally at `http://127.0.0.1:8420`.
   - `/bil/status` works.
   - `/bil/context` works.
   - Current status showed web events and clipboard events active.

2. Clipboard learning
   - Desktop clipboard watcher is active.
   - Clipboard events are being captured as local preference signals.

3. Browser/search preference layer
   - Browser plugin work lives in `X:\chrome-plugin`.
   - Search click/skipped-result learning was implemented earlier.
   - Remaining test: reload extension and live-test SearXNG ranking.

4. Dashboard stopping point
   - Visual shell copied to `D:\BIL\preference_engine_dashboard.html`.
   - The dashboard should not keep expanding until BIL gets smarter.

5. Cloudflare/tunnel architecture
   - Cloudflare is the public face.
   - Mini PC behind Cloudflare Tunnel handles local/private work.
   - Existing local tools should become dashboard modules.

6. Comms vector memory
   - Vectorize session handoffs first, not full conversations.
   - D1 remains the comms ledger.
   - Vectorize stores semantic embeddings.
   - BIL decides what is safe/useful to embed and retrieve.

7. Rolling retention
   - 30-day hot memory.
   - Optional 60-day warm memory.
   - Daily snapshots to Synology NAS for long-term archive.

## Key Files

- `D:\BIL\UNIVERSAL_AI_WORKFLOW_PREAMBLE.md`
- `D:\BIL\BIL_NEXT_BUILDING_MACHINE_STEPS.md`
- `D:\BIL\CLOUDFLARE_TUNNEL_DASHBOARD_PLAN.md`
- `D:\BIL\THEOPHYSICS_COMMS_VECTOR_MEMORY_PLAN.md`
- `D:\BIL\PREFERENCE_ENGINE_REPO_SPEC.md`
- `D:\BIL\PERSONAL_DASHBOARD_ARCHITECTURE.md`
- `D:\BIL\preference_engine_dashboard.html`
- `D:\BIL\AUDIT_OPUS_LEDGER_2026-05-10.md`
- `D:\BIL\AUDIT_OPUS_LEDGER_PROVENANCE_NOTE_2026-05-10.md`
- `X:\chrome-plugin\`

## Git Checkpoint

Recent BIL commits:

- `4a875a5 Add rolling memory retention plan`
- `57e95fa Plan comms handoff vector memory`
- `f03adb7 Define minimal dashboard stopping point`
- `1a76f30 Add personal dashboard context API`
- `ca745da Add desktop clipboard learning`
- `fbd3581 Specify preference engine architecture`
- `b845b34 Add preference machine dashboard`
- `fde7300 Document preference engine OS roadmap`

## Stabilization Tasks

Codex should own sequencing and integration.

Helpful tasks for other AI helpers:

1. Review architecture docs for contradictions.
   - Read the key files above.
   - Identify conflicts, missing assumptions, or dangerous exposure risks.
   - Do not rewrite the architecture unless asked.

2. Design Cloudflare D1 + Vectorize schema.
   - Focus on session handoffs first.
   - Include message metadata, vector ids, privacy level, token counts, open loops, tags.
   - Keep cost low.
   - Do not include API keys or secrets in frontend HTML.

3. Design daily NAS snapshot format.
   - 30-day rolling hot memory.
   - Daily folder layout.
   - Snapshot manifest.
   - Rehydration flow for old memory.

4. Test checklist only.
   - Check BIL endpoint health.
   - Check clipboard watcher.
   - Check Chrome/Edge extension reload path.
   - Check SearXNG ranking learning.
   - Check dashboard can read `/bil/context` later.

## Do Not Do Yet

- Do not keep expanding the dashboard.
- Do not ingest all raw conversations into Vectorize.
- Do not expose raw clipboard publicly.
- Do not put OpenAI, Anthropic, Cloudflare, or comms tokens into HTML.
- Do not replace BIL with the `ahk-dashboard` repo.
- Do not build a second preference engine in another folder without David's approval.

## Suggested Message To Post To Comms

Codex stabilized the BIL/preference-engine direction today. Current decision: BIL is the portable building machine; Cloudflare dashboard is only the control surface; mini PC via Cloudflare Tunnel is the local/private worker arm. Completed docs and checkpoints: `BIL_NEXT_BUILDING_MACHINE_STEPS.md`, `CLOUDFLARE_TUNNEL_DASHBOARD_PLAN.md`, `THEOPHYSICS_COMMS_VECTOR_MEMORY_PLAN.md`, `PREFERENCE_ENGINE_REPO_SPEC.md`, `PERSONAL_DASHBOARD_ARCHITECTURE.md`, and `preference_engine_dashboard.html` in `D:\BIL`. BIL is live at `127.0.0.1:8420`; `/bil/status` and `/bil/context` respond; clipboard watcher is active; browser/search preference plugin is in `X:\chrome-plugin` and still needs extension reload + live SearXNG ranking test. Major architecture decision: vectorize Theophysics comms session handoffs first, not full raw conversations. Use D1 as ledger, Vectorize as semantic lookup, and Synology NAS for daily 30-day rolling snapshot/cold archive. Next helpers should stabilize and review, not expand: check endpoint health, review D1/Vectorize schema, design NAS snapshot manifest, and flag security/cost risks. Do not expose raw clipboard or put API tokens in frontend HTML.

## Coordination Rule

Other AIs should report findings back through comms or to David. Codex can then integrate the final decisions into BIL.
