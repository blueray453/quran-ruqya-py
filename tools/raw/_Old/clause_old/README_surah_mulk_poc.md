# EQTB + QAC proof of concept: Surah Al-Mulk

## 1. Download the two inputs

### EQTB

Download **Primary Quranic.csv** from the Mendeley dataset:
https://data.mendeley.com/datasets/rk96pn66m4/1

### QAC

Use the official Quranic Arabic Corpus download page:
https://corpus.quran.com/download/

Download the Version 0.4 morphology file (`quranic-corpus-morphology-0.4.txt`). The page asks for a contact email and agreement to the corpus terms.

**Scope note:** The official bulk download used by this script is the QAC morphology file. It is not a full bulk export of all QAC syntactic tree structures. The script therefore compares EQTB's syntax fields with QAC's word/segment morphology and grammatical tags; it does not merge a full QAC syntactic treebank.

## 2. File layout

```text
project/
├── combine_surah_mulk.py
├── data/
│   ├── Primary Quranic.csv
│   └── quranic-corpus-morphology-0.4.txt
└── outputs/
```

## 3. Run

Python 3.9 or later is sufficient. No third-party packages are required.

```bash
python combine_surah_mulk.py \
  --eqtb "data/Primary Quranic.csv" \
  --qac "data/quranic-corpus-morphology-0.4.txt" \
  --out outputs/surah_67
```

The script detects common encodings automatically, including UTF-16 LE/BE (with a BOM) and UTF-8 with or without a BOM. This handles EQTB CSV files exported as UTF-16; no `iconv` conversion is necessary.

If automatic detection does not match your file, pass an explicit encoding:

```bash
python combine_surah_mulk.py \
  --eqtb "data/Primary Quranic.csv" \
  --qac "data/quranic-corpus-morphology-0.4.txt" \
  --eqtb-encoding utf-16 \
  --qac-encoding utf-8-sig \
  --out outputs/surah_67
```

Surah 67 is the default. To select a different surah, pass `--surah N`. The detected encodings are recorded in `summary_surah_67.json`.

## 4. Outputs

- `eqtb_surah_67.csv`: all EQTB rows for Surah Al-Mulk.
- `qac_surah_67.csv`: all QAC morphology rows for Surah Al-Mulk.
- `aligned_surah_67.csv`: outer alignment by the exact four-part location `surah:ayah:word:segment`.
- `clause_candidates_surah_67.csv`: EQTB rows that look relevant for clause/constituent review.
- `summary_surah_67.json`: match counts, unmatched rows, duplicate location keys, and parsing warnings.

## 5. Interpret the results carefully

- `exact_location_match` means the four-part source location strings matched. It does **not** prove that the analyses agree or that the segmentation conventions are identical.
- `eqtb_only` and `qac_only` rows should be inspected. They may indicate tokenization differences, missing source rows, or formatting issues.
- The clause candidate file is only a review queue. It does not claim to produce authoritative clause labels.
- Keep both original datasets and their annotations unchanged. The output stores the source analyses in separate `eqtb_` and `qac_` columns.

Check the source licenses and attribution requirements before redistributing any combined data. In particular, the QAC download page specifies conditions for copying and changing its annotation file.
