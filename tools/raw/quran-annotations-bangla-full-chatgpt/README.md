# Quran Arabic phrase-chunk annotation (Bangla + English)

This project annotates Quran ayahs as **small, contiguous Arabic syntactic / semantic
chunks**. The goal is not clause segmentation and not word-by-word glossing. A chunk should
be the smallest meaningful unit that preserves its local Arabic grammatical relationship.
The English and Bangla fragments are translations of exactly the same Arabic span.

New annotation shape:

```json
{
  "67:1": [
    {"ar": "تَبَارَكَ", "en": "Blessed is", "bn": "বরকতময়"},
    {"ar": "الَّذِىۡ", "en": "the One who", "bn": "যিনি"}
  ]
}
```

The pipeline derives word positions from the Arabic copies, checks exact coverage, stores
flat `chunks[]`, and creates separate English and Bangla files. Legacy `clauses[].phrases[]`
files are still readable by QA and build tools, but all new model output is flat.

## 1. Setup

Python 3.10+; no Python packages are required (stdlib only).

```bash
python3 --version
```

For real model calls, configure an OpenRouter API key:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

## 2. Offline smoke test (no API key and no cost)

The bundled Surah 67 reviewed prototype is replayed through the new flat-chunk pipeline.
This checks parsing, Arabic-word alignment, storage, merge, and QA without calling an LLM.

```bash
python3 tools/run_llm.py --surah 67 --tag smoke_chunks --mock-replay --workers 1
python3 qa.py --surah 67 --annotations-dir runs/smoke_chunks/annotations
python3 tools/chunker_report.py --surah 67 --annotations-dir runs/smoke_chunks/annotations
python3 build.py --surah 67 --annotations-dir runs/smoke_chunks/annotations --out-dir runs/smoke_chunks/data
```

Expected: 30 ayahs and 333 Arabic words validate; the replay contains 213 chunks. The
chunker report is diagnostic only: its boundaries are not treated as required phrase
boundaries.

## 3. Dry run, then annotate a small pilot

Inspect the prompt without making an API call:

```bash
python3 tools/run_llm.py --ayahs 67:1-3 --tag dry_preview --dry-run
```

Run a small live pilot:

```bash
python3 tools/run_llm.py --ayahs 67:1-3 --tag pilot_chunks
python3 qa.py --surah 67 --annotations-dir runs/pilot_chunks/annotations
python3 tools/review_flags.py --annotations-dir runs/pilot_chunks/annotations --out runs/pilot_chunks/review_flags.md
```

`tools/run_llm.py` is resumable. Validated ayahs are saved in `runs/<tag>/raw/`. Re-running
with the same tag skips completed ayahs. New output is written under `runs/<tag>/`, not to
`annotations/`, unless `--out-dir` explicitly directs it elsewhere.

## 4. Main pipeline

1. **Prompt** — the model sees Arabic words, English/Bangla word glosses, whole-ayah
   translations, and `CONVENTIONS.md`. It does not see chunker/treebank output or linguistic
   annotation labels.
2. **Segment** — model returns a flat ordered list of `{ar, en, bn}` chunk objects.
3. **Validate** — the pipeline aligns each Arabic copy to the original words and verifies
   exact word coverage, order, non-empty translations, and script constraints.
4. **Refine/escalate** — only phrase-chunk granularity and meaning-preservation checks are
   used. No clause-size metric or clause boundary is optimized.
5. **Merge** — `tools/collect.py` creates a flat English `chunks[]` file and a separate
   Bangla overlay with identical chunk spans.
6. **QA/review** — `qa.py` verifies tiling, source integrity, Bangla scripts, and overlay
   identity. Chunker reports are post-hoc diagnostics, not segmentation instructions.
7. **Build** — `build.py` joins Arabic text, word glosses, translations, and recitation
   windows into reader JSON views.

## 5. Useful commands

```bash
# Count ayahs by Arabic word length and chunker coverage
python3 ayah_length_counter.py

# Inspect a prompt
python3 tools/run_llm.py --ayahs 2:282 --tag preview --dry-run

# Sample ayahs by length, restricted to chunker-covered examples
python3 tools/sample_ayahs.py --out band_sample.txt

# Inspect chunker overlap (diagnostic only)
python3 tools/chunker_report.py --annotations-dir runs/pilot_chunks/annotations --out report.md

# Build data views from the default annotations/ directory
python3 build.py --surah 67
```

## 6. Chunk-size guidance

The reviewed Al-Mulk prototype averages about 1.6 words per chunk. Treat that as a useful
reference, not a quota. Many valid chunks are one word; two-word units are common; three-word
units are acceptable where syntax requires them. Chunks longer than four words deserve review,
but should not be split mechanically. Do not force one-word segmentation when it would break
an Arabic dependency or create a meaningless fragment.

## 7. Data and source integrity

Files under `sources/` are read-only and pinned in `sources.lock.yaml`. `qa.py` checks their
SHA-256 hashes. The keyed text includes an ayah-end marker as the final key; annotations and
audio positions use only real words. The three known-missing word-by-word gloss keys remain
handled by QA as before.

## 8. Legacy compatibility

Bundled legacy `clauses[].phrases[]` annotations can still be read by `qa.py`, `build.py`,
`tools/review_flags.py`, and `tools/chunker_report.py`. New work should use `chunks[]` only.
`tools/conform_chunker.py` is retired because treebank boundaries must not be used to force
chunk boundaries.
