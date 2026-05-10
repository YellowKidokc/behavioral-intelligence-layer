# Theophysics Comms + Vector Memory Plan

## Core Idea

The session handoff is the highest-value unit of memory.

Do not start by vectorizing every full conversation. Start by vectorizing the session handoff messages that David copies into BRAIN / comms, because those are already compressed, curated, and written for future AI sessions.

Raw conversations can still be archived locally or in R2, but the portable memory layer should begin with handoffs.

## Why Session Handoffs First

Session handoffs are:

- Dense.
- Intentional.
- Written for future retrieval.
- Smaller than raw chats.
- Less noisy than full conversations.
- Easier to classify by project, channel, date, and open loop.
- Cheap to embed.
- Safer to send into Cloudflare because they are already summaries.

Full conversations are useful later, but they create more chunks, more duplicate vectors, more privacy risk, and more retrieval noise.

## Cost Read

Cloudflare Vectorize bills by stored vector dimensions and queried vector dimensions. It does not charge for CPU, memory, active index hours, or index count. Empty indexes do not count as stored vector dimensions, and Vectorize does not charge for egress.

Workers AI embeddings are also inexpensive. Current official pricing lists:

- `@cf/qwen/qwen3-embedding-0.6b` at `$0.012 per M input tokens`.
- `@cf/baai/bge-m3` at `$0.012 per M input tokens`.
- `@cf/baai/bge-small-en-v1.5` at `$0.020 per M input tokens`.

Rough math:

- One 2,000-token handoff at `$0.012 / 1M tokens` costs about `$0.000024` to embed.
- 1,000 handoffs at 2,000 tokens each is about 2M tokens, or roughly `$0.024` for embeddings.
- One 50,000-token full conversation costs about `$0.0006` to embed, but it usually needs chunking into many vectors and creates more retrieval noise.
- 1,000 full conversations at 50,000 tokens each is about 50M tokens, or roughly `$0.60` for embeddings before Vectorize query/storage costs.

Vectorize storage/query costs are also low at this scale. Official examples show:

- 5,000 vectors at 384 dimensions with 10,000 monthly queries estimated around `$0.06/mo`, included in free-tier-style usage.
- 50,000 vectors at 768 dimensions with 200,000 monthly queries estimated around `$1.94/mo`.
- 250,000 vectors at 768 dimensions with 500,000 monthly queries estimated around `$5.86/mo`.

Conclusion: vectorizing curated handoffs is extremely cheap. The real cost risk is not money; it is noise, privacy, and bad retrieval if raw conversations are dumped in without structure.

Sources:

- Cloudflare Vectorize pricing: https://developers.cloudflare.com/vectorize/platform/pricing/
- Cloudflare Workers AI pricing: https://developers.cloudflare.com/workers-ai/platform/pricing/
- Qwen embedding model: https://developers.cloudflare.com/workers-ai/models/qwen3-embedding-0.6b/

## D1 + Vectorize Shape

Use D1 as the ledger and Vectorize as semantic memory.

D1 stores:

- message id
- session id
- channel from
- channel to
- category
- priority
- created timestamp
- read timestamp
- raw handoff text
- summary
- tags
- project
- open loops
- source URL/path when available
- vector id
- embedding model
- token count
- privacy level

Vectorize stores:

- vector id
- embedding vector
- metadata fields for routing and filtering

Suggested vector id format:

```text
handoff:{message_id}
session:{session_id}:summary
openloop:{message_id}:{loop_index}
```

## What To Embed

Phase 1:

- `messages.category = 'session-log'`
- high-priority broadcast handoffs
- targeted AI-to-AI requests
- open-loop summaries
- major findings

Phase 2:

- Daily manager briefings
- BIL daily intake summaries
- truth/fruits analysis summaries
- preference discoveries

Phase 3:

- Selected raw conversation chunks, only when marked useful
- Obsidian canonical notes
- research paper notes
- code handoff notes

## What Not To Embed Yet

Do not immediately vectorize:

- every raw clipboard entry
- every full chat transcript
- private credentials
- browser noise
- transient debugging logs
- unreviewed screenshots

Those can be captured locally, summarized, then embedded only if they become useful.

## Retrieval Pattern

When an AI session starts:

1. Check unread comms.
2. Pull recent handoffs from D1.
3. Embed the current task/question.
4. Query Vectorize for nearest session handoffs, findings, and open loops.
5. Return a compact brief:
   - unread comms
   - top related handoffs
   - unresolved open loops
   - recent decisions
   - disagreements between AI channels

The AI should not receive the whole database. It should receive the smallest useful context packet.

## Theophysics AI Communications Hub Summary

David Lowe / POF 2828 runs multiple independent AI sessions across the Theophysics project. Each AI has a channel in a shared Cloudflare D1 database.

Purpose:

- Avoid duplicate work.
- Preserve breakthroughs across sessions.
- Let independent AI voices converge naturally.
- Surface disagreement as useful signal.
- Give each new AI session the latest project state.

Database:

- Platform: Cloudflare D1 / SQLite.
- Database name: `theophysics-comms`.
- Database ID: `9ee117a7-f92a-4232-bb45-ae124bc57fe8`.
- Tables: `channels`, `messages`, `sessions`, `logs`.

Main channels:

- `broadcast` - system broadcast
- `david` - David Lowe
- `opus` - Claude Opus
- `opus-excel` - Claude Opus Excel/auditor
- `codex` - Claude Codex / engineer
- `claude-code` - Claude Code / engineer
- `gemini` - Google Gemini / adversarial review
- `haiku` - Claude Haiku / web and bulk ops
- `sonnet` - Claude Sonnet / research, coding, analysis
- `perplexity` - citation research
- `ollama` - local reasoning
- `gpt` - ChatGPT / adversarial review
- `claude-desktop` - general Claude desktop sessions

Start protocol:

- Read unread messages for the current channel or broadcast.
- Mark them read.
- Tell David a short summary.
- Do not dump raw comms.

End protocol:

- Post one dense session summary to broadcast.
- Include files, theorem names, decisions, breakthroughs, open problems, next-session instructions, and requests for other AIs.

Independence rule:

- Read other AI messages, but do not simply agree with them.
- Keep independent judgment.
- Natural agreement is confidence signal.
- Persistent disagreement is a fault line worth investigating.

## BIL Integration

BIL should treat comms as one of its main memory inputs.

New capture source:

```text
source = "theophysics_comms"
model = "comms"
category = "session-log" | "request" | "finding" | "question" | "alert"
```

New pipeline:

```text
comms message
  -> normalize
  -> classify
  -> extract open loops
  -> summarize if needed
  -> embed handoff
  -> store metadata in D1
  -> store vector in Vectorize
  -> expose in /bil/context
```

## NLP Chain

The next programming chain should be an NLP pipeline:

1. Normalize text.
2. Detect source/channel/project.
3. Classify message type.
4. Extract entities: files, domains, APIs, theorem names, repo paths, people, AI names.
5. Extract open loops and next actions.
6. Detect disagreement or verification requests.
7. Produce compact summary.
8. Embed summary.
9. Store vector + D1 metadata.
10. Retrieve relevant handoffs for future sessions.

This chain can run cheaply on local models or Workers AI embedding/classification, with OpenAI/Anthropic reserved for high-value synthesis.

## Real-Time Comms Notifications

The comms hub needs live workflow signals, not only archived messages.

Add a notification layer beside `messages`.

Suggested table:

```sql
CREATE TABLE notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target_channel TEXT NOT NULL,
  source_channel TEXT,
  title TEXT NOT NULL,
  body TEXT,
  level TEXT NOT NULL DEFAULT 'info',
  status TEXT NOT NULL DEFAULT 'new',
  related_message_id INTEGER,
  related_session_id TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  acknowledged_at TEXT,
  completed_at TEXT,
  defer_until TEXT
);
```

Levels:

- `info` - visible, no interruption.
- `soft` - notice soon.
- `checkpoint` - stop at next safe pause.
- `urgent` - inspect now.

Statuses:

- `new`
- `seen`
- `deferred`
- `inspecting`
- `done`

Worker loop:

1. Worker starts and checks comms.
2. Worker polls notifications while working.
3. If notification is soft/checkpoint/urgent, worker decides whether to defer or inspect.
4. Worker acknowledges the notification with status.
5. Worker includes unresolved notifications in its session handoff.

This gives AI workers a live "email/notification" layer without constantly derailing their task.

## Practical Decision

Build this order:

1. Vectorize session handoffs first.
2. Store metadata in D1 and vectors in Vectorize.
3. Add `/bil/comms/ingest` for copied handoffs.
4. Add `/bil/comms/search` for semantic retrieval.
5. Add comms results into `/bil/context`.
6. Later add full-conversation chunking only when a handoff points back to a raw archive.

This gives the personal dashboard and every AI session a real memory layer without spending much money or flooding retrieval with noise.

## Rolling Memory Retention

Use rolling memory instead of trying to keep everything hot forever.

Default policy:

- Keep the most recent 30 days in hot memory.
- Optionally extend to 60 days if cost and retrieval quality stay good.
- Export a daily snapshot before the day rolls over.
- Store snapshots on the Synology NAS for long-term archive.
- Keep raw/full conversations in NAS archive, not live AI context.
- Keep handoff vectors live because they are compact and useful.

Memory layers:

- Hot: 30-day D1 + Vectorize working set.
- Warm: 60-day optional D1 metadata/search window.
- Cold: NAS archive of daily snapshots, raw handoffs, full conversations, exports, and compressed summaries.

Daily rollover:

1. Collect the day's comms messages, BIL events, handoffs, open loops, and daily summary.
2. Save one dated snapshot file locally.
3. Copy the snapshot to the Synology NAS.
4. Keep compact handoff vectors in Vectorize.
5. Remove or deprioritize older low-value vectors from hot retrieval.
6. Keep an index record so old snapshots can be rehydrated later.

Suggested NAS path:

```text
\\SynologyNAS\AI-Memory\BIL\Snapshots\YYYY\MM\YYYY-MM-DD\
```

Suggested files per day:

```text
daily-summary.md
comms-handoffs.jsonl
bil-events.jsonl
open-loops.json
vector-manifest.json
raw-conversation-links.json
```

Rehydration rule:

If a future question needs old memory, search the 30-day hot memory first. If the answer is not there, search the NAS snapshot index and rehydrate only the relevant old handoffs or summaries into the current context.

This keeps token use controlled while preserving the long-term record.
