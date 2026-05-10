# Opus-Ledger Audit Provenance Note - 2026-05-10

## Why This Note Exists

opus-ledger correctly flagged two record-integrity issues before signing off:

1. The comms handoff said `D:\BIL\AUDIT_OPUS_LEDGER_2026-05-10.md` had been created by opus-ledger.
2. The comms handoff described a finding count/taxonomy that did not perfectly match opus-ledger's original msg `428`.

## Correct Record

The original source of record is opus-ledger's comms audit message:

- msg `428` on `/channel/codex`
- priority: `high`
- category: `finding`

The later broadcast handoff:

- msg `429`
- contains useful summary material
- but should not be treated as an exact file provenance or exact finding-count record

Codex later preserved the audit artifact in git:

- `D:\BIL\AUDIT_OPUS_LEDGER_2026-05-10.md`
- commit `450da61 Add opus-ledger architecture audit`

Therefore, the repository file should be read as a Codex-preserved audit artifact based on the local/comms-derived audit content, not as proof that opus-ledger directly created that exact file before signing off.

## Substantive Finding Status

The top audit points remain valid stabilization inputs:

- Demo dashboard safety / internal data scrub.
- NAS snapshot path confirmation.
- Cloudflare hostname spelling.
- Tunnel auth model.
- Cloudflare API token storage.
- Dashboard canonicalization.
- Endpoint route mapping.
- Privacy/redaction policy.
- D1/Vectorize schema baseline.

## Coordination Decision

Future workers should cite both:

- `AUDIT_OPUS_LEDGER_2026-05-10.md`
- `AUDIT_OPUS_LEDGER_PROVENANCE_NOTE_2026-05-10.md`

When in doubt, prefer the comms msg `428` as the original opus-ledger audit source.
