# Per-ayah Bangla gloss prompt (template)

Second pass; runs only after the ayah's English annotation exists and passed
`qa.py`. One LLM call per ayah — same discipline as the English pass, but the
segmentation is **given, never re-decided**: Bangla is a separate overlay file
(`annotations/bn/surah-NNN.json`), and this pass only fills one fragment per
existing phrase. Fill the three blocks, attach `CONVENTIONS.md` (its "Bangla
overlay pass" section governs style), and send the message below. Merge the reply
with `tools/collect.py --lang bn`, then run `qa.py`.

---

## Prompt template

```
You are adding a Bangla overlay to an already-segmented Quran ayah, following the
attached conventions (section "Bangla overlay pass"). Do not change the
segmentation: return exactly one Bangla fragment per phrase, in the given order.

Words (position, Arabic text, word-by-word gloss):

{WORDS_BLOCK}

Given phrase segmentation (word positions — English fragment), in Arabic order:

{SEGMENTATION_BLOCK}

Whole-ayah reference translation (Bangla):

"{BN_TRANSLATION}"

Return only the JSON object defined in the conventions' Bangla output contract
for ayah {SURAH}:{AYAH}. No prose, no code fences.
```

- `{WORDS_BLOCK}` — one line per word: `position Arabic-text — wbw-gloss`, from
  the text and wbw sources (real word numbers; no ayah-end marker).
- `{SEGMENTATION_BLOCK}` — one line per phrase, in phrase order:
  `words 1-2 — "He in whose hand"` (word positions from the English annotation,
  en fragment quoted for sense).
- `{BN_TRANSLATION}` — the whole-ayah Bangla reference translation, taken from
  the bn translation source (`sources/translation/quran-bn-*.json`). It is a
  sense reference only — never a source of segmentation or of fragment text to
  copy. Omit the whole block if the surah is not covered by the translation
  source yet.

---

## Rules of the pipeline

- The model never sees: linguistic labels, chunker output, i'rab groups, mined
  statistics, or QA results (anti-circularity holds for content). The phrase
  segmentation itself is an input of this pass because it was decided in the
  English pass — the bn pass is a gloss pass, not a segmentation pass.
- Count is sacred: one fragment per phrase, in order. `tools/collect.py --lang bn`
  aborts on any mismatch; the spans are copied from the English file, so the
  overlay cannot drift structurally.
- Output goes through `tools/collect.py --lang bn` into
  `annotations/bn/surah-NNN.json` (`status: auto`), then `qa.py` (script checks:
  Bengali script required, Arabic script forbidden), then human review flips
  statuses.
