# Folder Automations & Pipelines

FAP is the folder nervous system for BIL/PIL.

It is not only file movement. It is station-based workflow execution:

```text
folder event -> station -> verdict -> route -> manifest -> signal -> next station
```

## Core Concepts

- **Pipeline**: the rails between stations.
- **Station**: a processing point with input, output, pass/fail/review routes, and a processor.
- **Folder Automation**: a hot folder bound to a station.
- **Manifest**: the document's passport through the system.
- **Signal**: a message upstream or outward, such as gap, duplicate, quality, ready, or error.
- **LLM Hub**: queued model work for slow/expensive thinking stations.
- **Wiki Layer**: human-readable operating manual and station self-documentation.

## Station Categories

### 1. Intake Stations

Receive files and determine whether they are safe and processable.

Examples:

- hot-folder intake
- cold-folder sweep
- download intake
- NAS intake
- cloud/R2/Drive intake

### 2. Identity Stations

Decide what a thing is.

Examples:

- classifier
- series detector
- document type detector
- law/domain classifier
- axiom/7Q candidate detector

### 3. Transformation Stations

Change medium or structure.

Examples:

- lossless formatter
- HTML normalizer
- Markdown exporter
- JSON sidecar builder
- TTS generator
- STT transcriber
- video packager
- thumbnail/caption builder

### 4. Verification Stations

Do not move a paper forward unless it earns the right.

Examples:

- paper grader
- axiom rigor gate
- Lean candidate detector
- duplicate detector
- citation/evidence checker
- contradiction checker

### 5. Publication Stations

Make the finished artifact usable somewhere else.

Examples:

- AI portal generator
- vectorization/chunking
- Obsidian/wiki page writer
- R2/Cloudflare publisher
- archive/final package builder

### 6. Reciprocal Signal Stations

Send useful signals backward.

Examples:

- gap detector: no paper covers an axiom
- duplicate detector: new item overlaps existing item
- quality loop: grader sends it back to lossless
- creation request: write or revise a missing paper

## Postgres Rule

Postgres records the truth, but it does not need to be hit for every millisecond of movement.

Recommended rhythm:

- local JSONL logs for immediate station actions,
- Postgres sync twice a day or at run boundaries,
- Postgres as durable ledger and dashboard source.

Installed support:

```text
D:\BIL\RUN_FAP_POSTGRES_SYNC.bat
D:\BIL\INSTALL_FAP_POSTGRES_SYNC_TASKS.bat
```

The scheduled sync lane is intentionally separate from the hot-folder watcher.

## Wiki Rule

The wiki explains the system. Postgres records the system. FAP operates the system.

Do not let the wiki become the database.

## First Real Manufacturing Line

```text
INTAKE
-> CLASSIFY
-> MEDIA ROUTE
-> LOSSLESS
-> VECTORIZE
-> PAPER GRADE
-> AXIOM RIGOR
-> AI PORTAL / FINAL PACKAGE
```

This is the paper mill line. Other lines can reuse the same station types.
