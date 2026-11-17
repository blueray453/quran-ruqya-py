# Repeated Lexical Units in the Qur'anic Text: Methods and Descriptive Results

## Abstract

We conducted a complete-census, descriptive analysis of lexical repetition in the Qur'anic text using a
word-aligned Indo-Pak Nastaleeq digitization (N = 77,432 word tokens in 6,236 verses). After orthographic
normalization, we enumerated all word-level and multi-word units (n-grams, n >= 1) that occur at least twice
within a single verse context, distinguished each unit's total frequency from its *stand-alone* frequency
(occurrences not subsumed by a longer repeated unit), and quantified the proportion of the corpus covered by
these units. A greedy cost-benefit ordering was used to estimate how much of the text is covered as a function
of the number of units learned. Repeated units cover 88.90% of word tokens under normalized
spelling and 83.75% under exact diacritized spelling; repeated multi-word phrases alone cover
64.65% and 59.15% respectively. The remaining tokens are hapax legomena (word forms that occur
exactly once). A sensitivity analysis replaced the definition of "the same word" by database stems, lemmas and
roots, and audited the databases for consistency.

## 1. Data

The analysis used a word-by-word file (83,668 entries, each keyed by surah, ayah and word index), a verse-level
file (6,236 verses) and six morphological databases (stem, lemma and root, each at word and verse level). The
word file contains one verse-end marker per verse (6,236), none of which is lexical. Two lexical words
(18:19:34 and 73:20:8) are stored in the file as single private-use glyphs; their forms were restored from the
stem database. Excluding the markers leaves **N = 77,432 word tokens**. As an integrity check, the word entries of
every verse were concatenated and compared with the verse-level text; all 6,236 verses matched exactly.

Because the data are the entire text rather than a sample, the study is a census. No inferential procedures
(hypothesis tests, confidence intervals) are involved, and all quantities reported are descriptive population
values.

## 2. Preprocessing

Each token was mapped to two orthographic forms. The *normalized* form retains only base Arabic letters
(U+0621-U+064A, excluding tatweel), which removes diacritics, pause (waqf) marks, small Qur'anic annotation
signs and private-use glyphs, and unifies orthographic variants: Indo-Pak forms of kaf, yeh and heh to their
standard counterparts, and alef/hamza seats. The *exact* form retains the diacritics, removing only pause
marks, zero-width characters, tatweel and private-use glyphs, with canonical (NFC) ordering of marks. The
original text and the original `surah:ayah:word` index are retained so that every result can be traced to the
source.

The choice of form defines the equivalence classes of the analysis. Normalization treats tokens that differ only
in vocalization or hamza carrier (for example مَنْ and مِنْ) as the same type and therefore increases measured
repetition; exact spelling distinguishes them but also separates orthographic variants of one word (for example
مِنْ and مِّنْ). The two forms are reported as the permissive and strict ends of a range.

## 3. Definitions

Let the corpus be a sequence of verses, each a sequence of tokens in the chosen form.

- **Unit.** A contiguous sequence of n >= 1 tokens contained in a single verse. Units never span a verse
  boundary. A unit of length 1 is a word; a unit of length n >= 2 is a phrase.
- **Repeated unit.** A distinct unit (type) whose total frequency satisfies f >= 2 in the corpus.
- **Total frequency** f(u): the number of positions at which unit u occurs, with overlapping occurrences counted
  separately.
- **Stand-alone frequency** s(u): the number of occurrences of u that are not contained in any longer repeated
  unit. Hence f(u) = s(u) + c(u), where c(u) is the number of occurrences contained in a longer repeated unit.
- **Coverage** of a set of units U: the proportion of the N token positions that lie inside at least one
  occurrence of a unit in U.

```
coverage(U) = |{ positions covered by some occurrence of some u in U }| / N
```

Coverage is computed on the set of positions, so overlapping units are not double counted and the statistic is
bounded by 1.

## 4. Procedures

### 4.1 Enumeration of repeated units

For n = 1, 2, 3, ... all n-token windows within verses were tabulated in a hash map keyed by the token tuple, and
types with f >= 2 were retained. Enumeration terminated at the first n for which no type was repeated (n =
24 is the longest repeated unit). Because every sub-window of a repeated unit is itself repeated, this
termination rule is exact. Complexity is O(N L), where L is the maximum unit length.

### 4.2 Stand-alone frequency

An occurrence of a unit at start position (v, i) with length n is contained in a longer repeated unit if and
only if a repeated (n+1)-gram begins at (v, i) or at (v, i-1). This one-token extension test is sufficient: any
longer repeated unit containing the occurrence contains an (n+1)-token window that also contains it, and that
window is repeated because its frequency is at least that of the enclosing unit. Stand-alone frequency follows as
s(u) = f(u) - c(u).

### 4.3 Learning-order analysis (greedy cost-benefit ordering)

To describe how coverage accumulates as units are learned, we treated unit selection as a weighted set-cover
problem. For each candidate unit u, with position set P(u) and cost n(u) (its length in tokens):

```
gain(u | S)  = |P(u) \ (union of P(v) for v in S)|       (newly covered positions)
efficiency   = gain(u | S) / n(u)
```

At each step the unit with the largest efficiency was added to the selected set S, until no candidate contributed
any new position. Gains are non-increasing as S grows (diminishing returns), which justifies lazy re-evaluation
with a priority queue; the procedure then returns exactly the same sequence as full recomputation. The greedy
ratio rule is the standard heuristic for weighted set cover and has a logarithmic worst-case approximation
guarantee (Chvatal, 1979). The reported effort (cumulative tokens to learn) charges overlapping units separately
and therefore slightly overstates the true effort. Two orderings were produced: one over all repeated units, and
one restricted to phrases (n >= 2).

### 4.4 Sensitivity to the definition of "the same word"

The enumeration and coverage computations were repeated with the token label replaced by (i) the diacritized
spelling, (ii) the stem identifier, (iii) the lemma identifier and (iv) the root identifier from the
morphological databases. Tokens without a database label retained their normalized spelling. The databases were
audited by (a) counting normalized types whose tokens carry more than one exact spelling or more than one lemma,
(b) counting tokens without labels, and (c) comparing, verse by verse, the label sequence rebuilt from the
word-level database with the corresponding verse-level database.

### 4.5 Verification

Programmatic assertions confirmed, for every unit, that f(u) equals the number of recorded occurrences, that
s(u) + c(u) = f(u), that recorded start and end locations lie in one verse and reproduce the unit's text, and that
each greedy procedure's final coverage equals the coverage of its full candidate set. The pipeline uses only the
Python standard library (Python 3.12) and is deterministic; a clean rerun reproduces all output files byte for
byte.

## 5. Results

### 5.1 Inventory of repeated units (normalized spelling)

| Quantity | Value |
|---|---|
| Word tokens (N) | 77,432 |
| Distinct normalized word types | 14,690 |
| Word types occurring once (hapax legomena) | 8,595 (58.5% of types; 11.1% of tokens) |
| Repeated word types (f >= 2) | 6,095 |
| Repeated phrase types (2 <= n <= 24) | 25,188 |
| Phrase types with s(u) = 0 (never stand alone) | 16,598 (65.9% of phrase types) |

The token mass is concentrated in frequent forms: word types occurring at least 20 times account for 57.9%
of tokens, types occurring 5-19 times for 17.7%, and types occurring 2-4 times for 13.2%. This is the
heavy-tailed rank-frequency profile characteristic of natural-language text; no formal distributional fit (for
example to Zipf's law) was performed.

### 5.2 Coverage

| Set of units | Tokens covered | Coverage |
|---|---|---|
| Repeated words and phrases | 68,837 | **88.90%** |
| Repeated phrases only (n >= 2) | 50,057 | **64.65%** |
| Not covered (hapax legomena) | 8,595 | 11.10% |

When single words are admitted, phrases contribute no additional coverage, since every token inside a repeated
phrase is itself a repeated word. The uncovered tokens are exactly the hapax legomena.

Verse-level coverage (proportion of a verse's tokens covered by repeated units): 2,263 of 6,236 verses
(36.3%) are fully covered; 3,357 (53.8%) have coverage >= 0.90; 5,287 (84.8%) have coverage >=
0.75; and 6,058 (97.1%) have coverage >= 0.50. Among surahs with at least 20 tokens, coverage was highest
for Surah 97 (100%), then Surahs 98 and 45 (94.7% each) and Surah 10 (93.9%), and lowest for Surah 93 (62.5%), Surah 100 (65.0%), Surah 105 (65.2%) and Surah 86 (65.6%). Full per-surah values are provided in the results files.

### 5.3 Coverage as a function of units learned

Greedy ordering over all repeated units (words and phrases):

| Units selected | Tokens to learn | Coverage |
|---|---|---|
| 10 | 10 | 16.07% |
| 50 | 50 | 30.01% |
| 100 | 100 | 38.12% |
| 250 | 250 | 49.51% |
| 500 | 500 | 58.22% |
| 1,000 | 1,000 | 66.58% |
| 2,000 | 2,004 | 74.98% |
| 3,000 | 3,023 | 80.02% |
| 5,000 | 5,094 | 86.31% |
| 6,001 | 6,095 | 88.90% |

The curve is concave: the first 100 units cover 38.12% of tokens, whereas the last 3,000 units add under 9
percentage points. Only 87 of the 6,001 selected units are phrases, the first appearing at rank
1,432, because once their component words are selected most phrases add no new positions. The ordering
restricted to phrases accumulates more slowly:

| Phrases selected | Tokens to learn | Coverage |
|---|---|---|
| 10 | 20 | 3.41% |
| 100 | 200 | 12.11% |
| 1,000 | 2,019 | 32.78% |
| 2,500 | 5,113 | 46.14% |
| 5,000 | 10,594 | 59.60% |
| 7,109 | 14,854 | 64.65% |

### 5.4 Sensitivity to the definition of "the same word"

| Representation | Tokens | Distinct types | Once-only types | Words + phrases covered | Phrases only covered |
|---|---|---|---|---|---|
| Normalized spelling, before restoring the 2 glyph words | 77,430 | 14,688 | 8,593 | 88.9% | 64.65% |
| Normalized spelling (main analysis) | 77,432 | 14,690 | 8,595 | 88.9% | 64.65% |
| Exact spelling with diacritics | 77,432 | 19,478 | 12,583 | 83.75% | 59.15% |
| Stem (database) | 77,432 | 12,111 | 6,537 | 91.56% | 69.52% |
| Lemma (database) | 77,432 | 5,505 | 2,433 | 96.86% | 81.56% |
| Root (database) | 77,432 | 2,287 | 584 | 99.25% | 83.82% |

Coverage rises across the sequence exact spelling, normalized spelling, stem, lemma, root, which orders the
definitions roughly from strictest to loosest; looser labels merge more tokens into repeated types. For the question
this study addresses, repetition of the written text, the exact and normalized forms bound the answer
(83.75-88.90% for words and phrases; 59.15-64.65% for phrases). Under exact
spelling, 6,895 word types and 23,555 phrase types are repeated, 1,520 verses are fully covered, and
the first phrase enters the greedy ordering at rank 299 (130 phrases selected in total).

Stem, lemma and root labels address morphological rather than textual repetition, and their results should be
read with the database quality in mind (section 5.5).

### 5.5 Audit of the normalization and the databases

- **Over-merging by normalization.** 2,948 of 14,690 normalized types combine two or more exact spellings,
  and these types hold 55,279 tokens (71.4%). Examples are مِنْ / مَنْ, اِنَّ / اَنْ and
  the three case endings of اللّٰه.
- **Homographs by lemma.** 619 normalized types map to two or more database lemmas, holding 16,257 tokens
  (21.0%), for instance `ان`, which covers إِنَّ, إِنْ, أَنَّ and أَنْ.
- **Label coverage.** Every token has a stem except 5. 4,925 tokens have no lemma, and 27,134
  tokens (35.0%, chiefly function words) have no root, so root-level results rest on the 65.0%
  of tokens that carry a root.
- **Errors inside the lemma database.** The word-level lemma data assigns the lemma of "from" (مِن) to 391
  tokens of مَنْ ("who"), so it does not reliably separate this homograph.
- **Internal inconsistency.** The verse-level and word-level databases disagree for 1,834 verses (lemma),
  436 verses (stem) and 324 verses (root); 20 verses are absent from the verse-level lemma
  file and 22 from the verse-level root file. The word-level lemma data also carries 3 entries
  at verse-end marker positions.

These findings indicate that the databases improve semantic analyses but do not make the analysis of the written
text more accurate, and that their own errors limit how precisely lemma and root repetition can be stated.

## 6. Limitations

1. **Operational equivalence.** Normalization merges forms that differ only in diacritics or hamza; exact
   spelling splits orthographic variants of the same word. Neither is a lemma-level or recitation-level
   ground truth, so both are reported.
2. **Verse-bounded units.** Repetitions spanning the end of one verse and the beginning of the next are not
   detected.
3. **Overlap counting.** Total frequency counts overlapping occurrences separately (for example, `A A` in
   `A A A` occurs twice).
4. **Heuristic ordering.** The greedy ordering is an approximation to the (NP-hard) optimal cover, and its effort
   measure double-charges overlapping units.
5. **Interpretation of coverage.** Coverage measures the share of token positions that belong to some repeated
   unit. It does not measure the ability to recite verses, which depends on sequencing and context that this
   analysis does not model.
6. **Database quality.** Stem, lemma and root results depend on databases with missing labels and internal
   inconsistencies (section 5.5).
7. **Descriptive scope.** The study describes the supplied text; it makes no inferential claims and does not
   assess the statistical significance of repetition against a null model.

## 7. Reproducibility

All code, input files, outputs and definitions are provided in this package. The three scripts
(`normalize.py`, `analyze.py`, `compare_representations.py`) run end to end with `run_all.sh` and require only
Python 3.9 or later.

## Reference

Chvatal, V. (1979). A greedy heuristic for the set-covering problem. *Mathematics of Operations Research*,
4(3), 233-235.
