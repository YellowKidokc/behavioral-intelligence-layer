# Cloudflare Tunnel Personal Dashboard Plan

## Core Decision

Do not adopt the `ahk-dashboard` UI as the product. Use it only as a reference shelf for ideas like Emma, voice commands, OAuth notes, and dashboard plumbing.

The real product is David's personal dashboard:

- Cloudflare Pages/Worker is the public face.
- A mini PC behind Cloudflare Tunnel is the private worker arm.
- BIL / the preference engine is the memory and decision layer.
- Browser plugin, clipboard watcher, speech/TTS, Obsidian, and file watchers are capture sources.
- Existing local/NAS pages such as search, clipboard, prompt tools, and dashboards are first-class dashboard modules, not separate side apps.

## Why This Unlocks The System

Cloudflare Pages alone cannot safely read local files, clipboard history, desktop windows, private NAS services, local models, or TTS engines. A local machine can.

The tunnel gives Cloudflare a controlled path back to the local machine without exposing the home network directly. The dashboard can ask the mini PC for private context, and the mini PC can decide what is safe to return.

## Roles

### Cloudflare Dashboard

The dashboard should be fast, visual, and always reachable.

Responsibilities:

- Show daily intake: clipboard, searches, pages, files, speech, notes, AI conversations.
- Show preference summaries and pattern discoveries.
- Let David ask personal questions over his own working context.
- Display open loops and proactive suggestions.
- Provide controls for privacy, pausing capture, and approving actions.
- Embed or link to existing internal tools through stable Cloudflare routes.
- Treat `search.dlohomelab.com`-style front ends as dashboard modules.

### Mini PC Worker

The mini PC should do the private/local work.

Responsibilities:

- Run BIL and preference-engine services.
- Watch clipboard and selected folders.
- Connect to Obsidian vaults, NAS folders, browser data exports, and local logs.
- Run lightweight local models when possible.
- Handle TTS/STT services when browser speech is not enough.
- Expose a small API through Cloudflare Tunnel.
- Reverse-proxy selected local pages and NAS services into Cloudflare-safe dashboard routes.

### Preference Engine

The preference engine should be the shared brain, not just a dashboard feature.

Responsibilities:

- Store events from clipboard, browser, search, speech, files, and AI sessions.
- Learn preference clusters from repeated behavior.
- Score current context with `prioritize`, `consider`, `neutral`, or `deprioritize`.
- Maintain working memory and open loops.
- Provide compact context to any AI or dashboard that asks.

## First API Shape

The Cloudflare dashboard should start by calling a small set of tunnel endpoints:

- `GET /health` - Is the mini PC worker alive?
- `GET /context` - Current working memory, open loops, and mode guess.
- `GET /intake/today` - Today's captured information.
- `GET /preferences/summary` - Learned preference patterns.
- `POST /capture` - Send a new event into the engine.
- `POST /ask` - Ask the personal dashboard a question using local context.
- `POST /action/propose` - Queue a suggested action for approval.
- `GET /notifications/poll` - Let workers check for live workflow notifications.
- `POST /notifications/ack` - Worker acknowledges, defers, or completes a notification.

Current local BIL endpoints already cover part of this:

- `GET /bil/status`
- `GET /bil/summary`
- `GET /bil/context`
- `POST /bil/web`
- `POST /bil/clipboard`
- `POST /bil/decide`

## Frontend Page Access Pattern

The dashboard needs access to the local pages David has already built. Do this by giving every important internal tool a stable Cloudflare route while keeping the service itself local.

Example route pattern:

- `https://dashboard.dlohomelab.com/` - main personal dashboard
- `https://search.dlohomelab.com/` - NAS/SearXNG search front end
- `https://dashboard.dlohomelab.com/modules/clipboard` - clipboard UI
- `https://dashboard.dlohomelab.com/modules/prompts` - prompt picker
- `https://dashboard.dlohomelab.com/modules/research` - research links
- `https://dashboard.dlohomelab.com/modules/preferences` - BIL preference dashboard
- `https://dashboard.dlohomelab.com/api/context` - preference/context API
- `https://dashboard.dlohomelab.com/api/intake/today` - daily intake API

The cleanest shape is:

- Cloudflare Pages hosts the main shell.
- Cloudflare Worker handles routing, auth, and API wrappers.
- Cloudflare Tunnel points private routes to the mini PC.
- The mini PC proxies local pages from BIL, AI-HUB, NAS search, and future tools.

This lets the dashboard show local tools in panels or tabs while keeping local services off the open internet.

## MCP / Control Hub Layer

The comms dashboard should become an MCP-style workflow hub, not just a visual page.

Core idea:

- Comms is the operating channel.
- BIL is memory and preference intelligence.
- Dashboard is the human control tower.
- MCP/tools layer lets AI workers access the same hub programmatically.

Future tools/resources:

- `check_comms`
- `post_handoff`
- `get_bil_context`
- `search_handoffs`
- `list_open_loops`
- `get_notifications`
- `ack_notification`
- `run_daily_snapshot`
- `ask_preference_engine`
- `propose_action`

The goal is that Codex, Claude, Gemini, local agents, and future workers can all enter the same hub, read the same workflow state, and coordinate without David manually copy/pasting every update.

## Real-Time Notification Layer

The missing layer is live awareness.

The system should not constantly interrupt workers, but it should let them know when something matters.

Notification levels:

- `info` - no interruption; visible in dashboard/comms.
- `soft` - worker should notice soon, but can finish current thought.
- `checkpoint` - worker should stop at the next safe pause and inspect.
- `urgent` - worker should interrupt and inspect now.

Examples:

- A new comms message arrived for the worker.
- David answered a blocking question.
- Another AI found a contradiction.
- A build/test failed.
- A high-priority open loop was assigned.
- A security/privacy issue was flagged.
- A daily snapshot is ready.

Worker behavior:

- Poll or subscribe for notifications.
- If busy, acknowledge as `defer`.
- If at a safe stopping point, acknowledge as `inspect`.
- If complete, acknowledge as `done`.
- Always include the notification id in the handoff.

Implementation options:

- Simple first version: polling endpoint every 30-60 seconds.
- Better version: Server-Sent Events from the Cloudflare Worker or tunnel worker.
- Later version: WebSocket/session channel for active AI workers.

Do not start with complex orchestration. Start with reliable notification records in D1 and a polling endpoint.

## Security Rules

The tunnel should never expose raw local access broadly.

- Require an access token or Cloudflare Access before returning private context.
- Put Cloudflare Access in front of dashboard and module routes, especially clipboard.
- Keep raw clipboard and raw screenshots local by default.
- Return summaries unless David explicitly asks for raw data.
- Add a pause switch for capture.
- Add a redaction layer for passwords, keys, tokens, and financial data.
- Log every remote action request.
- Require approval before any action that writes files, sends messages, deletes data, or changes settings.

## TTS / Voice Layer

The mini PC can become the speech arm.

Options:

- Browser Web Speech for quick read-aloud.
- Local Kokoro or another NAS/local endpoint for downloadable audio.
- Mini-PC TTS service for dashboard responses.
- Future STT service for voice commands and daily dictation intake.

The voice layer should call the same preference context API before speaking, so it sounds like David's system instead of a generic assistant.

## Practical Build Order

1. Keep BIL running locally and stabilize `/bil/context`.
2. Add auth and a safe public wrapper around the BIL context endpoint.
3. Put the mini PC on Cloudflare Tunnel.
4. Build a clean Cloudflare dashboard shell that reads the tunnel context.
5. Add daily intake views: clipboard, browser/search, files, speech.
6. Add action queue: suggested next actions that require approval.
7. Add TTS response mode.
8. Add truth/fruits scoring as a separate analysis layer over intake items.

## Minimal Dashboard Stopping Point

The dashboard should not become the main project right now. Stop when it can do these things:

- Load on Cloudflare.
- Reach the mini PC through Cloudflare Tunnel.
- Show BIL context, daily intake, and preference summary.
- Let an AI ask for compact context through one approved endpoint.
- Show an action queue / open loops list.
- Show model-cost status and routing mode.

After that, return to BIL and the preference engine.

## AI And Cost Routing

The dashboard needs a model router so cost stays controlled.

Default policy:

- Use a local model first when the job is small, private, repetitive, or classification-heavy.
- Use OpenAI or Anthropic only when the job needs stronger reasoning, long context, writing quality, or agent coordination.
- Store keys only on the mini PC or in Cloudflare secrets, never in frontend HTML.
- Show which model handled each job.
- Log estimated cost per job and per day.
- Let David set a daily soft budget and a hard stop.

Example routing:

- Clipboard classification: local model.
- Search-result preference scoring: local model or BIL classifier.
- Daily intake clustering: local model first, remote model for final synthesis.
- Morning manager briefing: Claude/OpenAI can synthesize, but only after BIL compresses the raw day into summaries.
- Truth/fruits scoring: local first for triage, remote model only for deeper review.
- Proactive agent messages: require approval before sending to Codex, Claude, email, or any outside system.

The important rule: remote AI should receive compressed preference context, not the full raw clipboard/log firehose unless explicitly approved.

## Daily Manager Loop

Each morning, the system should run a manager pass:

- Pull yesterday/today intake from BIL.
- Cluster what happened.
- Identify unfinished loops.
- Identify urgent or high-value next actions.
- Detect where David got pulled onto tangents.
- Prepare a short briefing for the personal dashboard.
- Optionally prepare messages/tasks for Codex, Claude, or other assistants, but queue them for approval.

This should be an automation later, but first it can be a manual "Run Morning Briefing" button.

## What To Reuse From `ahk-dashboard`

Reuse ideas, not the product.

- Emma assistant pattern
- Voice intent notes
- OAuth / Google Drive setup notes
- AI cascade documentation
- Report-generation concepts
- Deployment notes

Avoid carrying over:

- AHK Strategies branding
- Marketing dashboard assumptions
- Old project/task data
- Any hardcoded old paths or keys
- UI shape that does not match David's actual daily workflow

## Next Concrete Step

Create a small tunnel-ready worker service that wraps local BIL:

- `/health`
- `/context`
- `/intake/today`
- `/ask`

Then build the Cloudflare dashboard around that instead of starting from someone else's dashboard.

Do not continue expanding the dashboard beyond this until BIL has better capture, classification, and preference learning.
