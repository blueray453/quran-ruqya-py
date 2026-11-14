# Surah Al-Mulk (67): EQTB + QAC clause extraction proof of concept

This package contains:

- `combine_surah_mulk_v2.py`: merges EQTB and QAC morphology while preserving implicit EQTB tokens without inventing Quranic word coordinates.
- `extract_surah_mulk_clauses.py`: extracts EQTB constituent spans using `sentence_id + token_id` and creates a nested clause-candidate inventory.

Python 3.9+; standard library only.

## 1. Run the corrected EQTB + QAC alignment

```bash
python combine_surah_mulk_v2.py \
  --eqtb "data/Primary Quranic.csv" \
  --qac "data/quranic-corpus-morphology-0.4.txt" \
  --out outputs/surah_67
```

The revised merger treats records with `word_id=0` and no real Quranic `location` as implicit EQTB tokens. It retains them in the aligned export with status `eqtb_implicit_no_quranic_location`, but does not assign synthetic keys such as `67:2:0:1` or count them as duplicate Quranic locations.

For the counts previously reported by the user, the expected interpretation is:

- 529 real location matches;
- 54 implicit EQTB tokens retained separately;
- no QAC-only rows;
- duplicate-location counts should no longer include the word_id=0 placeholders.

Actual counts depend on the files supplied.

## 2. Extract clause-like constituent spans

```bash
python extract_surah_mulk_clauses.py \
  --eqtb "outputs/surah_67/eqtb_surah_67.csv" \
  --aligned "outputs/surah_67/aligned_surah_67.csv" \
  --out "outputs/surah_67/clause_extraction"
```

`--aligned` is optional. When supplied, QAC morphology fields are attached to clause-member tokens by EQTB's global `tid`, not by synthetic implicit-token locations.

The extractor interprets `constituents_loc` such as `[15-29]` as an inclusive range of sentence-local `token_id` values. It selects members by `(sentence_id, token_id)`.

## 3. Outputs

| File | Contents |
|---|---|
| `constituents_surah_67.csv` | All recognized EQTB constituent spans, including PP |
| `clauses_surah_67.csv` | Candidate clause-like constituents with spans, source labels, head relations, and nesting metadata |
| `clause_tokens_surah_67.csv` | One row per token membership in each candidate clause; nested clauses intentionally repeat tokens |
| `clause_extraction_summary_surah_67.json` | Counts, malformed/incomplete spans, warnings, and extraction notes |

## 4. Important interpretation notes

- `VS`, `NS`, `CS`, and `SC` are preserved as EQTB source labels. The script adds cautious descriptive names, not a scholarly re-interpretation of those labels.
- `PP` is retained in the constituent inventory but excluded from the clause-like output.
- Dependency-only review records without `is_constituent=1` and a valid `constituents_loc` are not turned into clause spans.
- Nested/overlapping spans are preserved. They are not flattened or deduplicated into unrelated clauses.
- The EQTB `constituents` field is retained as the source-provided span text. The script also outputs a token-ID debug sequence. Do not reconstruct display Arabic by blindly joining morphological segments with spaces.
- `clause_function`, `speech_act`, and `rhetorical_features` remain unassigned. They require a separate linguistic annotation step.
- A candidate span is not automatically a validated independent clause or complete sentence. Review it against Arabic grammar and the Quranic context.

## 5. Suggested validation

Start with these examples from Surah Al-Mulk:

- 67:2: the nested VS / SC / VS / NS spans;
- 67:10: the CS span and its nested NS span;
- 67:25: the CS span `إِن كُنتُمْ صَٰدِقِينَ`.

Check `clauses_surah_67.csv` and `clause_tokens_surah_67.csv`. Confirm span completeness, nesting, and whether the source-provided constituent text matches the Quranic tokens. Do not train a classifier until this sample has been reviewed.
