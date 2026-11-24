# Quranic Arabic reproducible corpus analysis

This project recreates the Quranic Arabic grammar/frequency CSVs and produces two narrative reports from those CSVs. The CSV generators read the bundled raw data. The report builder reads **only the generated CSVs**; it does not reread or recalculate from source data.

## What is included

- `data_sources.zip` - curated original data inputs used by the pipeline (QAC, supplied MASAQ CSV, QUL WBW and QUL SQLite word mappings, codebooks).
- `reference_tables.zip` - curated grammar curriculum architecture, Ism taxonomy, phrase taxonomies and reference tables used in the generated output.
- `scripts/build_frequency_csvs.py` - creates QUL vocabulary, QAC verb/POS, QAC relationship/constituent and MASAQ role frequency CSVs.
- `scripts/build_ism_csvs.py` - creates quantitative QAC and MASAQ Ism feature distributions.
- `scripts/build_compatibility_csvs.py` - creates status, provenance, compatibility and interpretation tables from the generated CSVs.
- `scripts/build_reports_from_csvs.py` - builds the complete report and Ism addendum from CSVs only.
- `scripts/validate_outputs.py` - checks core counts against the bundled source snapshot.
- `run_pipeline.py` - extracts the nested archives, runs all generators and validation, then builds DOCX reports and PDFs (if LibreOffice is installed).
- `output/csv/` - generated CSV files from the tested run.
- `output/reports/` - generated DOCX/PDF reports from the tested run.

## Run it

Python 3.10+ is recommended. The CSV-generation scripts use only the Python standard library. Report generation requires `python-docx`.

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_pipeline.py
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_pipeline.py
```

Outputs are written under `output/csv/` and `output/reports/`. If LibreOffice is installed (`soffice` is on PATH), the runner converts the DOCX reports to PDF automatically. To skip PDF conversion:

```bash
python run_pipeline.py --skip-pdf
```

To skip the snapshot-specific expected-count tests when updating the input versions:

```bash
python run_pipeline.py --skip-validation
```

The source and reference archives can be replaced with compatible versions:

```bash
python run_pipeline.py --source-zip path/to/data_sources.zip --reference-zip path/to/reference_tables.zip
```

## Individual stages

After extracting both archives, the three CSV-generation steps can also be run separately:

```bash
python scripts/build_frequency_csvs.py --data-dir build_workspace/source_data --output-dir output/csv --reference-dir build_workspace/reference_tables
python scripts/build_ism_csvs.py --grammar-dir build_workspace/source_data/grammar --output-dir output/csv
python scripts/build_compatibility_csvs.py --csv-dir output/csv --data-dir build_workspace/source_data
python scripts/build_reports_from_csvs.py --csv-dir output/csv --output-dir output/reports
```

The fourth command is the report stage and consumes only `output/csv/`.

## Main calculations and population units

- QUL surface vocabulary: word-by-word entries with numeric verse markers excluded; the generated snapshot has 77,432 word tokens and 21,294 distinct surface forms.
- QUL lemma/stem/root: each uses its own SQLite mapping table and its own mapped-occurrence denominator. Mapping totals are not interchangeable.
- QAC v0.4 morphology: 77,915 STEM annotations and 19,356 verb STEMs. Mood distribution is calculated only over 8,330 imperfect verb STEMs.
- QAC broad Ism pool: 40,778 STEM annotations over 40,773 unique word positions. Gender, number, case, and nominal-state data are joined from the supplied QAC convenience export by exact segment location after POS membership is anchored to the raw v0.4 morphology file.
- Supplied MASAQ CSV: 157,676 data rows; 77,797 Stem segment rows; 39,237 Ism-family Stem rows. Its population does not reconcile with the published article profile, so the output labels this input as the supplied MASAQ CSV rather than asserting that it is a verified V6 snapshot.
- QAC convenience syntax: 103,781 observed dependency-relation rows and 26,463 constituent annotation rows in the supplied `Quranic.csv` export.


### Mapping dictionary reconciliation

The three QUL SQLite lexicons have 4,817 lemma entries and 12,113 stem entries in total. The frequency outputs include only entries with at least one word-location mapping: 4,793 lemmas and 12,108 stems. The remaining 24 lemmas and 5 stems have no linked Quran word positions and are excluded from occurrence-frequency rankings; `dataset_mapping_coverage.csv` now reports both the full lexicon size and the linked/unlinked term counts. This explains the row-count difference from earlier exports without changing the mapped occurrence totals. All 1,642 root entries have word-position links.

## Interpretation safeguards

- `UNMARKED` means an annotation is not present in that source field; it is not a grammar value. Do not infer masculine, singular, definite or indefinite.
- QAC nominal cases are NOM, ACC and GEN (Rafʿ, Nasb and Jarr). Jussive is a verb mood, not a noun case. Sukoon is not an additional noun case.
- Definiteness is reported through available state and marker evidence; the source does not supply a complete binary DEF/INDEF label for every Ism.
- MASAQ word/segment roles are not phrase-span `Phrasal_Function` frequencies. The pipeline deliberately does not treat word-level annotations as phrase counts.
- The six teaching phrase constructions describe internal phrase structure; MASAQ `Phrasal_Function` is an external phrase function. They are separate taxonomies.
- QAC, QUL and MASAQ counts use different populations, tags and counting units. Never add their occurrence totals together.

## Rebuilding reports independently

To rebuild just the reports after editing any CSV, run:

```bash
python scripts/build_reports_from_csvs.py --csv-dir output/csv --output-dir output/reports
```

This script deliberately has no source-data argument. The reports are generated exclusively from the CSV tables and the two JSON summaries written alongside them.

## Licensing and provenance

Read `SOURCES_AND_LICENSES.md` before sharing or using this package in a product. In brief: QAC includes a GNU GPL notice and attribution requirements; the source file also contains Tanzil text terms; the MASAQ V6 Mendeley record lists CC BY-NC 3.0 but the supplied CSV version/profile is not independently reconciled; and QUL resources may have resource-specific terms. The book PDFs marked personal-use-only are excluded.
