# Source Inventory

## EQTB

- Dataset page: https://data.mendeley.com/datasets/rk96pn66m4/1
- GitHub repository: https://github.com/NoorBayan/Quranic
- Main file: `Quranic.csv` (user reports approximately 50 MB; UTF-16, tab-delimited despite `.csv` extension).
- The `Quranic.csv` main table contains word/token and syntactic information, including fields such as `tid`, `sentence_id`, `token_id`, `location`, `uthmani_token`, `pos`, `features`, `lemma`, `root`, `rel_label`, `ref_token_id`, `is_constituent`, `constituents_loc`, `constituent_label`, and `constituents`.

### EQTB auxiliary files

| File | Approximate rows / structure | Role |
|---|---:|---|
| `RelLabels.csv` | 140 rows | Dependency relation codebook |
| `CAPoS.csv` | 45 rows | POS codebook |
| `ConstituentsTags.csv` | 6 rows | Constituent codebook |
| `CAMorphFeatures.xlsx` | 13 sheets | Morphological feature codebooks |
| `CALemmaLexicon.csv` | 4,833 rows | Lemma lookup lexicon |
| `CARootLexicon.csv` | 1,643 rows | Root lookup lexicon |

The six auxiliary files provided in this conversation are included under `reference/eqtb_aux/`. They were observed as UTF-16 tab-delimited files even though the CSV extension suggests comma-separated text. The Excel workbook is a normal `.xlsx` file.

### Important EQTB schema facts observed

- `constituents_loc` values look like `[3-18]` and represent inclusive, sentence-local `token_id` ranges.
- The correct lookup key for tokens within these spans is `(sentence_id, token_id)`.
- `sentence_id` can span more than one Quranic verse.
- Some implicit tokens have `sentence_word = 0`, `location = _`, and surface placeholders such as `(هُوَ)` or `(*)`. They are grammatical/source records but do not map directly to ordinary QAC Quranic word coordinates.
- EQTB constituent tags observed for Al-Mulk: PP, NS, VS, SC, CS. The codebook also includes S.
- Do not assume all constituent tags are phrase-level labels. PP is prepositional phrase; NS/VS/CS/SC are sentence/clause-like structures in the source's own scheme.
- `RelLabels.csv`'s `rel_en` field was observed to contain relation codes (e.g. `cond`, `rslt`, `circ`), not necessarily human-readable English glosses. Use `rel_ar` for the Arabic description and preserve the source code.

## QAC

- Corpus: https://corpus.quran.com/
- Current file used: `quranic-corpus-morphology-0.4.txt`.
- This project used QAC morphology, not a complete QAC syntactic treebank. Do not describe this integration as independent syntactic validation.
- QAC morphology locations use Quranic surah:ayah:word:segment coordinates. They are not interchangeable with EQTB's sentence-local token IDs.

## Surah Al-Mulk production run (user-reported)

The summary file is included at `reference/results_surah_67/dataset_summary_surah_67.json`.

| Metric | Result |
|---|---:|
| EQTB total file rows | 139,376 |
| EQTB rows for Surah 67 | 583 |
| QAC morphology rows | 529 |
| Exact location matches | 529 |
| EQTB implicit tokens without Quranic location | 54 |
| Duplicate location keys | 0 |
| Constituents | 116 |
| PP | 50 |
| NS | 17 |
| VS | 44 |
| SC | 3 |
| CS | 2 |
| Clause-like candidates (NS+VS+SC+CS) | 66 |
| Constituent-token memberships | 560 |
| Unique lemmas / found in lexicon | 171 / 171 |
| Unique roots / found in lexicon | 128 / 128 |

The production summary was generated before the user reran the latest morphology-mapping correction. It is suitable for source counts/alignment/constituent inventory, but its pre-correction mapping status fields should not be treated as the final morphology audit.

## Not included in this handoff package

- Full main `Quranic.csv` (50 MB; provide from the user's original download).
- QAC morphology export (provide from the user's original download).

These are deliberately not duplicated in this handoff bundle.
