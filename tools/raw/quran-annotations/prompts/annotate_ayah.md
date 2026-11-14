# Per-ayah annotation prompt (template)

One LLM call per ayah. That is the only LLM step in the whole pipeline. Fill the two
blocks, attach `CONVENTIONS.md` to every request, and send the message below. Merge
the reply with `tools/collect.py`, then run `qa.py`.

---

## Prompt template

```
Annotate this Quran ayah according to the attached conventions.

Words (position, Arabic text, word-by-word gloss):

{WORDS_BLOCK}

Whole-ayah reference translation:

"{AYAH_TRANSLATION}"

Return only the JSON object defined in the conventions' output contract for ayah
{SURAH}:{AYAH}. No prose, no code fences.
```

- `{WORDS_BLOCK}` — one line per word: `position Arabic-text — wbw-gloss`, taken from
  the text and wbw sources (real word numbers; do not include the ayah-end marker).
- `{AYAH_TRANSLATION}` — the whole-ayah English reference translation.

---

## Rules of the pipeline

- The model never sees: clause or phrase labels from any linguistic layer, any prior
  or parallel annotation, chunker output, i'rab groups, mined statistics, or QA
  results. (Anti-circularity rule — segmentation decisions come from the words, the
  glosses, the reference translation and the conventions only.)
- `CONVENTIONS.md` is the only rules document in the annotation package. There is no
  glossary in the package; word-by-word glosses already arrive per word.
- Output goes through `tools/collect.py` into `annotations/surah-NNN.json`
  (`status: auto`), then `qa.py`, then human review flips statuses.
