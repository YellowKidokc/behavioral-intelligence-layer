# Personal Dashboard Architecture

This is the larger "Cloudflare personal dashboard" vision built on top of BIL and the preference engine.

## One-Sentence Product

A personal daily intake dashboard that gathers what David reads, copies, watches, says, saves, and builds; runs it through preference/truth/fruits filters; organizes it into a living personal knowledge surface; and queues useful actions for nearby AI agents.

## What It Is Not

It is not just a dashboard of widgets.

It is not just RAG search.

It is not just a diary.

It is a personal operating layer for intake, sorting, evaluation, recall, and agent coordination.

## Daily Intake Sources

- Browser activity and search behavior
- Clipboard text and reuse patterns
- Speech/dictation transcripts
- YouTube videos and transcripts
- Obsidian vault notes
- Local files and downloads
- GitHub repositories and code snippets
- AI conversations and handoffs
- Screenshots/captures
- Manual ratings and notes

## Processing Layers

### 1. Capture

Everything enters as small events:

```text
source -> event -> text/metadata -> local log -> preference engine
```

Examples:

- Copied text
- Watched video
- Clicked search result #7
- Saved a PDF
- Asked Codex to change a plugin
- Claude produced a useful architecture note

### 2. Evaluation

Each event can be scored or tagged by multiple lenses:

- Preference engine: does this match David's learned taste/work patterns?
- Truth engine: is this likely truthful, deceptive, uncertain, unsupported?
- Fruits engine: does this produce clarity, patience, humility, courage, love, coherence?
- Relevance engine: which project does this belong to?
- Urgency engine: should this become an action now or go into archive?

### 3. Organization

The system should not wait for manual filing. It should infer placement and then make it inspectable.

Possible buckets:

- Today
- Needs action
- Research
- Theophysics
- Code/build
- AI handoff
- Watch/listen later
- Save to Obsidian
- Ignore/decay
- Private/sensitive

### 4. Personal Surface

The dashboard should feel personal, not generic.

It should show:

- What came in today
- What mattered today
- What was probably noise
- What needs follow-up
- What AI work is unfinished
- What repeated pattern is emerging
- What the system thinks David is currently doing

## AI Coordination Layer

This is the part that makes the system feel like an operating layer.

The dashboard should be able to queue messages to agents:

```text
Hey Codex, this plugin task was started but not finished.
Hey Claude, summarize these three intake items into a note.
Hey local model, classify this clipboard cluster.
Hey file sorter, move these PDFs to the likely project folder.
```

The system should notice open loops:

- A plugin was modified but not live-tested.
- A dashboard idea was discussed but not captured.
- A Cloudflare deployment changed but Edge still shows an old cache.
- A task shifted to Claude before Codex finished verification.
- A repeated search implies a missing pinned shortcut or note.

## RAG Role

The dashboard becomes a personal RAG surface by indexing:

- Obsidian
- clipboard history
- transcripts
- browser/search history
- code/project notes
- AI handoffs

But RAG is not the whole product. RAG answers questions. The preference engine decides what matters. The truth/fruits engines evaluate quality. The dashboard organizes action.

## Minimum Useful Version

Build the smallest version that proves the loop:

1. BIL captures browser/search/clipboard events.
2. `/bil/context` returns a compact working-memory pack.
3. Dashboard reads `/bil/context`.
4. Dashboard shows:
   - current mode guess
   - recent clipboard
   - top domains
   - open loops
   - suggested next actions
5. User can correct the system.

## First Open Loops To Track

- Extension must be loaded/reloaded from `X:\chrome-plugin`.
- SearXNG live result re-ranking needs a real browser test.
- Clipboard copy is captured; paste/reuse outside browser still needs stronger detection.
- Truth/fruits scoring is conceptual and needs a first schema.
- Cloudflare personal dashboard needs to consume BIL context.

## Guiding Rule

The system should not merely remember what happened. It should help David see the whole picture and act on what matters next.
