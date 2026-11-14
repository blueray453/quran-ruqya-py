# Surah Al-Mulk (67): clause / phrase dataset

Pipeline: `annotations/mulk_spec.json` (hand-edited) + `sources/*` -> `scripts/build_dataset.py` -> `data/*`.
To change a boundary or translation, edit the spec and re-run `python3 scripts/build_dataset.py`;
the build asserts that phrases tile clauses and clauses tile each ayah.

## Dataset (data/mulk.json)
Single nested JSON: `ayahs[] > clauses[] > phrases[] > words[]`. Morphology is inline on each word.
333 words, 213 phrases, 86 clauses, 30 ayahs.

- **ayah**: verse_key, text_digital_khatt, translation_sahih, translation_phrased (clauses joined), clauses[]
- **clause**: clause_id (67:15:c2), word_start/end, text, text_norm, translation, translation_key, pattern, first_cat, first_prefix, ends_with_waqf, is_ayah_final, phrases[]
- **phrase**: phrase_id (67:15:c2:p1), word_start/end, text, text_norm, translation (readable), translation_key (lower-case, no punctuation, referent-neutral: "and it is" -> "and he is"), pattern, first_cat/last_cat, has_waqf, words[]
- **word**: word_id (67:15:3), text (QPC Hafs), text_norm, waqf_mark, root, lemma, pos (N/V/P), cat (PRON, REL, DEM, NEG, COND, INTG, CONJ, REM, CIRC, ...), prefix_tags, definite, suffix_pron, features,
  boundary_before (A=ayah start, C=clause start, P=phrase start, I=inside a phrase), is_clause_start, is_phrase_start, prev_word_waqf

Analysis flattens the JSON with pandas in memory (see scripts/analyze.py); jq works directly, e.g.
`jq '[.ayahs[].clauses[].phrases[]] | group_by(.translation_key) | map(select(length>1) | {key:.[0].translation_key, n:length})' data/mulk.json`

## Translation normalisation applied
Same Arabic now always gets the same `translation_key` (0 conflicts):
- فَسَتَعْلَمُونَ -> "So you will soon know" (67:17 was "Then you will know")
- فَمَن -> "who then" (67:28 was "who")
- إِنَّهُ -> "Indeed, He is" (67:19 was "Indeed He" + "sees everything")
- وَهُوَ in 67:4 stays "and it is" (it refers to the vision) but shares the key "and he is".

## Sources and licences
- QUL (Tarteel): QPC Hafs word-by-word, Digital Khatt v2, Sahih International: see qul.tarteel.ai resource terms.
- Quranic Arabic Corpus morphology via github.com/mustafa0x/quran-morphology (QAC is GPL-licensed).
