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
- **word**: word_id (67:15:3), text (QPC Hafs), text_norm, waqf_mark, root, lemma, stem (all three from QUL), qac_lemma (QAC's lemma, for reference), pos (N/V/P), cat (PRON, REL, DEM, NEG, COND, INTG, CONJ, REM, CIRC, ...), prefix_tags, definite, suffix_pron, features,
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
| Field(s) | Source |
|---|---|
| word text, word numbering, waqf marks | QUL qpc-hafs-word-by-word |
| ayah text | QUL digital-khatt-v2 |
| translation_sahih | QUL en-sahih-international-simple |
| root, lemma, stem | QUL word-root.db, word-lemma.db, word-stem.db (extracted for Surah 67 into sources/qul_mulk_morph.tsv) |
| pos, cat, prefix_tags, features, definite, suffix_pron, qac_lemma | Quranic Arabic Corpus via github.com/mustafa0x/quran-morphology (GPL) |
| clause/phrase boundaries and English phrases | hand annotation, annotations/mulk_spec.json |

QUL root vs QAC root: 0 disagreements on 209 words (after removing spaces and treating ا/أ/ء alike); the build asserts this.
QUL lemma vs QAC lemma: 28 differences, mostly spelling (dagger alif, رَءَا vs رَأَى, هَٰذَا vs ذا); 3 words have no QUL lemma
(67:8:9, 67:19:9, 67:23:10) and 3 words (67:20:1, 67:21:1, 67:22:7; all أَمَّنْ) are lemmatised as مِن by QUL vs أَم by QAC.
See qac_lemma to compare. QUL licence terms: see qul.tarteel.ai.

## Reference legends (reference/)
Plain-language names for every tag code used in the data (pos_tags, prefix_tags, constituent_tags, relation_labels),
taken from the Quranic Treebank's legend files. Look up `cat` and `prefix_tags` values here, e.g. REM = "Resumption particle".
Caution: the English descriptions in the treebank's VerbMood and VerbForm sheets are wrong, so those sheets are not included.

## Generating annotations (OpenRouter)
Per-surah annotations are written to `annotations/surah-NNN.json` (`ayahs` = clauses/phrases/English/Bangla, `status` = auto | needs_human | reviewed).
The model sees only Arabic words, word glosses, the two reference translations, `annotations/CONVENTIONS.md` and `annotations/glossary.json`.
It never sees tags, sentence ids or mined rules. Every reply is validated (tiling, JSON shape, scripts, quotes) and failures are retried, then marked needs_human.

    export OPENROUTER_API_KEY=...
    python3 scripts/generate_spec.py --data-root /path/to/qul --surah 67 --dry-run          # writes the prompts to annotations/_prompts/, no API call
    python3 scripts/generate_spec.py --data-root /path/to/qul --surah 67 --model <slug>      # one surah
    python3 scripts/generate_spec.py --data-root /path/to/qul --surahs 1-114 --model <slug> # everything; safe to re-run, done ayahs are skipped
    python3 scripts/generate_spec.py ... --retry-failed                                       # re-ask needs_human ayahs

`--data-root` is your QUL folder (quran-script/wbw/..., english-translation/..., bangla-translation/...). Token usage per call is logged to `annotations/usage.jsonl`.
After checking an ayah by hand, change its status to `reviewed` so it is never regenerated.

To start the new chat

Attach the zip and paste the starter prompt at the end of HANDOFF.md (section 11). Replace the bracket at the end with what you want first. I’d suggest step 1 of the next steps: run the generator on Surah 67 with your chosen model and compare it with the Al-Mulk annotation.

One thing to do on your side: the converter output you generated went into your current folder, so move the surah-NNN.json files into quranic-treebank/data/.

NOTE: Can you do it in memory. How to do it using bartch models. how can i make this cheap

NOTE: make a html prototype that show the full capability of this dataset using mulk.json and what it can do. for example if highlifht all clause, phase amd word with different color and give their meaning in both english and bangla. Give the analysis. Maybe highlish the phrases everywhere is the text. maybe highlight same word everywhere in the text. Give analysis. I am not understanding the capabilities. So show and also explain what we can do

NOTE: How can we make it better. for example, i think here the key is annotations. Should i make files for language seperate. Should we seperate mulk.json by language. What is the best format to represent the data. At this moment if something change, it is not clear. Should we use some other format so that `git diff` shows what changed. Think completely.