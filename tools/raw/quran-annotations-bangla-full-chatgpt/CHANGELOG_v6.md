# Version 6 changes

## Segmentation conventions

- Refined the target to the **smallest valid Arabic syntactic-semantic chunk**, not the
  smallest possible word count.
- Added explicit guidance for conditional particles, function words, required predicate / argument
  relationships, prepositions and complements, and other local dependencies.
- Reaffirmed that treebank boundaries, English fluency, and chunk-size averages do not decide
  Arabic segmentation.
- Added source-grounded regression cases from the v5 pilot, including 2:196, 2:282, 4:12,
  4:176 and Al-Mulk 67:8, 67:16, 67:27 and 67:30.

## Islamic terminology

- English output must use Allah, Rabb, ilah / ilahs, or the applicable established Islamic name
  according to the actual Arabic source.
- Bangla output must use আল্লাহ, রব, ইলাহ according to the actual Arabic source.
- Terminology violations are checked during annotation validation and by `qa.py`.

## Attempt / retry observability

- Each live model call is archived under `runs/<tag>/attempts/<attempt-id>.json`.
- Attempt records include the system and user prompts, exact request metadata, raw model text,
  provider response payload, usage, timing, parse status, and errors when available.
- `calls.jsonl` indexes the attempts.
- `retry_events.jsonl` records initial validation failures, successful retry resolution, and
  failures that remain unresolved. Each event links to the exact attempt files.
- Bangla-only repair calls and optional semantic-audit calls are also archived.

## Source trace and historical pilot

- Validated raw annotation JSON now embeds exact Arabic source words, one-based positions,
  English and Bangla word-by-word glosses, and full-ayah reference translations.
- `tools/export_evidence.py` exports the source trace beside the final English/Bangla chunks.
- The supplied historical v5 archive did not include original raw requests or responses. Its
  four retry-resolved validation failures are recorded in
  `pilot_evidence/historical_retry_events.jsonl`, with raw-payload availability correctly marked
  false. They are not reconstructed or fabricated.
- Historical v5 final annotations are retained as evidence copies. Any terminology normalization
  in those copies is documented in the evidence provenance; the original uploaded archive is
  unchanged.

## QA and tools

- Retired the old word-overlap heuristic that falsely called context-dependent fragments
  semantically missing.
- Added conservative syntactic review candidates and an optional non-mutating semantic audit.
- Added regression tests for terminology, source-linked Arabic words, historical retry records,
  and live retry/raw-response archiving.
