# quran-annotations

Annotation layer for the whole Quran: for every ayah, **clauses → phrases → one
English fragment per phrase**, fragments in Arabic word order. The annotation file
is the dataset's single record of truth; everything else is either a read-only
source (never modified) or a deterministic, regenerable view.

Scope: whole Quran (6,236 ayahs / 77,432 real words). English is the base layer;
**Bangla rides along as a separate overlay** (`annotations/bn/`), never as a slot
inside the English file (see `annotations/SCHEMA.md`).

## Layout

```
quran-annotations/
├── sources.lock.yaml        pinned read-only sources (sha256, role, license status)
├── CONVENTIONS.md           the only rules document; enters the annotation package
├── prompts/
│   ├── annotate_ayah.md       the per-ayah LLM prompt template (the only segmentation step)
│   └── annotate_ayah_bn.md    the per-ayah Bangla gloss prompt (second pass, overlay)
├── annotations/
│   ├── SCHEMA.md              file contract for surah-NNN.json + language overlays
│   ├── surah-067.json         SAMPLE: English, replaying the hand-edited prototype
│   │                          (333 words / 213 phrases / 86 clauses) — dummy for format
│   └── bn/
│       └── surah-067.json     SAMPLE: Bangla overlay — separate file, mirrors the English
│                              spans exactly, hand-edited bn fragments replayed
├── tools/
│   └── collect.py             merge raw LLM output (--lang en segmentation / --lang bn gloss)
├── build.py                   sources + annotations -> data/surah-NNN.json + data/bn/ overlays
├── qa.py                      hard fences + cross-checks (exit 1 on any FAIL)
├── data/                      generated views (regenerable, never hand-edited)
└── sources/                   the read-only layer (see sources/README.md)
```

## Quickstart

```bash
python3 qa.py                 # verify sources + annotations (en + bn, surah 67 sample)
python3 build.py --surah 67   # regenerate data/surah-067.json (joins text, wbw,
                              # translation, recitation windows) and, when the
                              # overlay exists, data/bn/surah-067.json
```

Both scripts are stdlib-only Python 3, offline and deterministic.

## Pipeline (segmentation LLM pass + per-language gloss passes)

1. **Lock** — sources live under `sources/` and are pinned in `sources.lock.yaml`.
   Never modify them; `qa.py` verifies every sha256 before anything else.
2. **Annotate** — for each ayah, fill the template in `prompts/annotate_ayah.md`
   (words + wbw glosses + whole-ayah translation + `CONVENTIONS.md` attached) and
   send it to the LLM. The model returns JSON only. This is the only step that
   decides segmentation.
3. **Collect** — `python3 tools/collect.py --surah N --file llm_output.json`
   merges the reply into `annotations/surah-NNN.json` with `status: auto`
   (refuses to overwrite `reviewed` ayahs).
4. **Fence** — `python3 qa.py --surah N`: tiling assertions, wbw coverage,
   chunker-boundary subset check, baseline replay for surah 67.
   Failures go back to re-annotation or `status: needs_human`.
5. **Bangla overlay** — for each fenced ayah, fill the template in
   `prompts/annotate_ayah_bn.md` (words + wbw + the existing phrase list + the
   whole-ayah Bangla reference translation) and send it to the LLM. The model
   returns one Bangla fragment per phrase, in order — it never re-segments. Merge
   with `python3 tools/collect.py --surah N --file llm_output_bn.json --lang bn`
   (aborts on count mismatch or missing English ayah), then `qa.py` re-checks:
   structural identity with the English file, Bengali script required / Arabic
   script forbidden, bn wbw coverage, translation_bn completeness.
6. **Review** — human review flips `auto` → `reviewed` (flagged ayahs + a sample),
   per language: the English file and the bn overlay carry independent statuses.
7. **Build** — `python3 build.py --surah N` regenerates the reader view
   (`data/surah-NNN.json`), including highlight windows joined from any reciter
   file with segments `[word_no, start_ms, end_ms]`, plus the separate Bangla
   overlay view `data/bn/surah-NNN.json` when the overlay file exists.

## What the annotation layer does NOT contain

- No linguistic tags, no i'rab groups, no chunker output, no mined statistics —
  the LLM never sees any of these (anti-circularity).
- No glossary: word-by-word glosses already arrive per word, and the same-Arabic /
  same-English drift check lives in the **separate whole-Quran glossary project**,
  which consumes the (Arabic phrase → English fragment) pairs mined from finished
  annotations. Frequent agreements become draft glossary rows; conflicts become a
  curation queue. The glossary project, once published, will be referenced from
  `sources.lock.yaml` like any other read-only source — never embedded.

## Verified facts baked into the code

- Word numbering: the keyed text/wbw sources count the ayah-end marker as the last
  key, so `keyed_max == real_max + 1`; annotations and recitation timestamps use
  **real word numbers** (whole Quran: 83,668 keyed entries → 77,432 real words).
- wbw glosses are missing for exactly 3 real word positions (`2:181:4`, `8:6:5`,
  `13:37:9`) — rendered as `null`, asserted by `qa.py`. The Bangla wbw source is
  missing exactly the same 3 positions (`KNOWN_MISSING_WBW_BN`).
- Bangla is fully sourced in the overlay view: `build.py` joins the whole-Quran
  Bangla translation (`translation_bn`) and per-word Bangla glosses (`wbw_bn`)
  into `data/bn/surah-NNN.json`; the base view stays English-only.
- Recitation: 5,824/6,236 ayahs align 1:1 with segments; the rest carry extra
  short fragments (pauses / aligner artifacts). `build.py` applies the documented
  fallback (<100 ms → merge into nearest word; longer extras → time-order mapping;
  leftovers reported). Timestamps stay in milliseconds — any reciter file with the
  same shape joins for free.
- Chunker (`sources/chunker/quranic-treebank-0.4-chunks.tsv` — the Quranic Arabic
  Corpus treebank 0.4 chunks layer; role: QA cross-check only): on surah 67 its 56
  boundaries are a strict subset of the 86 clause boundaries — asserted per ayah
  by `qa.py` wherever the chunker has coverage.
- Highlight windows are pure arithmetic: `window(phrase) = [first word start, last
  word end]`. Example from the sample: phrase `67:1:1.1` (word 1) → `0–920 ms`.

## Planned fences (not yet implemented)

- EQTB clause starts ≈ annotation clause starts (`sources/eqtb/Quranic.csv`).
- Waqf marks → clause starts (15/15 held on the prototype).
- Translation family for the whole Quran in **English** (only surah 67 is pinned
  today; the Bangla translation family is whole-Quran already).

## License status

Every family in `sources.lock.yaml` carries `license: unverified-pending` plus a
specific note. Known so far: the Quranic Arabic Corpus morphology file is GPL with
Tanzil text under CC BY-ND 3.0 (per its header); the chunker file states no license.
Resolve all before any publication.

## Sample file provenance

`annotations/surah-067.json` is a **dummy demonstrating the format**: it replays
the hand-edited Surah 67 prototype (`sources/reference/mulk_spec.json`) into this
schema, verified against the recitation alignment. `annotations/bn/surah-067.json`
replays the same prototype's hand-edited Bangla fragments into the overlay
contract (separate file by design). In production, files are produced by the LLM
steps (`status: auto`) and become `reviewed` only after human review. The
overlay view additionally carries the sourced Bangla joins — `translation_bn`
(whole-ayah translation, `sources/translation/quran-bn-dr-abu-bakr-muhammad-zakaria-simple.json`)
and `words[].wbw_bn` (per-word glosses, `sources/wbw/bangla-wbw-translation.json`);
`bn_assembled` remains the draft fragment reading.
