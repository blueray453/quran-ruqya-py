# Quranic grammar annotation layers

Two JSON files that annotate the existing IndoPak Nastaleeq Quran files (`indopak-nastaleeq.json`, `indopak-nastaleeq-wbw.json`) with
word morphology and sentence syntax from the Quranic Arabic Corpus / Treebank, plus a set of study and linguist tables computed from them.
The layers add grammar to that text; they never change or re-define it.

Start with `docs/plain-language-guide.md` (what everything is, in plain words), `docs/SCHEMA.md` (every field and rule) and
`docs/QUESTIONS.md` (which question is answered by which script).

## Pipeline: one Python file per stage, bound by `run_all.sh`

| Stage | File | Writes |
|---|---|---|
| 01 normalize | `pipeline/01_normalize.py` | `build/indopak-nastaleeq-wbw-normalized.json` (fails unless byte-identical to the supplied `data/` copy) |
| 02 build JSON | `pipeline/02_build_json.py` | `output/*-grammar-normalized.json`: the **word layer** and the **sentence layer** |
| 03 validate JSON | `pipeline/03_validate_json.py` | `output/validation-report.json` (34 checks) |
| 04 sequences | `pipeline/04_generate_csv.py` | `output/sequences/` (repeated POS / function patterns) and the pattern memorization orders |
| 05 analysis | `pipeline/05_analysis.py` | `output/analysis/` (verb forms, derived nouns, frequencies, complete source-issue lists) |
| 06 phrases | `pipeline/06_phrases.py` | `output/phrases/` (repeated Arabic words and phrases) and their memorization orders |
| 07 lexicon tables | `pipeline/07_lexicon_tables.py` | `output/lexicon/` (root families, written forms, conjugations, pronouns, affixes, hapax ...) |
| 08 syntax tables | `pipeline/08_syntax_tables.py` | `output/syntax/` (case by role, verb valency, prepositions, possessives, particles, implicit elements ...) |
| 09 reading tables | `pipeline/09_reading_tables.py` | `output/reading/` (surah and ayah vocabulary load) and the vocabulary memorization orders |
| 10 validate tables | `pipeline/10_validate_tables.py` | `output/tables-validation-report.json` (53 checks: every table reconciled with the JSON and with each other) |
| 11 docs | `pipeline/11_docs.py` | `docs/QUESTIONS.md`, `docs/examples/` |
| 12 self-test | `queries/_self_test.py` | runs every question script (23) on a known example |

```bash
pip install -r requirements.txt
./run_all.sh            # everything (about two minutes);  ./run_all.sh 07 08  runs only those stages
```

After stage 03 the pipeline prints a **checkpoint**: the JSON is final, so decide which questions it must answer, add scripts under `queries/`,
and only then rely on stages 04-12. `data/` holds every input exactly as supplied (`data/CHECKSUMS.sha256`; stage 03 fails if anything changed).
Stages 04-10 read **only the two JSON layers**.

## Output folders

| Folder | Contents |
|---|---|
| `output/*.json` | the two grammar layers: 77,432 written words and 11,693 sentences |
| `output/memorization-order/` | every "learn this first" list: Arabic words and phrases (4 variants, plus exact-diacritics), grammar patterns (8), dictionary words (2), roots, verbs, ayahs, surahs |
| `output/phrases/` | repeated Arabic words and phrases with locations; coverage by surah |
| `output/sequences/` | repeated grammar patterns by word type and by sentence role, with locations |
| `output/lexicon/` | 12 tables: root families, surface forms, verb paradigms, noun features, pronouns, affixes, function words, special groups, hapax, proper nouns |
| `output/syntax/` | 12 tables: case by function, verb valency, verb-preposition pairs, possessive pairs, noun-adjective pairs, preposition usage, particle-mood government, implicit elements, constituents, sentence lengths |
| `output/reading/` | surah profile and ayah vocabulary load |
| `output/analysis/` | verb and counting tables; `source-lists/` = COMPLETE lists of every source irregularity |

The guides in `docs/` explain every table: `plain-language-guide.md` (questions, sequences), `verb-and-counting-tables-guide.md` (`analysis/`) and
`study-and-linguist-tables-guide.md` (everything else), each with how to read the table and how to study with it.

## Ask questions of the JSON

One script per question in `queries/` (23 of them), e.g.

```bash
python3 queries/q07_word_relations.py 67:15:4         # relation, head and dependents of a word
python3 queries/q11_dependency_tree.py 10846          # dependency tree of a sentence
python3 queries/q21_root_family.py Elm                # all the words of a root
python3 queries/q22_verb_patterns.py Ealima           # how a verb is used
python3 queries/q23_ayah_vocabulary.py 1:2            # vocabulary and difficulty of an ayah
```

## Memorization order (greedy lists)

Every list picks, at each step, the unit that adds the most new coverage per word to learn, never counting a word twice (the method of the original
`quran-greedy-order-words-and-phrases.csv`). Arabic words and phrases reproduce the original project's tables **byte for byte** (checked in stage 10).
Grammar-pattern lists come in four variants by minimum pattern length (1, 2, 3, 5); the 3-plus variant is the useful one, because with so few
word types and roles nearly every short pattern repeats (the first 10 POS labels already cover 63% of the Quran).

## What is guaranteed

* **JSON (stage 03, 34 checks):** keys equal the written words of the WBW file; Treebank and WBW words are aligned by their Arabic letters (3 ayahs
  differ in word division); all 139,376 Treebank rows x 43 columns are re-created exactly from the two files; derived fields are recomputed independently.
* **Tables (stage 10, 53 checks):** totals reconcile with the JSON and across tables; ordering and cumulative columns are consistent; the Arabic phrase
  analysis matches the original project exactly (6,095 repeated words, 25,188 phrases, longest phrase 24 words, 88.9% coverage).
* **Questions (stage 12, 23 checks):** each question script reproduces a known answer.

## Things to know

* **No word is missing.** The Treebank writes `بَعْدَمَا` as one word where the IndoPak text writes two (2:181, 8:6, 13:37); the two are aligned by letters.
* Original vs derived: anything under `derived` (and sentence `constituents`) is computed here.
* Segment text is Uthmani, so annotations attach to whole IndoPak words, not to characters.
* Form I is never explicit in the source: all 12,347 are inferred. Nouns with a form annotation (1,968) are not counted as verbs.
* 41 words straddle two sentences; 26 sentences are prefix-only fragments; 132 POS tags differ from v0.4; 16 words have a short `text_normalized`.
  `output/analysis/source-lists/` lists every one.
* The supplied feature guide has 7 wrong English descriptions (verb-form ordinals, mood); they are kept verbatim and corrected beside the original.
* In the Treebank some particles are the head of their verb (negation) and others depend on it (future); `syntax/quran-particle-mood-government.csv` states the direction.
* Not in the source, hence not in the files: explanations of why a case applies, what a particle does, contextual translation.

Grammar data: Quranic Arabic Corpus (corpus.quran.com), morphology v0.4 (GNU GPL; the source file says it must not be changed). The generated
files are derivative works and should carry the same attribution and license terms.
