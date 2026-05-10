# BIL Next Building Machine Steps

## Current Decision

Pause the personal dashboard after a minimal deployable shell. Return focus to BIL / the preference engine, because that is the portable "building machine" David can take across browsers, AIs, dashboards, and computers.

All AI workers should start with:

- `D:\BIL\UNIVERSAL_AI_WORKFLOW_PREAMBLE.md`
- `D:\BIL\AI_COMMS_WORKFLOW_HANDOFF_2026-05-10.md`

## Dashboard Stop Line

Good enough for now means:

- `preference_engine_dashboard.html` exists as the visual shell.
- Cloudflare can serve the shell.
- Cloudflare Tunnel can reach the mini PC.
- The shell can read compact BIL context.
- An AI can ask BIL for summarized context.
- Model routing and cost status are visible.

Do not keep adding dashboard pages before BIL gets smarter.

## BIL Work That Matters Next

1. Capture better signals.
   - Clipboard copy, paste, repeat, and discard.
   - Browser search result position, click, skip, bounce, and revisit.
   - File save location and naming patterns.
   - AI conversation snippets and unfinished loops.

2. Classify intake.
   - Research vs lookup vs task vs writing vs shopping.
   - Useful vs ignored vs bounced.
   - Private/raw vs safe summary.
   - Needs action vs archive.

3. Learn reusable preferences.
   - Preferred domains.
   - Preferred folders and filenames.
   - Dictation corrections.
   - Response style preferences across Codex, Claude, OpenAI, Gemini.
   - Morning/evening working rhythm.

4. Expose compact context.
   - `/bil/context`
   - `/bil/summary`
   - `/bil/intake/today`
   - `/bil/open-loops`
   - `/bil/model-route`
   - `/bil/comms/search`

5. Add AI manager loop.
   - Manual button first: "Run Morning Briefing".
   - BIL compresses raw data first.
   - Local model handles cheap classification.
   - OpenAI/Anthropic only handle higher-value synthesis.
   - All proactive messages/actions require approval.

6. Add Theophysics comms vector memory.
   - Ingest session handoffs first.
   - Store raw handoff metadata in D1.
   - Store embeddings in Cloudflare Vectorize.
   - Retrieve related handoffs when a new AI session starts.
   - Use full conversations later, only after handoffs are working.

## Model Cost Policy

Use local compute for anything it can do well enough:

- classification
- clustering
- tagging
- duplicate detection
- low-risk summaries
- preference scoring

Use paid models only for:

- high-value synthesis
- complex reasoning
- long-form writing
- agent coordination
- important truth/fruits analysis

Never put API keys in frontend HTML. Keys live on the mini PC or in Cloudflare secrets.

## Vector Memory Policy

Vectorize the compressed handoffs before full conversations.

Reason:

- Handoffs are already curated memory.
- They are cheaper.
- They create less retrieval noise.
- They are safer than raw chat logs.
- They map naturally to the Theophysics AI Communications Hub.

Cloudflare D1 should hold the comms ledger and metadata. Cloudflare Vectorize should hold semantic embeddings. BIL should be the layer that decides what gets embedded, what gets retrieved, and what gets shown to an AI.

Use rolling memory:

- 30 days hot by default.
- 60 days optional if it stays useful and cheap.
- Daily rollover snapshot to Synology NAS.
- NAS keeps long-term raw/full archives.
- Hot AI context gets summaries and handoffs, not the whole archive.
- Older memory can be rehydrated only when a future task needs it.

## Files

- Dashboard visual shell: `D:\BIL\preference_engine_dashboard.html`
- Universal workflow preamble: `D:\BIL\UNIVERSAL_AI_WORKFLOW_PREAMBLE.md`
- Cloudflare/tunnel plan: `D:\BIL\CLOUDFLARE_TUNNEL_DASHBOARD_PLAN.md`
- Preference architecture: `D:\BIL\PREFERENCE_ENGINE_REPO_SPEC.md`
- Personal dashboard architecture: `D:\BIL\PERSONAL_DASHBOARD_ARCHITECTURE.md`
- Comms/vector memory plan: `D:\BIL\THEOPHYSICS_COMMS_VECTOR_MEMORY_PLAN.md`
