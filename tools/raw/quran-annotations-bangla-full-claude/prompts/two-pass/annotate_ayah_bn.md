# Bangla overlay pass (gloss only; segmentation is fixed)

This pass runs only after an English chunk annotation exists. It must not change boundaries.
Return one Bangla fragment for every existing chunk, in exactly the same order.

```
Add Bangla fragments to this already-segmented Quran ayah, following the Bangla rules in
CONVENTIONS.md. Do not re-segment, merge, split, or reorder chunks.

Words (position, Arabic text, Bangla word gloss):
{WORDS_BLOCK}

Existing chunk spans and English fragments, in Arabic order:
{SEGMENTATION_BLOCK}

Whole-ayah Bangla reference translation:
"{BN_TRANSLATION}"

Return only a JSON object for ayah {SURAH}:{AYAH}, with one Bangla string per existing chunk.
No prose or code fences.
```
