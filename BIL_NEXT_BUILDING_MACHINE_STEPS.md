# BIL Next Building Machine Steps

## Current Decision

Pause the personal dashboard after a minimal deployable shell. Return focus to BIL / the preference engine, because that is the portable "building machine" David can take across browsers, AIs, dashboards, and computers.

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

5. Add AI manager loop.
   - Manual button first: "Run Morning Briefing".
   - BIL compresses raw data first.
   - Local model handles cheap classification.
   - OpenAI/Anthropic only handle higher-value synthesis.
   - All proactive messages/actions require approval.

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

## Files

- Dashboard visual shell: `D:\BIL\preference_engine_dashboard.html`
- Cloudflare/tunnel plan: `D:\BIL\CLOUDFLARE_TUNNEL_DASHBOARD_PLAN.md`
- Preference architecture: `D:\BIL\PREFERENCE_ENGINE_REPO_SPEC.md`
- Personal dashboard architecture: `D:\BIL\PERSONAL_DASHBOARD_ARCHITECTURE.md`
