# Reproduction test results

The project was run from its two nested ZIP archives using `python run_pipeline.py` on the supplied source snapshot. The pipeline verified the 13 bundled source files against SHA-256 and regenerated the CSVs and both DOCX/PDF reports. It passed every validation check.

Snapshot checks passed:

- QUL: 77,432 word tokens; 21,294 surface forms; 72,510 lemma occurrences; 77,427 stem occurrences; 50,298 root occurrences.
- QAC v0.4: 77,915 STEM rows; 19,356 verb STEMs; 8,330 imperfect verb STEMs.
- QAC extended export: 139,376 rows; 103,781 dependency-relation rows; 26,463 constituent-annotation rows.
- Supplied MASAQ CSV: 157,676 rows; 110,886 observed word/segment syntactic-role annotations; 77,797 Stem rows.
- QAC broad Ism: 40,778 STEM annotations over 40,773 word positions; gender, number and case distributions passed their expected-value checks.
- MASAQ Ism family subset: 39,237 STEM rows.

The report-only script was also tested using a directory containing the generated CSV files without the JSON summaries or original source data. Both DOCX reports were successfully rebuilt from that CSV-only directory.

Run `python run_pipeline.py` to repeat the test and rebuild all deliverables.
