# Quran Arabic phrase-chunk annotation (English + Bangla)

Each ayah is split into small contiguous Arabic chunks. Every chunk has its Arabic word
positions, an English fragment and a Bangla fragment. Rules: `CONVENTIONS.md` (this is the
system prompt sent to the model). Output shape: `annotations/SCHEMA.md`.

```json
"67:1": [{"words": [1], "en": "Blessed is", "bn": "বরকতময়"}, {"words": [2], "en": "the One who", "bn": "যিনি"}]
```

## Files

| File | Purpose |
| --- | --- |
| `annotate.py` | the whole annotation pipeline (one file, stdlib only) |
| `smoke_test.sh` | sample 45 ayahs -> annotate -> QA |
| `qa.py` | checks word coverage, Bangla overlay, terminology, source integrity |
| `build.py` | optional: builds reader data under `data/` from annotations |
| `tools/sample_ayahs.py` | builds the stratified sample used by the smoke test |
| `CONVENTIONS.md`, `prompts/` | instructions sent to the model |
| `sources/`, `sources.lock.yaml` | read-only inputs, pinned by sha256 |
| `annotations/`, `data/` | the bundled Al-Mulk (67) reference sample |
| `runs/<tag>/` | everything one run produces |

## Run

```bash
export OPENROUTER_API_KEY=sk-or-...           # default model: anthropic/claude-haiku-5.5
./smoke_test.sh                               # sample run, ~$0.03
python3 annotate.py --tag full --all --workers 4      # whole Quran (~$2)
python3 annotate.py --tag x --ayahs "2:255,2:282-286" # or --surah 67
python3 qa.py --annotations-dir runs/full/annotations --no-baseline
```

## What `annotate.py` does

For each ayah with no `runs/<tag>/raw/SSS-AAA.json`: build the prompt, call the model (thinking
off), parse its JSON, validate. Valid -> write the raw file. Invalid -> up to 2 retries (the error
and the exact skipped/doubled words are fed back, low thinking). Still invalid -> **stop**, write
`runs/<tag>/STOPPED.md` and the full prompts/replies to `runs/<tag>/failures/`, exit 1.

**Resume:** run the same command again. Finished ayahs are skipped.

Outputs per run: `raw/` (one file per ayah), `annotations/surah-NNN.json` (English),
`annotations/bn/surah-NNN.json` (Bangla), `retries.jsonl` (ayahs that needed a retry),
`STOPPED.md` (only after a stop).

The code checks structure and terminology only (every word covered once and in order; Allah /
Rabb / ilah, never God / Lord / ঈশ্বর / প্রভু / খোদা). Chunk quality is for human review.
The terminology rule lives in `annotate.py` (`terminology_flags`); `qa.py` reuses it.
