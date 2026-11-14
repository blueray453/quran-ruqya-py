# Exploratory prototypes — not the final annotation architecture

These scripts were created during the earlier Surah Al-Mulk source-integration experiment.

- `build_surah_mulk_dataset.py` reads EQTB, the six auxiliary files and optionally QAC morphology. It exports enriched copies of source rows for inspection and produces counts/audits.
- `extract_surah_mulk_clauses.py` is an earlier constituent-span extraction experiment.

They are included for provenance and to reuse useful parsing logic. Their output CSVs are not the final project dataset because they copy existing source attributes. The agreed final architecture is reference-only: store new phrase/clause annotations and references, and resolve source data at runtime.
