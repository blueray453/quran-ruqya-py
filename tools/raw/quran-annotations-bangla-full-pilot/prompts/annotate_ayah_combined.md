# Combined annotation prompt (English + Bangla in one call)

The default pipeline. One LLM call covers a batch of consecutive ayahs (batched by
`tools/run_llm.py`, capped by word count) and returns, per phrase, the English **and**
the Bangla fragment. `CONVENTIONS.md` is sent as the system message (cached); this
template is the user message. `tools/collect.py` then splits the reply into the English
file and the Bangla overlay file, which keep identical spans.

## Prompt template

```
Annotate the following Quran ayah(s) according to the attached conventions. For every
phrase write one English fragment and one Bangla fragment.

{AYAH_BLOCKS}

Return only the JSON object defined in the conventions' output contract for: {KEYS}.
No prose, no code fences.
```

- `{AYAH_BLOCKS}` — one block per ayah (see `ayah_block()` in `tools/ayahlib.py`):
  words with Arabic text + English gloss + Bangla gloss (real word numbers, no
  ayah-end marker), then the English and Bangla whole-ayah reference translations.
  The first ayah of a request also carries the previous ayah's English translation as
  quote-state context.
- `{KEYS}` — e.g. `67:1, 67:2, 67:3`.

## Rules of the pipeline

- The model never sees chunker output, i'rab/treebank labels, mined statistics, QA
  results, or any prior annotation (anti-circularity). The chunker is a post-hoc check
  only (`tools/chunker_report.py`, `qa.py`).
- Output goes through `tools/collect.py` (status `auto`), then `qa.py`, then review.
- The two-pass prompts (`prompts/two-pass/`) are kept as a fallback.
