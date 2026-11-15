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

For live model calls, create an API key in OpenRouter and configure it:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

The default model is `openai/gpt-6-luna`, called through OpenRouter's OpenAI-compatible
Chat Completions endpoint. The script uses the OpenRouter model slug, not the bare `gpt-6-luna` name.

## 2. Live smoke test (OpenRouter API; low-cost model)

The primary smoke test makes real model calls using `openai/gpt-6-luna` through OpenRouter.
It includes these required ayahs:

- Al-Baqarah: 2:255, 2:282, 2:286
- An-Nisa: 4:176
- Al-Ma'idah: 5:106–107

It also selects up to two ayahs from each 10-word length band (1–10 through 121–130).
The fixed examples count toward their own bands. The source corpus has only one ayah in
81–90 words, none in 91–120, and only one in 121–130, so those bands cannot provide two
distinct examples. The sample manifest records the actual selections and word counts.

```bash
export OPENROUTER_API_KEY="sk-or-..."
./smoke_test.sh
```

The live test uses one ayah per request, `openai/gpt-6-luna` for every length, low reasoning, no premium-model escalation, and no automatic second-pass refinement. It then validates
word coverage, Bangla overlay alignment, source hashes, review flags, chunker diagnostics,
and generated reader data. OpenRouter reports actual token usage and cost in the runner output.

Results are written to `runs/gpt6_luna_smoke/`. To use a different tag, set `TAG` before
running the script. Re-running with the same tag deletes and recreates that generated run
directory.

## 2a. Offline pipeline test (no API key; no model calls)

The offline test replays the bundled Al-Mulk prototype through the flat-chunk pipeline.
It checks parsing, Arabic-word alignment, storage, merge, and QA without calling an LLM.

```bash
./smoke_test_offline.sh
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

# Sample by word-length band, retaining fixed test cases
python3 tools/sample_ayahs.py --include '2:255,2:282,2:286,4:176,5:106-107' --out band_sample.txt

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
