# Surah Al-Mulk (67): clause / phrase dataset

Pipeline: `annotations/mulk_spec.json` (hand-edited) + `sources/*` -> `scripts/build_dataset.py` -> `data/*`.
To change a boundary or translation, edit the spec and re-run `python3 scripts/build_dataset.py`;
the build asserts that phrases tile clauses and clauses tile each ayah.

## Tables (data/)
| file | grain | rows |
|---|---|---|
| words.csv | one row per word (end-of-ayah number excluded) | 333 |
| phrases.csv | one row per phrase | 213 |
| clauses.csv | one row per clause | 86 |
| mulk.json | nested ayah > clause > phrase > word ids | 30 ayahs |

Join keys: `word_id` (67:15:3), `phrase_id` (67:15:c2:p1), `clause_id` (67:15:c2).

### words.csv
text (QPC Hafs), text_norm, waqf_mark, root, lemma, pos (N/V/P), cat (specific tag: PRON, REL, DEM, NEG, COND, INTG, CONJ, REM, CIRC, ...),
prefix_tags (e.g. REM, CONJ, P+DET), definite, suffix_pron, features,
clause_id/phrase_id and their orders, boundary_before (A=ayah start, C=clause start, P=phrase start, I=inside a phrase),
is_clause_start, is_phrase_start, prev_word_waqf, qsu_unit_begins / qsu_unit_ends (empty until import_qsu.py is run).

### phrases.csv / clauses.csv
text, text_norm (diacritics stripped, for grouping), translation (readable), translation_key (lower-case, no punctuation,
referent-neutral: "and it is" -> "and he is"), pattern (POS/tag sequence), n_words, first/last category, waqf flags.

## Translation normalisation applied
Same Arabic now always gets the same `translation_key` (0 conflicts):
- فَسَتَعْلَمُونَ -> "So you will soon know" (67:17 was "Then you will know")
- فَمَن -> "who then" (67:28 was "who")
- إِنَّهُ -> "Indeed, He is" (67:19 was "Indeed He" + "sees everything")
- وَهُوَ in 67:4 stays "and it is" (it refers to the vision) but shares the key "and he is".

## Sources and licences
- QUL (Tarteel): QPC Hafs word-by-word, Digital Khatt v2, Sahih International: see qul.tarteel.ai resource terms.
- Quranic Arabic Corpus morphology via github.com/mustafa0x/quran-morphology (QAC is GPL-licensed).
- QSU (optional): Mendeley Data DOI 10.17632/v7hyhk7krd.1, CC BY-NC 3.0 (non-commercial).
