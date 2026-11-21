# Quranic grammar annotation layers

Two JSON files that annotate the existing IndoPak Nastaleeq Quran files (`indopak-nastaleeq.json`, `indopak-nastaleeq-wbw.json`) with
word morphology and sentence syntax from the Quranic Arabic Corpus / Treebank. They add grammar to that text; they never change or
re-define it. Start with `docs/SCHEMA.md` (every field and rule) and `docs/QUESTIONS.md` (which question is answered by which script).

## Pipeline: one Python file per stage, bound by `run_all.sh`

| Stage | File | Reads | Writes |
|---|---|---|---|
| 01 normalize | `pipeline/01_normalize.py` | `data/` Quran files, `word-stem.db` | `build/indopak-nastaleeq-wbw-normalized.json`; fails unless it is byte-identical to the supplied `data/` copy |
| 02 build JSON | `pipeline/02_build_json.py` | `build/`, `data/Quranic/*` | `output/*-grammar-normalized.json` (word layer, sentence layer) |
| 03 validate JSON | `pipeline/03_validate_json.py` | `output/`, `data/` | `output/validation-report.json` (34 checks) |
| 04 generate CSV | `pipeline/04_generate_csv.py` | **the two JSON layers only** | `output/sequences/` POS and function sequence CSVs, greedy learning orders, occurrence JSON |
| 05 analysis | `pipeline/05_analysis.py` | **the two JSON layers only** | `output/analysis/` verb forms, roots, derived nouns, frequencies, complete source-issue lists |
| 06 docs | `pipeline/06_docs.py` | the query scripts | `docs/QUESTIONS.md`, `docs/examples/` |
| 07 self-test | `queries/_self_test.py` | `output/` | runs every question script on a known example |

```bash
pip install -r requirements.txt
./run_all.sh            # everything (a few minutes);  ./run_all.sh 04 05  runs only those stages
```

After stage 03 the pipeline prints a **checkpoint**: the JSON is final, so decide which questions it must answer (`docs/QUESTIONS.md`),
add scripts under `queries/`, and only then rely on stages 04-07. `data/` holds every input exactly as supplied
(`data/CHECKSUMS.sha256`; stage 03 fails if anything changed).

## Output

| Path | Contents |
|---|---|
| `output/indopak-nastaleeq-wbw-grammar-normalized.json` | 77,432 written words (`surah:ayah:word`): segments, POS, root, lemma, features, verb forms (explicit vs inferred), derived nouns, word gloss, whole-word projections |
| `output/indopak-nastaleeq-sentence-grammar-normalized.json` | 11,693 Treebank sentences: words, nodes with relation and head, constituents, implicit nodes, POS / function sequences |
| `output/sequences/` | grammar equivalents of `quran-phrases.csv` (below) |
| `output/analysis/` | verb-form, root, derived-noun and frequency CSVs; `source-lists/` = COMPLETE lists of every source irregularity |

## Ask questions of the JSON

One script per question in `queries/` (20 of them), e.g.

```bash
python3 queries/q07_word_relations.py 67:15:4         # relation, head and dependents of a word
python3 queries/q11_dependency_tree.py 10846          # dependency tree of a sentence
python3 queries/q19_occurrences.py --root jEl         # where else does this root occur
python3 queries/q16_verb_form_statistics.py           # Forms I-XII, explicit vs inferred
```

## Sequence CSVs (grammar equivalents of `quran-phrases.csv`)

`pipeline/04_generate_csv.py` reads only the two JSON layers. Same definition as the original: consecutive whole words, one label per
word, **never across a sentence boundary**, kept if they occur at least twice, `total = stand_alone + inside_longer`; POS and function
sequences are separate; ids are ordered most frequent first, then longer first. It re-counts 150 random units per analysis by brute force.

| File | Contents |
|---|---|
| `quran-pos-sequences.csv`, `quran-function-sequences.csv` | repeated sequences (ids `P00001`..., `F00001`...) with total / stand-alone / inside-longer counts, sentence counts, example text |
| `quran-greedy-order-pos-sequences.csv`, `quran-greedy-order-function-sequences.csv` | learning order = new words covered / sequence length |
| `*-annotation.json` | every unit with exact occurrence locations (compact start positions into `word_index`) |
| `sequence-analysis-report.json` | parameters, input hashes, coverage by minimum length, greedy checkpoints |

Options: `--pos-projection pos_all_segments|pos_stem`, `--function-projection function_without_NonRel|function_all|function_stem`,
`--min-count 2`, `--greedy-min-len 3`. The learning order **ignores sequences shorter than 3 labels by default**: with
`--greedy-min-len 1` (the original algorithm) the ten most common single POS labels already cover 63% of the Quran, which carries no
ranking information. With 3, learning 300 words (100 sequences) covers 31% of the Quran (POS) / 30% (function). Coverage percentages divide by all 77,432 written words.

## What is guaranteed (stage 03, 34 checks)

* Word keys equal the written words of the WBW file; text and ids match; verse-end markers are not words.
* **Alignment:** the IndoPak WBW text and the Uthmani Treebank split the text into words differently in 3 ayahs (see below); every word is aligned
  by its Arabic text and the check fails if any aligned pair does not match.
* **Lossless:** all 139,376 Treebank rows x 43 columns are re-created exactly from the two JSON files; each row is stored once.
* Sentence ids 1..11693, original order, valid heads and constituent spans; every word is in exactly one sentence.
* Derived fields (projections, verb forms, sequences) are recomputed independently and match.
* Every POS, relation, form, case, root and lemma used is defined in `reference_data`.
* Morphology v0.4 has the same 128,219 segments and identical feature strings as the Treebank.

## Things to know

* **No word is missing.** The Treebank writes `بَعْدَمَا` as one word where the IndoPak WBW text writes two (2:181, 8:6, 13:37). The merged
  word's two segments are distributed over the two WBW words; Treebank word numbers after it in those ayahs are one lower than the WBW numbers.
* Original vs derived: anything under `derived` (and sentence `constituents`) is computed here.
* Segment text is Uthmani, so annotations attach to whole IndoPak words, not to characters.
* Form I is never explicit in the source: all 12,347 are inferred. Nouns with a form annotation (1,968) are not counted as verbs.
* 41 words straddle two sentences; 26 sentences are prefix-only fragments; 132 POS tags differ from v0.4; 16 words have a short
  `text_normalized` because the IndoPak font stores letter clusters as one glyph. `output/analysis/source-lists/` lists every one.
* The supplied feature guide has 7 wrong English descriptions (verb-form ordinals, mood). They are kept verbatim and corrected beside the original.
* Not in the source, hence not in the files: explanations of why a case applies, what a particle does, contextual translation.

Grammar data: Quranic Arabic Corpus (corpus.quran.com), morphology v0.4 (GNU GPL; the source file says it must not be changed). The generated
files are derivative works and should carry the same attribution and license terms.
