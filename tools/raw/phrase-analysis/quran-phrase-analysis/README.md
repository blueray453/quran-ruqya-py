# Quran repeated words and phrases

Finds every word and multi-word phrase that occurs at least twice in the Quran, counts
how often each one stands alone, and measures how much of the Quran those units cover.

## Layout
    data/      input files (Indo-Pak Nastaleeq text)
    src/       normalize.py (step 1), analyze.py (step 2)
    results/   all outputs (already generated)
    run_all.sh runs both steps

## Run
    ./run_all.sh          # or run the two scripts in src/ by hand
Needs Python 3.9+ and no third-party packages (see requirements.txt).
Output is deterministic: re-running reproduces `results/` exactly.

## Inputs (data/)
- `indopak-nastaleeq-wbw.json`  word-by-word text, 83,668 entries keyed by `surah:ayah:word`.
  It includes one verse-end marker per verse (6,236) and two stray glyph entries (18:19:34, 73:20:8).
- `indopak-nastaleeq.json`  verse text, used only to cross-check the word file.

Real words: 83,668 - 6,238 = **77,430**.

## Method
1. **Normalize** each word: keep base Arabic letters only (drops diacritics, pause marks, small signs,
   private-use glyphs) and unify variants (Indo-Pak kaf/yeh/heh, alef and hamza seats).
2. **Units**: every run of n >= 1 consecutive words inside one verse (never across a verse boundary)
   that occurs at least twice. Single words are units with word_count = 1.
3. **Total count**: every occurrence, overlapping ones included.
   **Stand-alone count**: occurrences that are not part of a longer repeated unit.
   total = stand_alone + inside_longer.
4. **Coverage**: share of the 77,430 word positions inside at least one unit (a set of positions,
   so overlapping units are never double counted).
5. **Memorization order**: greedy - repeatedly take the unit that covers the most still-uncovered
   words per word of the unit. Words that occur only once in the Quran are not included.

## Results (results/)
| File | Contents |
|---|---|
| `quran-phrases-annotation.json` | all 31,283 units: counts, verse lists, exact word ranges per occurrence (with stand-alone flag) |
| `quran-phrases.csv` | same data as a spreadsheet (UTF-8 with BOM) |
| `indopak-nastaleeq-wbw-normalized.json` | normalized word file the matching runs on |
| `quran-coverage-by-surah.csv` | coverage per surah, with and without single words |
| `quran-greedy-order-words-and-phrases.csv` | memorization order, words + phrases |
| `quran-greedy-order-phrases-only.csv` | memorization order, phrases of 2+ words only |

Annotation fields: `id, type (word|phrase), phrase_normalized, phrase_nastaleeq, word_count, char_count
(normalized, spaces included), letter_count, total_count, stand_alone_count, inside_longer_count,
verses_total, verses_stand_alone, occurrences[{start, end, stand_alone}]`.

## Key numbers
- 6,095 repeated single words; 25,188 repeated phrases (2 to 24 words); 16,598 phrases never stand alone.
- Words + phrases cover **88.90%** of the 77,430 words; phrases of 2+ words alone cover 64.65%.
  The other 11.1% are 8,593 words that occur only once in the Quran.
- Learning the 1,000 best units (1,000 words) covers 66.58%; 3,000 units covers 80.03%.

## Caveats
- Normalization merges words that differ only in diacritics or hamza (e.g. مَنْ / مِنْ), which raises
  coverage slightly.
- Coverage means a word or phrase has appeared elsewhere, not that the verse can be recited.
- Once single words are included, phrases add no extra coverage (each word of a repeated phrase is
  already a repeated word), so the combined ranking is mostly a word-frequency ranking.
