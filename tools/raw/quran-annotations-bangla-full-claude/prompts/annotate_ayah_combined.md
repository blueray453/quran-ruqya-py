# Combined Arabic chunk annotation prompt (English + Bangla)

The default pipeline sends one or more consecutive ayahs per request. `CONVENTIONS.md` is attached as the system message; this file supplies the user-message template. The attached conventions are authoritative if any wording here appears inconsistent with them.

## Prompt template

```text
Annotate the following Quran ayah(s) according to the attached conventions.

Your primary and most important task is to find the smallest VALID Arabic syntactic phrases / semantic chunks. Segmentation quality is the highest priority. Decide every boundary from Arabic syntax and local meaning alone. Do not segment clauses, subclauses, or whole sentences. Return one flat ordered list of chunks per ayah.

First determine the Arabic chunks. Only after the boundaries are decided, translate each fixed span into English and Bangla. The translations must represent all and only the meaning of their own source-word positions. They only need to be understandable and make reasonable sense when the fragments are joined in their original order. They do not need to be elegant, polished, or fully fluent.

Do not sacrifice a smaller valid Arabic segmentation to make English or Bangla smoother. Never combine or enlarge Arabic spans merely for translation fluency. Equally, do not split a required Arabic grammatical or semantic unit just to make chunks shorter or to reach a one-word average. Choose the smallest span that preserves the necessary local Arabic relationship.

Before finalizing, silently audit every boundary from the Arabic itself:
- Prefer one Arabic word per chunk when that word has an identifiable meaning or syntactic function in context.
- Keep words together only when separating them would break an important local grammatical dependency, fixed expression, or semantic unit. Use the minimum number of words needed to preserve that relationship.
- Do not strand a conditional particle, conjunction, preposition, auxiliary, or other function word when it has no useful independent meaning in that construction. Keep it with the smallest adjacent Arabic span needed to express its function; do not expand the span beyond what the Arabic relationship requires.
- Do not split a required predicate-argument relationship if doing so makes either resulting fragment misleading (for example, a passive predicate separated from its post-verbal subject).
- Do not automatically combine every iḍāfa, verb-object pair, adjective-noun pair, or preposition-noun pair. Split them when their parts can remain meaningful and grammatically interpretable as separate chunks.
- Do not turn an entire clause into one chunk when smaller valid local chunks are possible.
- Keep every chunk contiguous and preserve the original Arabic word order. Do not skip, repeat, overlap, or reorder source words.
- Check that each English and Bangla fragment represents all and only the meaning of its own source-word positions. Do not duplicate meaning, borrow meaning from a neighbouring chunk, or leave any source meaning untranslated.
- Do not enlarge a chunk to make its English or Bangla fragment read more naturally. A fragment may be elliptical, context-dependent, or somewhat awkward on its own, provided it faithfully represents its assigned Arabic span and remains understandable in sequence.

Terminology is mandatory: never write God/gods/Lord/lords/lordship/deity/deities in English. Use Allah for الله, Rabb for رَبّ, and ilah/ilahs for إِلٰه / آلِهَة. For الرَّحْمَٰن, use Ar-Rahman. In Bangla use আল্লাহ, রব, ইলাহ, and আর-রহমান respectively; do not use ঈশ্বর, প্রভু, or খোদা. These rules override any generic wording in the supplied reference translations.

For each chunk, return the inclusive source-word positions in `words`: use `[n]` for a one-word chunk or `[start, end]` for a contiguous inclusive range. Then provide the English fragment in `en` and the Bangla fragment in `bn`. The numbered words in the input are authoritative. `[start, end]` always includes every word between start and end; never emit a span that skips a word to reach a later one, and never re-emit a word that an earlier chunk already covered. The chunks must tile the ayah exactly once, strictly left to right: chunk k+1 must start at the word immediately after chunk k ends.

Do not copy, rewrite, normalize, or reproduce the Arabic text: the pipeline reconstructs the exact Arabic from the source using these positions. English and Bangla may adjust word order inside a chunk where their grammar requires it, but chunk boundaries and chunk order must remain unchanged.

{AYAH_BLOCKS}

Return only the JSON object defined in the conventions' output contract for: {KEYS}.
No prose, no code fences, no grammatical-unit labels, and no separate full-ayah smooth-flow translations.
```

- `{AYAH_BLOCKS}` contains numbered Arabic words, English and Bangla word glosses, and whole-ayah reference translations. Do not provide previous-ayah context for quotation continuity; quotation marks and quotation-continuity handling are not part of this annotation task.
- `{KEYS}` is the comma-separated list of requested `surah:ayah` keys.

## Anti-circularity

The model never sees chunker/treebank data, iʿrāb labels, mined statistics, QA results, or prior annotations. Those remain post-hoc QA/review signals only. Do not use them to decide or revise chunk boundaries.
