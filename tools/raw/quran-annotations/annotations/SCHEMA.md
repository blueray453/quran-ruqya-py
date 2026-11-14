# `annotations/surah-NNN.json` — file contract (schema 1.0)

One file per surah. This file is the dataset's **single record of truth** for the
annotation layer. It is produced by the LLM annotation step
(`prompts/annotate_ayah.md` + `CONVENTIONS.md`), merged with `tools/collect.py`,
validated by `qa.py`, and consumed by `build.py`. Nothing else in the project is
edited by hand.

## Top level

```json
{
  "schema_version": "1.0",
  "conventions_version": "2.0",
  "surah": 67,
  "language": "en",
  "provenance": { "generator": "...", "note": "..." },
  "ayahs": { "<ayah number as string>": { "status": "...", "clauses": [ ... ] } }
}
```

- `ayahs` may be partial during production: a missing key means "not yet annotated".
  `qa.py` reports completeness against the surah's ayah count.
- `provenance` records who/what produced the file (e.g. `llm-annotation` with model
  id, or `prototype-replay` for the bundled sample).

## Ayah entry

- `status` — one of `"auto"` | `"needs_human"` | `"reviewed"`.
  - `auto`: fresh LLM output, not yet reviewed.
  - `needs_human`: QA or review flagged it.
  - `reviewed`: passed human review.
- `clauses` — ordered list. Each clause is an object:

```json
{ "words": [5, 6, 7, 8, 9], "phrases": [ { "words": [5], "en": "and He is" }, ... ] }
```

## Phrase

- `words` — contiguous, ascending, 1-based word positions. These are **real word
  numbers** (the numbering used by the recitation timestamps). The ayah-end marker
  is not a word here; in the keyed sources the marker is the last key, so
  `keyed_max == real_max + 1` for every ayah.
- `en` — the English fragment. The fragments of an ayah, joined with single spaces
  in Arabic order, must read as natural English.

## Invariants (enforced by qa.py)

1. Clauses tile the ayah: word positions `1..N` each covered exactly once, in order
   (`N` = real word count of the ayah from the text source).
2. Phrases tile each clause the same way.
3. `en` is a non-empty string on every phrase.
4. `status` is in the enum above.

## Bangla (frozen, optional slot)

Scope is English-only. A fourth slot (`"bn"` per phrase) may be added later without
any structural change; nothing else in the schema anticipates it.

## Known-good reference

`annotations/surah-067.json` replays the hand-edited Surah 67 prototype:
**333 words / 213 phrases / 86 clauses**. `qa.py` asserts these totals for surah 67.
