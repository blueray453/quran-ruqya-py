# `annotations/surah-NNN.json` — file contract (schema 1.0)

One file per surah **per language**. The English file is the dataset's **single
record of truth** for the segmentation. It is produced by the LLM annotation step
(`prompts/annotate_ayah.md` + `CONVENTIONS.md`), merged with `tools/collect.py`,
validated by `qa.py`, and consumed by `build.py`. Other languages ride along as
**separate overlay files** (see "Language overlay files" below) — never as extra
slots inside this file. Nothing else in the project is edited by hand.

## Top level

```json
{
  "schema_version": "1.0",
  "conventions_version": "2.1",
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

## Language overlay files (`annotations/<lang>/`)

Every non-English language lives in its **own file** — `annotations/bn/surah-NNN.json`
for Bangla — with the same header shape and `"language": "<lang>"`. The overlay is
**gloss-only**: the segmentation belongs to the Arabic text and is decided once (in
the English pass). Therefore an overlay mirrors the English file exactly — same
ayah keys, same clause `words`, same phrase `words` spans — and each phrase carries
`"bn": "..."` (the language's fragment) instead of `"en"`.

- The bn pass runs only after the English ayah passed `qa.py` (`prompts/annotate_ayah_bn.md`);
  raw output is a flat list of strings, one per phrase, aligned positionally by
  `tools/collect.py --lang bn` (count mismatch aborts; a bn ayah without an
  English counterpart aborts).
- Separation is fenced in both directions: `qa.py` fails on a `bn` slot inside the
  English file and on `en` content inside a bn overlay.
- Script fences per fragment: Bengali script (U+0980–U+09FF) required, Arabic
  script forbidden; status enum and `reviewed` protection identical to English.
- `build.py` emits `data/bn/surah-NNN.json` — a separate overlay view keyed by
  clause/phrase ids that joins against `data/surah-NNN.json` (ids, word spans,
  `bn_assembled` per ayah); words, audio timings and English content are not
  duplicated.
- A future language adds `annotations/<lang>/` + a `collect.py --lang <lang>`
  branch + the same fences; nothing else changes.

## Known-good reference

`annotations/surah-067.json` replays the hand-edited Surah 67 prototype:
**333 words / 213 phrases / 86 clauses**. `qa.py` asserts these totals for surah 67.
`annotations/bn/surah-067.json` replays the same prototype's hand-edited Bangla
fragments into the overlay contract; `qa.py` asserts the same totals for it
(structural identity implies them).
