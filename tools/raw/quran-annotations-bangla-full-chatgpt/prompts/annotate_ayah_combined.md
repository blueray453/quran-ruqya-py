# Combined Arabic chunk annotation prompt (English + Bangla)

The default pipeline sends one or more consecutive ayahs per request. `CONVENTIONS.md` is
attached as the system message; this file supplies the user-message template.

## Prompt template

```
Annotate the following Quran ayah(s) according to the attached conventions.
Your only structural task is to find the smallest meaningful Arabic syntactic phrases /
semantic chunks. Do not segment clauses. Return one flat ordered list of chunks per ayah.

For each chunk, return the inclusive source-word positions as `words: [start, end]`
(use `[n]` for a one-word chunk), then provide the English fragment in `en` and Bangla
fragment in `bn`. The numbered words in the input are authoritative. Do not copy, rewrite,
normalize, or reproduce the Arabic text: the pipeline reconstructs exact Arabic from the
source by these positions. Decide all boundaries from Arabic grammar and local meaning. Do
not merge words merely to make a translation fragment more fluent, and do not split a
grammatical unit just to reach a one-word average.

{AYAH_BLOCKS}

Return only the JSON object defined in the conventions' output contract for: {KEYS}.
No prose, no code fences.
```

- `{AYAH_BLOCKS}` contains numbered Arabic words, English and Bangla word glosses, and
  whole-ayah reference translations. The first ayah also receives previous-ayah English
  context for quotation continuity.
- `{KEYS}` is the comma-separated list of requested `surah:ayah` keys.

## Anti-circularity

The model never sees chunker/treebank data, i'rab labels, mined statistics, QA results, or
prior annotations. Those remain post-hoc QA/review signals only.
