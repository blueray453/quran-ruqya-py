# Formulas and Algorithms: Qur'an Repeated Words and Phrases

This document describes every calculation in the pipeline (`src/normalize.py`, `src/analyze.py`,
`src/compare_representations.py`).

**Notation**

| Symbol | Meaning |
|---|---|
| `T` | total number of real words = **77,432** |
| `v` | verse index (0 to 6,235), verses in reading order |
| `i` | word index inside verse `v` (0-based, after removing empty entries) |
| `w[v][i]` | matching form of word `i` of verse `v` (`normalized` or `exact`) |
| `n` | length of a unit in words (`n >= 1`) |
| `gram(v, i, n)` | the tuple `(w[v][i], ..., w[v][i+n-1])` |
| `pos(v, i)` | global word position = `offset[v] + i`, where `offset[v]` = number of words in all earlier verses |

---

## 1. Normalization

**Input:** each word's text from `indopak-nastaleeq-wbw.json`.
**Goal:** make two spellings of the same word compare equal, ignoring diacritics and decoration.

```
normalize(text):
    out = ""
    for each character ch in text:
        c = MAP.get(ch, ch)                 # unify letter variants
        if 'ء' <= c <= 'ي'  (U+0621..U+064A)  and  c != tatweel (U+0640):
            out += c                        # keep base letters only
        # everything else is dropped: diacritics, pause/waqf marks, small signs,
        # digits, private-use glyphs, zero-width characters
    return out
```

Letter mapping (`MAP`):

| From | To | Reason |
|---|---|---|
| ک ڪ | ك | Indo-Pak kaf forms |
| ی ى ې ے ۍ ٮ | ي | yeh forms (ٮ is a dotless carrier) |
| ٱ أ إ آ | ا | alef and hamza seats |
| ؤ | و | waw seat |
| ئ | ي | yeh seat |
| ہ ھ | ه | heh forms |
| ۃ | ة | ta marbuta |
| ں | ن | noon ghunna |

**Exact form.** A second matching form keeps the diacritics:

```
exact(text) = NFC( MAP applied to text, after deleting pause marks (U+0615, U+06D6..U+06DB),
                   whitespace and zero-width characters, tatweel and private-use glyphs )
```

**Restored words.** Two words (18:19:34 and 73:20:8) are stored in the Nastaleeq file as one private-use
glyph, so `normalize` returns an empty string for them. Any entry whose normalized form is empty
but which has an entry in `word-stem.db` is a real word: its normalized and exact forms are taken from
the database stem text and the entry is flagged `restored_from`. The script asserts that exactly two
entries are restored.

**Real words.** An entry is a real word if its normalized form is non-empty (after restoration).

```
T = (entries in wbw file) - (verse-end markers)
  = 83,668 - 6,236 = 77,432
```

**Cross-check.** For every verse, the wbw words joined with a single space must equal the text in
`indopak-nastaleeq.json`. Result: 0 mismatches.

---

## 2. Finding repeated units

A **unit** is a run of `n >= 1` consecutive words inside one verse that occurs at least twice in the
whole Qur'an. Units never cross a verse boundary. A single word is a unit with `n = 1`.

```
for n = 1, 2, 3, ...:
    counts = empty dictionary: gram -> list of (v, i)
    for each verse v:
        for i = 0 .. len(verse v) - n:
            counts[ gram(v, i, n) ].append( (v, i) )
    repeated[n] = { g : positions   for g, positions in counts   if len(positions) >= 2 }
    if repeated[n] is empty: stop
```

- The loop stops at the first `n` with no repeated gram. For this data the longest repeated unit has
  **n = 24**.
- If a gram of length `n` is repeated, every gram of length `n-1` inside it is repeated too, so
  stopping at the first empty length loses nothing.
- Occurrences may **overlap**. In the word sequence `A A A`, the gram `A A` is counted twice.
- Output size (normalized spelling): 6,095 repeated single words and 25,188 repeated phrases (`n >= 2`).

**Time and memory.** There are about `T` windows for each `n`, so the cost is `O(T x L)` for the maximum
unit length `L`. A dictionary holds the windows for one `n` at a time.

---

## 3. Counts

For a unit `g` with occurrence list `P`:

```
total_count = |P|
```

Total count includes every occurrence, even those inside longer repeated units.

### 3.1 Stand-alone count

An occurrence is **inside a longer unit** if some longer repeated unit contains it. Stand-alone
occurrences are the rest.

**Test (one-word extension).** The occurrence at `(v, i)` of an `n`-word unit is inside a longer unit
exactly when:

```
(v, i)   is the start of a repeated (n+1)-gram     (extended to the right)
   OR
(v, i-1) is the start of a repeated (n+1)-gram     (extended to the left)
```

Implementation: let `S[n+1]` be the set of all start positions `(v, i)` of all occurrences of repeated
`(n+1)`-grams.

```
inside_longer(v, i, n) = ((v, i) in S[n+1])  or  ((v, i-1) in S[n+1])
stand_alone(v, i, n)   = not inside_longer(v, i, n)

stand_alone_count   = number of occurrences with stand_alone = true
inside_longer_count = total_count - stand_alone_count
```

**Why checking only one extra word is enough.** If a longer repeated unit `Q` contains the occurrence,
then at least one `(n+1)`-word window of `Q` also contains it, starting at `i` or at `i-1`. Every window of
a repeated unit is itself repeated (it occurs at least as often as `Q`), so that window is in `S[n+1]`.
The test therefore finds every such case.

**Worked example.** Suppose these units are repeated:

| Unit | Total | Stand-alone | How |
|---|---|---|---|
| A B C D E | 3 | 3 | nothing longer repeats |
| A B C D | 7 | 4 | 3 occurrences are followed by E and fall inside A B C D E |

So `7 = 4 + 3`. A unit whose every occurrence sits inside one longer unit has `stand_alone_count = 0`.

### 3.2 Length fields

```
word_count   = n
char_count   = length of the base-letter spelling of the phrase, spaces included
letter_count = length of the base-letter spelling of the phrase, spaces excluded
```

Character counts are always taken on the base-letter form, even in the exact-spelling run, so that
combining marks are never counted. For example `اِنَّ اللّٰهَ` gives `ان الله`, with `char_count = 7`
and `letter_count = 6`.

### 3.3 Verse lists

```
verses_total       = distinct verses (surah:ayah) of all occurrences, in reading order
verses_stand_alone = distinct verses of the stand-alone occurrences only
```

### 3.4 Ordering and IDs

Units are sorted by `total_count` descending, then `word_count` descending, then matching text
ascending. IDs are assigned in that order: `U00001`, `U00002`, ...

### 3.5 Display text

`phrase_nastaleeq` is the original text of the **first occurrence** of the unit. Zero-width characters
are trimmed from every word, and pause marks (U+0615, U+06D6 to U+06DB) are removed from the end of the
last word.

---

## 4. Coverage

A word position is **covered** if it lies inside at least one occurrence of a unit.

```
covered[pos] = 1  if some unit occurrence (v, i, n) has  offset[v]+i <= pos < offset[v]+i+n
coverage     = sum(covered) / T x 100
```

Covered positions are kept as one flag per position, so overlapping units are never counted twice.

| Set of units (normalized spelling) | Covered words | Coverage |
|---|---|---|
| Words and phrases | 68,837 | **88.90%** |
| Phrases only (`n >= 2`) | 50,057 | 64.65% |

**Once-only words.** The uncovered positions are exactly the words that occur once in the Qur'an:

```
uncovered = T - covered = 77,432 - 68,837 = 8,595   (11.10%)
```

Phrases add nothing to the words-and-phrases figure, because every word inside a repeated phrase is
already a repeated word.

**Per surah.** `surah_coverage(s) = covered words in surah s / total words in surah s x 100`

**Per verse.** `verse_coverage(v) = covered words in verse v / words in verse v`

Verses with coverage = 1: 2,263; at least 0.90: 3,357; at least 0.75: 5,287; at least 0.50: 6,058.

---

## 5. Memorization ranking (greedy set cover)

**Goal.** Order the units so that each step adds as much new coverage as possible for the effort of
learning the unit.

**Definitions** (for a candidate unit `u` with occurrences `P(u)` and word length `n(u)`):

```
positions(u)  = set of all positions covered by occurrences of u
gain(u)       = number of positions in positions(u) not yet covered
cost(u)       = n(u)            (words in the unit)
efficiency(u) = gain(u) / cost(u)
```

**Algorithm (lazy greedy).**

```
covered = all zeros
heap    = max-heap of (efficiency(u), u) for every candidate u, using initial gains
selected = []
while heap is not empty:
    pop the entry with the highest stored efficiency
    recompute gain(u) against the current covered set
    if gain(u) == 0: discard u; continue
    eff = gain(u) / cost(u)
    if heap is not empty and eff < (stored efficiency at the top of the heap):
        push (eff, u) back; continue           # stored value was stale
    select u:
        mark all positions(u) as covered
        cumulative_words_covered  += gain(u)
        cumulative_words_to_learn += cost(u)
        record row
```

**Why lazy evaluation is valid.** A unit's gain can only stay the same or fall as more positions get
covered (diminishing returns). A stored efficiency is therefore always an upper bound on the true value.
If the recomputed efficiency is still at least as high as the best stored value, no other unit can beat it,
and it is safe to select. This returns the same sequence as recomputing every gain at every step, much
faster. The greedy ratio rule is the standard heuristic for weighted set cover (Chvatal, 1979).

**Ties** are broken by candidate order, which is the sort order in section 3.4 (higher total count first).

**Output columns.**

```
new_words_covered         = gain(u) at the time u was selected
cumulative_words_covered  = running sum of new_words_covered
cumulative_pct_of_quran   = cumulative_words_covered / 77,432 x 100   (2 decimals)
cumulative_words_to_learn = running sum of cost(u) over selected units
```

Overlapping selected units are charged separately in `cumulative_words_to_learn`, so this effort figure
slightly overstates the real work.

**Two runs.**

| File | Candidates | Ends at |
|---|---|---|
| `quran-greedy-order-words-and-phrases.csv` | all 6,095 words and 25,188 phrases | 6,001 selected units, 88.90% |
| `quran-greedy-order-phrases-only.csv` | the 25,188 phrases | 7,109 selected phrases, 64.65% |

In the combined run only 87 phrases are selected (the first at rank 1,432), because once their
words are known most phrases add no new coverage.

---

## 6. Alternative definitions of "the same word"

`compare_representations.py` repeats the unit enumeration and the coverage calculation of sections 2 and 4
with different matching labels `w[v][i]`:

| Representation | Label of a word |
|---|---|
| Normalized spelling | base-letter form |
| Exact spelling | diacritized form (NFC) |
| Stem | stem id from `word-stem.db` |
| Lemma | lemma id from `word-lemma.db` |
| Root | root id from `word-root.db` |

A word with no database label keeps its normalized spelling as its label (marked so it cannot collide
with a database id). Everything else is unchanged: units stay inside a verse, and coverage is the share of
positions inside a repeated unit. For each representation the script reports types, once-only types, the
coverage of words and phrases (`1 - once-only tokens / T`), the coverage of phrases only, the number of
repeated phrase types and the longest phrase.

**Over-merging audit.**
```
types_merging_multiple_exact_forms   = normalized types whose tokens have >= 2 different exact spellings
types_mapping_to_multiple_lemmas     = normalized types whose tokens map to >= 2 different lemma ids
```

**Database consistency.** For each verse, the sequence of labels rebuilt from the word-level database is
compared with the text in the matching verse-level database: identical, same number of items but
different items, or different number of items.

---

## 7. Validation checks

The scripts assert, for every unit:

1. `total_count == number of occurrences >= 2`
2. `stand_alone_count + inside_longer_count == total_count`
3. for the first three occurrences, the matching words at the recorded `start` and `end` locations,
   joined by spaces, equal `phrase_normalized`
4. `start` and `end` lie in the same verse
5. both greedy runs end with a cumulative coverage equal to the full coverage of their candidate set

and, in the normalization step, that exactly two words are restored, that there are 6,236 verse-end
markers, and that the word entries reproduce the verse text of all 6,236 verses.

---

## 8. Limitations

- Normalization merges words that differ only in diacritics or hamza, such as مَنْ and مِنْ. Exact spelling
  over-splits equivalents such as مِنْ and مِّنْ. Results under both are reported.
- Overlapping occurrences are counted separately in `total_count`.
- Coverage shows that a word or phrase appears elsewhere. It does not mean a verse can be recited from it.
- Phrases never cross verse boundaries, so repeats spanning the end of one verse and the start of the
  next are not found.
- The lemma, stem and root databases have gaps and internal inconsistencies (see the methods document).
