# Quran Arabic phrase-chunk annotation (Bangla + English)

**Conventions v4.0** — smallest valid Arabic syntactic-semantic chunks, with mandatory
Allah / Rabb / ilah terminology.

This project annotates Quran ayahs as **small, contiguous Arabic syntactic / semantic
chunks**. The goal is not clause segmentation and not word-by-word glossing. A chunk should
be the smallest meaningful unit that preserves its local Arabic grammatical relationship.
The English and Bangla fragments are translations of exactly the same Arabic span. A chunk
must preserve the minimum local grammatical dependency needed for meaning; a small average
word count is not enough. English outputs must use Allah / Rabb / ilah, never God / Lord / deity.
Bangla outputs must use আল্লাহ / রব / ইলাহ, never ঈশ্বর / প্রভু / খোদা.

New annotation shape:

```json
{
  "67:1": [
    {"words": [1], "en": "Blessed is", "bn": "বরকতময়"},
    {"words": [2], "en": "the One who", "bn": "যিনি"}
  ]
}
```

The model returns one-based source-word positions, not copied Arabic text. The pipeline
reconstructs the exact Arabic from the pinned source, checks full word coverage, stores flat
`chunks[]`, and creates separate English and Bangla files. Legacy `clauses[].phrases[]`
files remain readable by QA and build tools.

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

It also includes **all 30 ayahs of Surah Al-Mulk** (the complete bundled prototype/reference
surah) and selects at least two ayahs from each 10-word length band (1–10 through 121–130)
where enough ayahs exist. All fixed ayahs and the Al-Mulk ayahs count toward their bands. The source corpus has only one ayah in
81–90 words, none in 91–120, and only one in 121–130, so those bands cannot provide two
distinct examples. The sample manifest records the actual selections and word counts.

```bash
export OPENROUTER_API_KEY="sk-or-..."
./smoke_test.sh
```

The live test uses one ayah per request, `openai/gpt-6-luna` for every length, reasoning off,
no premium-model escalation, and no automatic granularity refinement. The model returns word
positions instead of Arabic copies. If a Bangla fragment is blank, the runner requests only
that missing translation while keeping all chunk boundaries fixed. It then validates word
coverage, mandatory Allah/Rabb/ilah terminology, Bangla overlay alignment, source hashes,
review candidates, chunker diagnostics, and generated reader data. OpenRouter reports actual
token usage and cost in the runner output. Full attempts and retry resolutions are archived.

Results are written to `runs/gpt6_luna_v6_smoke/`. To use a different tag, set `TAG` before
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
2. **Segment** — model returns a flat ordered list of `{words, en, bn}` chunk objects, with
   one-based inclusive word-position ranges.
3. **Validate** — the pipeline verifies exact word coverage, order, non-empty translations,
   and script constraints. Arabic is reconstructed from the source, not copied from the model.
4. **Refine/escalate** — only phrase-chunk granularity and meaning-preservation checks are
   used. No clause-size metric or clause boundary is optimized.
5. **Merge** — `tools/collect.py` creates a flat English `chunks[]` file and a separate
   Bangla overlay with identical chunk spans.
6. **QA/review** — `qa.py` verifies tiling, source integrity, Bangla scripts, mandatory
   terminology and overlay identity. `tools/review_flags.py` uses conservative syntactic
   boundary hints; the former word-overlap heuristic is retired because it produced false
   positives for context-dependent fragments. Chunker reports remain post-hoc diagnostics.
7. **Build** — `build.py` joins Arabic text, word glosses, translations, and recitation
   windows into reader JSON views.

## 5. Useful commands

```bash
# Count ayahs by Arabic word length and chunker coverage
python3 ayah_length_counter.py

# Inspect a prompt
python3 tools/run_llm.py --ayahs 2:282 --tag preview --dry-run

# Sample by word-length band, retaining fixed test cases
python3 tools/sample_ayahs.py --include '67,2:255,2:282,2:286,4:176,5:106-107' --out band_sample.txt

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

## 7. Semantic / syntactic second-pass audit (optional paid calls)

After a smoke run, you can request an independent review of the fixed chunk spans:

```bash
python3 tools/semantic_audit.py \
  --annotations-dir runs/gpt6_luna_v6_smoke/annotations \
  --out-dir runs/gpt6_luna_v6_smoke/semantic_audit \
  --model openai/gpt-6-luna
```

To audit only known difficult ayahs:

```bash
python3 tools/semantic_audit.py \
  --annotations-dir runs/gpt6_luna_v6_smoke/annotations \
  --out-dir runs/gpt6_luna_v6_smoke/semantic_audit \
  --ayahs '2:196,2:282,4:12,4:176,33:53,67:7-11,67:16,67:27-30'
```

This audit does not change annotations. It returns high/medium/low review candidates for
meaning omission, meaning borrowing/duplication, syntactic dependency splits, translation
errors, Bangla alignment and terminology. Full prompts and raw audit responses are archived.
It is a second opinion, not an infallible gold-standard validator.

## 8. Exporting exact Arabic source traces

Every validated raw result embeds its source words. For merged annotations from any run, you
can also create line-oriented source/chunk evidence:

```bash
python3 tools/export_evidence.py \
  --annotations-dir runs/gpt6_luna_v6_smoke/annotations \
  --out-dir runs/gpt6_luna_v6_smoke/evidence
```

It writes exact numbered Arabic source words, English/Bangla word glosses, reference translations,
and final chunk-to-source alignments. A merged annotation is not the same thing as the raw
model response; original model text can only be preserved at generation time in `attempts/`.

## 9. Data and source integrity

Files under `sources/` are read-only and pinned in `sources.lock.yaml`. `qa.py` checks their
SHA-256 hashes. The keyed text includes an ayah-end marker as the final key; annotations and
audio positions use only real words. The three known-missing word-by-word gloss keys remain
handled by QA as before.

## 10. Legacy compatibility

Bundled legacy `clauses[].phrases[]` annotations can still be read by `qa.py`, `build.py`,
`tools/review_flags.py`, and `tools/chunker_report.py`. New work should use `chunks[]` only.
`tools/conform_chunker.py` is retired because treebank boundaries must not be used to force
chunk boundaries.
