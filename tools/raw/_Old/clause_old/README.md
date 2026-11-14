# QLAC Surah Al-Mulk: EQTB + QAC enrichment pipeline

This package replaces the earlier two-step `combine_surah_mulk_v2.py` + `extract_surah_mulk_clauses.py` proof of concept with one pipeline that loads the **complete set of EQTB auxiliary resources** as well as the main `Quranic.csv` file and, optionally, QAC's morphology export.

## Included in this package

- `build_surah_mulk_dataset.py` — full data preparation pipeline.
- `eqtb_aux/RelLabels.csv` — dependency-relation codebook.
- `eqtb_aux/CAPoS.csv` — part-of-speech codebook.
- `eqtb_aux/ConstituentsTags.csv` — constituent codebook.
- `eqtb_aux/CAMorphFeatures.xlsx` — morphology feature workbook.
- `eqtb_aux/CALemmaLexicon.csv` — lemma lexicon.
- `eqtb_aux/CARootLexicon.csv` — root lexicon.

The main `Quranic.csv` (about 50 MB in your local copy) and QAC morphology file are not included; supply their local paths when running the script.

## Requirements

- Python 3.9+
- `openpyxl` for reading the workbook

Install the dependency:

```bash
python -m pip install openpyxl
```

## Run for Surah Al-Mulk

From the extracted package directory:

```bash
python build_surah_mulk_dataset.py \
  --eqtb "/path/to/Quranic.csv" \
  --qac "/path/to/quranic-corpus-morphology-0.4.txt" \
  --aux-dir "eqtb_aux" \
  --out "outputs/surah_67_full"
```

Surah 67 is the default. You can omit `--surah 67`; for a different surah, pass `--surah N`.

QAC is optional. To build the enriched EQTB-only dataset, omit `--qac`.

## Output files

| Output | Contents |
|---|---|
| `eqtb_tokens_enriched_surah_67.csv` | All Surah 67 EQTB token rows, retaining original values and adding decoded POS, relation, constituent and morphology metadata. |
| `qac_morphology_surah_67.csv` | QAC morphology rows for Surah 67. |
| `eqtb_qac_alignment_surah_67.csv` | Coordinate-based EQTB/QAC outer alignment, preserving both sources. |
| `morphology_surah_67.csv` | Focused morphology view with decoded features and lexicon indicators. |
| `dependencies_surah_67.csv` | Dependency relations and best-effort resolution of `ref_token_id` within each sentence. |
| `constituents_surah_67.csv` | All EQTB constituent spans, including prepositional phrases. |
| `clause_candidates_surah_67.csv` | Clause-like constituent candidates (`S`, `NS`, `VS`, `CS`, `SC`); not final classifications. |
| `constituent_tokens_surah_67.csv` | Token membership for each constituent span, including implicit tokens. |
| `lemma_validation_surah_67.csv` | Unique lemmas and whether they occur in the supplied lemma lexicon. |
| `root_validation_surah_67.csv` | Unique roots and whether they occur in the supplied root lexicon. |
| `lookup_relations.csv` | Normalized relation-code lookup. |
| `lookup_pos.csv` | Normalized POS lookup. |
| `lookup_constituents.csv` | Normalized constituent lookup. |
| `lookup_morphology_features.csv` | Flattened lookup values from the morphology workbook. |
| `eqtb_metadata_lookup.json` | Full metadata mappings used by the pipeline. |
| `dataset_summary_surah_67.json` | Counts, mapping coverage, unknown codes, duplicate locations, warnings and methodological notes. |

## How all EQTB resources are used

1. `Quranic.csv` supplies the token, morphological, dependency and constituent records.
2. `RelLabels.csv` maps `rel_label` codes to their Arabic descriptions. **Its `rel_en` column contains codes** such as `cond`, `rslt`, and `circ`; it is not an English gloss column.
3. `CAPoS.csv` adds Arabic and English descriptions for POS codes.
4. `ConstituentsTags.csv` adds Arabic and English descriptions for `NS`, `VS`, `CS`, `PP`, `SC`, and `S`.
5. `CAMorphFeatures.xlsx` decodes nominal case, noun type/state, number, prefixes, suffixes, verb form/mood/state/voice, special group, gender and person.
6. `CALemmaLexicon.csv` and `CARootLexicon.csv` provide membership checks and supplementary Arabic/frequency data. They do not overwrite the source lemma or root.

## Important data handling decisions

- The auxiliary `.csv` files are UTF-16, tab-delimited files despite their `.csv` extensions. The loader detects this automatically.
- The main EQTB file's encoding and delimiter are also detected automatically; `--eqtb-encoding` can override encoding detection.
- Implicit EQTB tokens such as `(هُوَ)` with `word_id=0` or `location=_` are preserved. They are not assigned fake Quranic word coordinates and are not matched directly to QAC.
- `constituents_loc` is interpreted as an inclusive sentence-local token range, using `(sentence_id, token_id)`.
- Constituents may be nested. The pipeline preserves overlapping spans and identifies the nearest containing constituent as a parent.
- Duplicate Quranic coordinates are paired by occurrence order for the alignment output. Any duplicate-coordinate cases should be reviewed rather than assumed to be semantically identical.
- QAC input is the downloadable **morphology** export, not a complete QAC syntactic treebank.
- A clause candidate is not a verified clause annotation. The candidates require linguistic review before they are used as training labels.

## Workbook corrections

The supplied `CAMorphFeatures.xlsx` has the English descriptions for `JUS` and `SUBJ` reversed in the `VerbMood` sheet relative to their Arabic descriptions. The pipeline corrects these English lookup descriptions:

- `JUS` / مجزوم → Jussive mood
- `SUBJ` / منصوب → Subjunctive mood

The `VerbState` sheet also has Arabic placeholder text in its English-description column. The pipeline uses the corresponding standard English descriptions for `PERF`, `IMPF`, and `IMPV`.

## Validation status

The script has been compiled and run against a synthetic test fixture that uses the supplied auxiliary files and mirrors the observed EQTB column names, implicit tokens, and nested constituent spans. **It has not yet been run against your full 50 MB production `Quranic.csv` and your QAC download in this environment.** Review `dataset_summary_surah_67.json` after your first full run.

## Attribution and licensing

Retain the original EQTB and QAC attribution and comply with each source's applicable data license and terms before redistributing a derived combined dataset. This package includes the EQTB auxiliary files you supplied; it does not include the main Quranic table or QAC export.
