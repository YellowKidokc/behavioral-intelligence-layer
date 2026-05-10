# BIL / Preference Engine — Architecture Audit

**Auditor:** opus-ledger (Claude Opus 4.7, Claude Code)
**Date:** 2026-05-10
**Scope:** stabilization-pass review of architecture docs in `D:\BIL\`. No code changes. No architecture rewrite.
**Sources read:** `UNIVERSAL_AI_WORKFLOW_PREAMBLE.md`, `AI_COMMS_WORKFLOW_HANDOFF_2026-05-10.md`, `BIL_NEXT_BUILDING_MACHINE_STEPS.md`, `CLOUDFLARE_TUNNEL_DASHBOARD_PLAN.md`, `THEOPHYSICS_COMMS_VECTOR_MEMORY_PLAN.md`, `PREFERENCE_ENGINE_REPO_SPEC.md`, `PERSONAL_DASHBOARD_ARCHITECTURE.md`, `preference_engine_dashboard.html`. Glob also surfaced `bil-dashboard.html`, `PREFERENCE_MACHINE_DASHBOARD.html`.

Findings are sorted by severity. Each finding includes evidence and a recommended next step. Recommendations are advisory; Codex owns the integration call.

---

## A. LOAD-BEARING — fix before any Cloudflare-served deploy

### A1. Static demo HTML contains private/internal data and is named the "stopping point" dashboard
File: `preference_engine_dashboard.html` (1,311 lines, all hardcoded mock data).
- Contains `192.168.1.177:2665` (LAN IP + port for PostgreSQL) — internal network signal.
- Contains local file paths: `O:\_Theophysics_v4\00_Canonical\`, `Law9_canonical.md`, `D:\BIL\`.
- Contains the Master Equation glyph and references to `faiththruphysics.com`.
- Has a "STREAMING / LIVE / LEARNING" badge and a "uptime 14d 6h 32m" indicator while showing zero live data.
- Workflow handoff (line 41) names this file as the dashboard stopping point.
- Risk: served via Cloudflare Pages as-is, this leaks LAN topology and internal layout, and gives a false impression of a working system to future workers and to anyone with access.
- Recommended next step: before deploy, replace mock content with empty panels that fetch from `/bil/context`, OR add a banner clearly labeling the page as "demo / not wired to BIL yet."

### A2. NAS hostname inconsistency — snapshot path will be broken on day one
- `THEOPHYSICS_COMMS_VECTOR_MEMORY_PLAN.md` (line 290): `\\SynologyNAS\AI-Memory\BIL\Snapshots\YYYY\MM\YYYY-MM-DD\`.
- Pinned standing order on comms hub (and `reference_brain_handoff.md` in memory): NAS host is `dlowenas`, with shares like `\\dlowenas\brain\`, `\\dlowenas\github\`, etc. There is no `\\SynologyNAS\` share or `AI-Memory` share documented.
- Risk: the daily-rollover script will fail silently (or worse, succeed against a non-canonical path that nobody backs up).
- Recommended next step: pick one — `\\dlowenas\brain\snapshots\YYYY\MM\YYYY-MM-DD\` is consistent with existing NAS layout. Update `THEOPHYSICS_COMMS_VECTOR_MEMORY_PLAN.md`.

### A3. Cloudflare hostname typo
- `CLOUDFLARE_TUNNEL_DASHBOARD_PLAN.md` lines 92–98 use `dashboard.dlohomelab.com` and `search.dlohomelab.com` ("dloh").
- Comms reference + comms hub endpoint use `dlowehomelab.com` ("dlowe", correct domain David already owns).
- Risk: tunnel routes provisioned against a domain David doesn't control; or worse, a typo-squatter eventually grabs `dlohomelab.com`.
- Recommended next step: global search-and-replace `dlohomelab.com` → `dlowehomelab.com` in all `D:\BIL\` docs. Verify with `grep`.

### A4. Tunnel auth model is asserted but not specified
- `CLOUDFLARE_TUNNEL_DASHBOARD_PLAN.md` "Security Rules" says "Require an access token or Cloudflare Access before returning private context" and "Put Cloudflare Access in front of dashboard and module routes, especially clipboard."
- No doc specifies: which Cloudflare Access policy / identity provider / group, what the bearer-token shape is for AI workers calling the tunnel, what happens to existing local `/bil/*` requests when the tunnel is up.
- Today, `127.0.0.1:8420/bil/context` has no auth (it's loopback). The moment the tunnel exposes that port, the same endpoint becomes internet-reachable.
- Risk: race between tunnel cutover and auth wrapper. Default-open is the failure mode.
- Recommended next step: before tunnel cutover, document the auth shape in a new short doc — `TUNNEL_AUTH_MODEL.md` — covering: (1) Cloudflare Access policy, (2) per-worker bearer scheme if any, (3) which BIL endpoints are public-readable vs. private, (4) fail-closed default.

### A5. Cloudflare API token storage for BIL → Vectorize is unstated
- `THEOPHYSICS_COMMS_VECTOR_MEMORY_PLAN.md` requires BIL to write/query Vectorize and D1.
- `BIL_NEXT_BUILDING_MACHINE_STEPS.md` says "Never put API keys in frontend HTML. Keys live on the mini PC or in Cloudflare secrets."
- No doc says which: mini-PC env file, Windows Credential Manager, secret in a wrangler-managed Worker that BIL proxies through, etc. Token rotation / scope (read-only? per-index?) not specified.
- Risk: a worker implementing comms ingestion will pick something ad-hoc.
- Recommended next step: state the storage location and least-privilege scope for the Cloudflare API token in the comms-memory plan, alongside the D1 ID that's already there.

---

## B. CONTRADICTIONS — need one decision so workers stop drifting

### B1. Three dashboard HTML files, two of them named "the" dashboard
- Glob result: `bil-dashboard.html`, `PREFERENCE_MACHINE_DASHBOARD.html`, `preference_engine_dashboard.html`.
- `PREFERENCE_ENGINE_REPO_SPEC.md` line 74: dashboard is `D:\BIL\PREFERENCE_MACHINE_DASHBOARD.html`.
- `BIL_NEXT_BUILDING_MACHINE_STEPS.md` line 114 + workflow handoff: dashboard stopping point is `preference_engine_dashboard.html`.
- Recommended next step: pick one canonical, archive the other two under `D:\BIL\archive\` (do not delete — they may contain UI ideas worth re-using). Update `PREFERENCE_ENGINE_REPO_SPEC.md` to match.

### B2. API surface drift between local BIL and the tunnel-facing wrapper
Two namespaces appear without a documented mapping:
- Local BIL (current, working): `/bil/status`, `/bil/summary`, `/bil/context`, `/bil/web`, `/bil/clipboard`, `/bil/decide`, `/bil/rank`.
- Tunnel-facing (planned): `/health`, `/context`, `/intake/today`, `/preferences/summary`, `/capture`, `/ask`, `/action/propose`.
- `BIL_NEXT_BUILDING_MACHINE_STEPS.md` adds yet more `/bil/*` endpoints: `/bil/intake/today`, `/bil/open-loops`, `/bil/model-route`, `/bil/comms/search`.
- The tunnel plan implies a wrapper translates the second list into the first, but the mapping isn't written down.
- Risk: workers add endpoints to whichever surface they're touching; integration breaks later.
- Recommended next step: a one-page route table — left column = public tunnel route, right column = local BIL route, plus auth required column. Mark which exist, which are next, which are out of scope.

### B3. Browser plugin lives in two places per the docs
- `PREFERENCE_ENGINE_REPO_SPEC.md` line 18: "Browser plugin: `D:\BIL\browser` and `X:\chrome-plugin`."
- Workflow handoff line 37: "Browser plugin work lives in `X:\chrome-plugin`."
- Cannot tell from docs alone which is canonical for the SearXNG / clipboard tests.
- Recommended next step: confirm canonical path (suspected: `X:\chrome-plugin` per the workflow). Either remove the `D:\BIL\browser` reference or label it as a reference fork.

### B4. Warm-tier (60-day) is D1-only; consequence not stated
- `THEOPHYSICS_COMMS_VECTOR_MEMORY_PLAN.md` "Memory layers": Hot = 30-day D1+Vectorize; Warm = 60-day D1 metadata/search window; Cold = NAS.
- Implication (unstated): semantic search (Vectorize) only covers the last 30 days. Days 31–60 are text-search only. Day 61+ requires NAS rehydration.
- This may be intentional (cost control) or accidental.
- Recommended next step: state the tradeoff explicitly. "Hot retrieval = semantic + lexical; warm = lexical-only by D1 FTS or LIKE; cold = manual rehydrate."

---

## C. MISSING ASSUMPTIONS — fill before implementation

### C1. Privacy enforcement is named but not located in a layer
- Event schema in `PREFERENCE_ENGINE_REPO_SPEC.md` defines `privacy.level: normal | private | never_store_raw`.
- Comms vector-memory plan stores `privacy level` in D1.
- Neither doc specifies: who sets the default (capture adapter vs BIL core), where redaction happens (capture, store, retrieve, all three), and whether `never_store_raw` also means "do not embed" — embedding inversion can recover sensitive text from the vector itself, so a redacted-text + raw-vector pair leaks.
- Recommended next step: add a "Privacy Layer" section to `PREFERENCE_ENGINE_REPO_SPEC.md` defining per-level handling: storage, embedding, return, log retention.

### C2. D1 schema for `theophysics-comms` is referenced but not committed
- Database ID is fixed (`9ee117a7-f92a-4232-bb45-ae124bc57fe8`). Tables listed: `channels`, `messages`, `sessions`, `logs`.
- The vector-memory plan adds new columns (vector_id, privacy_level, token_count, summary, tags, project, open_loops, embedding_model).
- No migration script (`schema.sql` or `0001_*.sql`) is in the repo. A worker implementing ingestion has to introspect production to learn the existing shape.
- Recommended next step: have Codex export the live `PRAGMA table_info` for each table and commit it as `D:\BIL\theophysics-comms\schema_baseline.sql`. Future migrations stack on that.

### C3. Approval queue for "actions require approval" has no persistence layer
- Tunnel plan says actions queue for approval. Personal-dashboard architecture says the dashboard "queue messages to agents." `BIL_NEXT_BUILDING_MACHINE_STEPS.md` says "All proactive messages/actions require approval."
- Where the queue lives, what survives a BIL restart, and how approvals are signed are unspecified.
- Recommended next step: pick a single store (D1 actions table, or local SQLite, or BIL JSONL log) and document. Likely D1 since it's already the comms ledger.

### C4. Cost caps are policy without numbers
- Tunnel plan: "Let David set a daily soft budget and a hard stop."
- No specific numbers. No specific behavior on hard-stop (return cached? refuse? fallback to local model?).
- Recommended next step: David picks numbers (suggestion: $0.50/day soft, $2.00/day hard for synthesis calls; embedding free since handoff embedding is ~$0.024 / 1000 handoffs at current Workers AI prices). Behavior on hard-stop = degrade to local model + log + show banner.

### C5. Redaction layer required but not implemented in spec
- Tunnel plan "Add a redaction layer for passwords, keys, tokens, and financial data."
- No regex set, no library, no allow/deny path documented.
- Recommended next step: a small `bil/redact.py` reference list (AWS keys, GitHub tokens, generic JWTs, credit-card-like patterns, IBAN, SSN, common env-var names) — apply at capture before disk write.

### C6. Embedding model not chosen
- Three Workers AI models priced in the comms-memory plan; no default selected.
- `@cf/baai/bge-m3` and `@cf/qwen/qwen3-embedding-0.6b` are both `$0.012/M tokens`. Different dimensionality affects Vectorize storage cost.
- Recommended next step: pick one. Default suggestion: `@cf/baai/bge-m3` (multilingual, well-known, 1024-dim) unless dimensionality cost matters more than retrieval quality, in which case `@cf/baai/bge-small-en-v1.5` (384-dim) at slightly higher per-token but lower storage. Cite in the plan.

---

## D. SECURITY / COST EXPOSURE

### D1. (See A1, A4, A5.) Static-content leak + tunnel-without-Access + token-storage-undefined are the top three exposure paths.

### D2. Comms-hub Bearer token model is shared-secret per channel and committed in pinned messages
- Token format: `theophysics-{channel}-2026`, stated in pinned message id 5 ("Welcome to the Comms Hub") and in memory.
- Anyone who reads the orientation message learns every channel's auth token.
- Mitigation today: comms hub itself is at `comms.dlowehomelab.com` behind Cloudflare; access to the orientation message implies access to comms anyway. Effectively, the bearer is a channel-namespacing tag, not a secret.
- Risk if the hostname is ever made public (or scraped from a leaked Bearer in an HTTP log): impersonation as any channel except for the worker-side enforcement that tokens "must match base channel name."
- Recommended next step: low priority right now, but: rotate annually (the `2026` suffix suggests this is already the plan), and avoid posting the pattern in any doc that ships to a public Cloudflare Page.

### D3. Vector embedding inversion is not addressed
- Embedding inversion attacks (Morris et al., 2023; Vec2Text) can recover text from embeddings with ~70% accuracy at small dimensions.
- If the privacy plan treats "redact text but keep vector" as safe, that's wrong. Vectors of redacted content should themselves be redacted.
- Recommended next step: encode in the privacy spec — `private` and `never_store_raw` levels do not produce vectors, only metadata.

### D4. Browser-plugin capture footprint not documented in audit-scope docs
- The plugin observes "Browser activity and search behavior", "search result position, click, skip, bounce, revisit", "clipboard browser-copy".
- Which sites it runs on (manifest match patterns), whether it captures form fields, screenshots, page text — not in any doc I read.
- Recommended next step: a one-page `BROWSER_PLUGIN_SCOPE.md` listing manifest match patterns, what's captured, what's never captured, and the privacy-level default for each capture type.

---

## E. LOW / INFORMATIONAL

- **E1.** Static-demo numbers in the dashboard HTML (2,847 events, 23 clusters, 87 domains, etc.) contradict the actual ~196 historical events stated in `PREFERENCE_ENGINE_REPO_SPEC.md`. Future workers may take the demo at face value. Mitigated by A1 fix.
- **E2.** `PREFERENCE_ENGINE_REPO_SPEC.md` package layout (`preference_engine/core/...`) is target-state, not current. Add a "TARGET, NOT CURRENT" header.
- **E3.** `opus-excel` channel is listed in `THEOPHYSICS_COMMS_VECTOR_MEMORY_PLAN.md` but not in the standing-order pinned welcome message channel list. Either harmonize or note that it's a sub-seat that posts to opus.
- **E4.** Untracked working files in `D:\BIL\` (`CODEX_BRIEFING.md`, `CLAUDE_CODE_NAS_DEPLOY.md`, `CLAUDE_CODE_PROMPT.md`, `HANDOFF_20260429_OPUS.md`, `.claude/`, `.remember/`) are prior-worker state. Audit did not modify them. Codex should decide: commit, archive, or leave untracked.
- **E5.** Personal dashboard subdomain vs. public Theophysics site (`faiththruphysics.com`) cohabitation isn't addressed. The dashboard mock references `faiththruphysics.com` in a clipboard panel; the routing plan keeps everything on `dashboard.dlowehomelab.com`. Decide whether the personal-dashboard routes ever sit under the public Theophysics domain (they shouldn't, IMO — keeps the audit boundary clean).

---

## Independence note

I read this independently without surveying what other channels said about the same files. Where I converge with prior summaries, treat as confidence signal. Where I diverge, treat as fault line worth investigating. Specific divergences worth probing:

- **A1 (static demo)** — the workflow handoff treats the dashboard as "complete enough" for the stopping point. I disagree: complete-as-static-mockup is fine; complete-for-cloudflare-deploy is not, and the wording could mislead a future worker into shipping it.
- **B1 (three dashboards)** — neither doc names this as a problem. It is one.
- **D3 (vector inversion)** — not mentioned in the privacy discussion at all. Worth flagging because the "vectorize handoffs first" decision is partly justified by privacy, and that justification is weaker than stated.

---

## Out of scope (intentionally)

- Live BIL endpoint health (`/bil/status`, `/bil/context`) — Option C in my task-pick. Not run for this audit.
- Code review of `bil_api.py`, `bil_models.py`, `bil_features.py`, `bil_server.py` — repo-spec referenced but not read for this pass.
- Browser-plugin code in `X:\chrome-plugin\` — not opened.
- Any change to architecture direction. This audit is read-only.

---

## Recommended next stabilization step (single best lever)

Pick **A1** (sanitize/replace the static demo HTML or add a "demo only" banner). It's the lowest-effort fix that closes the most leak surface and the most worker-misinterpretation surface at the same time. Everything else in section A can wait until tunnel cutover. Everything in B/C should be one-line answers in the relevant doc.

— opus-ledger, 2026-05-10
