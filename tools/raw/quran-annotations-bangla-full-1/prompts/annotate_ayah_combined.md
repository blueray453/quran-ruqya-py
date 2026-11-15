# Combined Arabic chunk annotation prompt (English + Bangla)

The default pipeline sends one or more consecutive ayahs per request. `CONVENTIONS.md` is
attached as the system message; this file supplies the user-message template.

## Prompt template

```
Annotate the following Quran ayah(s) according to the attached conventions.
Your only structural task is to find the smallest VALID Arabic syntactic phrases / semantic
chunks. Do not segment clauses. Return one flat ordered list of chunks per ayah.

Before finalizing, silently audit every boundary from the Arabic itself:
- do not strand a conditional particle, conjunction, preposition, auxiliary, or other function
  word when it has no useful independent meaning in that construction;
- do not split a required predicate-argument relationship if doing so makes either fragment
  misleading (for example, a passive predicate separated from its post-verbal subject);
- keep only the minimum words required by the local Arabic dependency; do not turn the whole
  clause into one chunk and do not group words merely for English/Bangla fluency;
- check that each English and Bangla fragment represents all and only the meaning of its own
  source-word positions, with no meaning duplicated in or borrowed from a neighbouring chunk.

Terminology is mandatory: never write God/gods/Lord/lords/lordship/deity/deities in English.
Use Allah for الله, Rabb for رَبّ, and ilah/ilahs for إِلٰه / آلِهَة. In Bangla use আল্লাহ,
রব, and ইলাহ respectively; do not use ঈশ্বর, প্রভু, or খোদা. These rules override any generic
wording in the supplied reference translations.

For each chunk, return the inclusive source-word positions as `words: [start, end]`
(use `[n]` for a one-word chunk), then provide the English fragment in `en` and Bangla
fragment in `bn`. The numbered words in the input are authoritative. `[start, end]` always
includes every word between start and end; never emit a span that skips over a word to reach
a later one, and never re-emit a word that an earlier chunk already covered. The chunks must
tile the ayah exactly once, strictly left to right: chunk k+1 must start at the word
immediately after chunk k ends. Do not copy, rewrite,
normalize, or reproduce the Arabic text: the pipeline reconstructs exact Arabic from the
source by these positions. Decide all boundaries from Arabic grammar and local meaning. Do not merge words merely to
make a translation fragment more fluent, and do not split a grammatical unit just to reach a
one-word average. English and Bangla may reorder words *inside* a chunk where their grammar
requires it, but chunk order and source-word spans must remain exact.

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
