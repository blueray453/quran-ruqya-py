# Quranic Arabic frequency analysis data pack

## Purpose
Frequency analysis to inform an English-language Quranic Arabic comprehension curriculum. Tajweed and recitation coaching are out of scope.

## Primary counts
- QUL Uthmani word-by-word entries: 77,432 (numeric ayah marker rows excluded)
- Distinct surface-form types: 21,294
- QUL lemma mappings: 72,510 word locations; 4,793 occurring lemmas (93.64% of QUL word entries)
- QUL root mappings: 50,298 word locations; 1,642 occurring roots (64.96% of QUL word entries)
- QAC word_id groups: 77,429
- MASAQ unique word positions: 77,411
- QAC actual verb stems: 19,356
- QAC syntactic relation instances: 103,781 (includes `link`, excludes `root` and `NonRel` metadata)
- MASAQ observed syntactic role annotations: 110,886 (59 observed of 73 defined roles)

## Surface-form cumulative thresholds
- 50% token coverage: 618 distinct forms
- 60%: 1,421 forms
- 70%: 3,124 forms
- 80%: 6,493 forms
- 85%: 9,680 forms
- 90%: 13,551 forms
- 95%: 17,423 forms

These values measure lexical exposure over QUL WBW word positions, not comprehension. They do not equal the `85%` textbook's course-specific estimate.

## Important counting rules
1. `vocabulary_surface_frequency.csv` has one row per distinct Uthmani surface form. The frequency denominator is 77,432 QUL WBW entries.
2. QUL lemma/root reports use their mapped-occurrence denominators, not the full Quran token count.
3. QAC verb-form and feature reports use 19,356 actual verb-stem occurrences. QAC defaults are applied: Form I where no form tag is present, active voice where voice is unmarked, and indicative mood where mood is unmarked.
4. Sarf features (form, aspect, voice, mood, person, gender, number) are separate dimensions and overlap; do not sum them into one distribution.
5. QAC Nahw dependency relations are not the same unit as MASAQ syntactic-role annotations. Keep their tables separate.
6. `link` is included as a genuine PP-attachment relationship; `root` and `NonRel` are excluded as tree metadata in the current QAC relationship distribution.
7. Unique-Ayah incidence for individual categories is not additive. Cumulative Ayah coverage must be computed as a union of Ayah IDs.
8. Tanzil Uthmani raw whitespace splitting is not a valid word-token denominator because of prefatory basmalas, standalone marks and orthographic spacing. QUL WBW is the primary surface-word denominator in this release.
9. Source token positions differ slightly (QUL 77,432; QAC 77,429; MASAQ 77,411). Full reconciliation is not yet complete. Preserve source-specific location IDs and do not silently merge.

## Data files
The CSV files preserve complete ranked distributions. The primary workbook contains the individual surface-word table. Additional CSVs hold lemma, root, stem, Sarf dimension, feature-bundle, Nahw relation, MASAQ role, constituent and mapping reports.

## Curriculum references
- ILMHUB Book 1: https://www.ilmhub.org/courses/language-of-quran/book-1/
- ILMHUB Book 2: https://www.ilmhub.org/courses/language-of-quran/book-2/
- ILMHUB Grammar Guide: https://www.ilmhub.org/arabic-grammar/
- Bayyinah Dream Arabic: https://explore.bayyinahtv.com/arabic-resources/
- Arabic101 85% book/course: https://store.arabic101.org/85landing/

## Dataset references
- MASAQ V6: https://data.mendeley.com/datasets/9yvrzxktmr/6
- QUL: https://qul.tarteel.ai/resources
- QAC morphology: https://corpus.quran.com/documentation/morphologicalfeatures.jsp
- QAC syntax: https://corpus.quran.com/documentation/syntaxrelation.jsp
- Qabas: https://sina.birzeit.edu/qabas/
- Tanzil: https://tanzil.net/download/

## Licensing note
The uploaded `How to Understand 85% of the Quran` PDF is marked personal use only / not for sale or distribution. MASAQ V6 lists CC BY-NC 3.0. QUL licensing differs by individual resource. This analysis export should not be treated as clearing commercial redistribution rights. Obtain legal review and permissions before integrating dataset-derived materials into a commercial product.
