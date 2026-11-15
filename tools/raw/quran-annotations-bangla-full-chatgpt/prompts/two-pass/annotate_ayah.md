# English segmentation pass (flat Arabic chunks)

The segmentation pass decides the Arabic chunk boundaries once. Its output is a flat ordered
list of chunk objects for each ayah, with `ar` and `en` fields. It does not create clauses.

```
Annotate this Quran ayah according to CONVENTIONS.md. Find the smallest meaningful Arabic
syntactic phrases / semantic chunks. Return a flat ordered list, not nested clauses.

Words (position, Arabic text, English word gloss):
{WORDS_BLOCK}

Whole-ayah English reference translation:
"{AYAH_TRANSLATION}"

Return only the JSON object for ayah {SURAH}:{AYAH}. Each item must contain exact `ar` and
non-empty `en` fields. No prose or code fences.
```
