# Repeated Words and Phrases in the Qur'anic Text

Finds every word and multi-word phrase that occurs at least twice in the Qur'an, counts how often
each one occurs on its own, measures how much of the text these units cover, and tests how the
answer changes under different definitions of "the same word" (normalized spelling, exact
spelling, stem, lemma, root).

## Contents
    README.md                      this file
    requirements.txt               dependencies (none beyond the Python standard library)
    run_all.sh                     runs the full pipeline
    src/normalize.py               step 1: normalize the word-by-word text
    src/analyze.py                 step 2: repeated units, counts, coverage, memorization ranking
    src/compare_representations.py step 3: lemma / stem / root comparison and database audit
    data/                          input files exactly as supplied (2 text files, 6 SQLite databases)
    results/                       all outputs (already generated)
    results/exact-diacritics/      the same analysis matching on the diacritized spelling
    docs/formulas-and-algorithms.md    every formula and algorithm
    docs/methods-and-results-summary.md  methods and results in academic style

## Run
    ./run_all.sh
Needs Python 3.9+ and no third-party packages. Output is deterministic: re-running reproduces
`results/` exactly.

## Inputs (data/)
- `indopak-nastaleeq-wbw.json`: word-by-word text, 83,668 entries keyed by `surah:ayah:word`
  (6,236 verse-end markers + 77,432 words).
- `indopak-nastaleeq.json`: verse text, used only to cross-check the word file (0 mismatches).
- `word-{stem,lemma,root}.db`, `ayah-{stem,lemma,root}.db`: morphological databases. Only
  `word-stem.db` is used by the main analysis (to restore two words, see below); all six are used by
  step 3.

Data note: two words (18:19:34 and 73:20:8) are stored in the Nastaleeq file as a single private-use
glyph instead of letters. `normalize.py` restores them from `word-stem.db` and flags them
(`restored_from`). The word count is therefore **77,432**.

## Method in brief
1. **Normalize** each word. `normalized` keeps base Arabic letters only (no diacritics, pause marks or
   small signs; letter variants unified). `exact` keeps the diacritics.
2. **Units**: every run of n >= 1 consecutive words inside one verse (never across a verse
   boundary) that occurs at least twice. A single word is a unit with word_count = 1.
3. **Total count** = every occurrence (overlaps included). **Stand-alone count** = occurrences not part
   of a longer repeated unit. total = stand_alone + inside_longer.
4. **Coverage** = share of the 77,432 word positions inside at least one unit.
5. **Memorization order** = greedy set cover: repeatedly take the unit that covers the most
   still-uncovered words per word of the unit. Words that occur only once are not included.
6. **Sensitivity**: repeat the coverage analysis with exact spelling, stems, lemmas and roots.

## Results (results/)
| File | Contents |
|---|---|
| `quran-phrases-annotation.json` | all units: counts, verse lists, exact word ranges per occurrence (with stand-alone flag) |
| `quran-phrases.csv` | same data as a spreadsheet (UTF-8 with BOM) |
| `quran-greedy-order-words-and-phrases.csv` | memorization order, words + phrases |
| `quran-greedy-order-phrases-only.csv` | memorization order, phrases of 2+ words only |
| `quran-coverage-by-surah.csv` | coverage per surah, with and without single words |
| `summary.json` | every headline number quoted in the documentation |
| `indopak-nastaleeq-wbw-normalized.json` | normalized and exact forms the matching runs on |
| `representation-comparison.csv` | coverage under six definitions of "the same word" |
| `db-audit.json` | over-merging audit and database consistency checks |
| `exact-diacritics/` | the same files, matching on the diacritized spelling |

Annotation fields: `id, type (word|phrase), phrase_normalized, phrase_nastaleeq, word_count, char_count`
(base letters, spaces included)`, letter_count, total_count, stand_alone_count, inside_longer_count,
verses_total, verses_stand_alone, occurrences[{start, end, stand_alone}]`. In `exact-diacritics/` the
field `phrase_normalized` holds the diacritized matching form.

## Key numbers
- 6,095 repeated single words and 25,188 repeated phrases (2 to 24 words);
  16,598 phrases never stand alone.
- Words + phrases cover **88.90%** of the 77,432 words; phrases of 2+ words alone cover
  64.65%. The remaining 11.10% are 8,595 words that occur only once in the Qur'an.
- With exact (diacritized) spelling the figures are **83.75%** and 59.15%, so the
  normalized figures are the permissive end of a range of 83.75-88.90%.
- Lemma and root definitions give higher coverage (see `representation-comparison.csv`) but answer a
  different, semantic question and rely on databases with gaps and inconsistencies.

## Caveats
- Normalization merges words that differ only in diacritics or hamza (for example مَنْ and مِنْ);
  exact spelling over-splits equivalents such as مِنْ and مِّنْ. The truth lies between them.
- Coverage means a word or phrase has appeared elsewhere, not that a verse can be recited.
- Once single words are included, phrases add no extra coverage, because every word inside a repeated
  phrase is already a repeated word.
- Units never cross a verse boundary.
