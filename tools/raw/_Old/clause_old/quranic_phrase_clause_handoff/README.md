# Quranic Phrase & Clause Annotation — Project Handoff

This package captures the project's current objective, architecture, source inventory, Surah Al-Mulk proof-of-concept results, proposed annotation schema, and next steps.

## The central design principle

**Existing datasets are immutable reference sources. Our new dataset stores only new phrase/clause annotations and references back to existing source records.**

Do not copy existing Quranic text, token morphology, roots, lemmas, POS, dependency annotations, or codebooks into the new annotation dataset. Resolve those values from the source datasets when the application displays them.

## Package contents

- `docs/PROJECT_HANDOFF.md` — full handoff for a new development session or collaborator.
- `docs/ARCHITECTURE.md` — recommended data architecture and source-reference strategy.
- `docs/SOURCE_INVENTORY.md` — source datasets, files, roles, limitations, and identifiers.
- `docs/ANNOTATION_MODEL.md` — phrase/clause concepts, taxonomy dimensions, and annotation rules.
- `docs/ROADMAP.md` — work plan and acceptance criteria.
- `schema/proposed_schema.sql` — proposed relational schema for our new annotation data only.
- `schema/source_registry.example.yaml` — source registry template.
- `schema/taxonomy_template.yaml` — initial taxonomy template; not a finalized linguistic standard.
- `reference/eqtb_aux/` — the six EQTB auxiliary files supplied in this conversation.
- `reference/results_surah_67/dataset_summary_surah_67.json` — summary from the user's successful Surah Al-Mulk production run.
- `prototype/` — exploratory scripts from the earlier data-inspection phase. They are **not** the final architecture or final QCAD exporter.

## Required source files not included

The package deliberately does not include the full 50 MB `Quranic.csv` or the QAC morphology export. Supply those from their original downloads in your local project. The `reference/eqtb_aux/` files are the supplementary EQTB resources.

## Working command from the previous prototype

```bash
python prototype/build_surah_mulk_dataset.py \
  --eqtb data/Quranic.csv \
  --qac data/quranic-corpus-morphology-0.4.txt \
  --aux-dir reference/eqtb_aux \
  --out outputs/surah_67_full
```

This command is retained for reproducing/inspecting the earlier integration. Its enriched CSV outputs copy source fields for analysis; do not treat those outputs as the final new annotation dataset.

## Immediate next task

Design and implement **read-only source adapters and a source-reference resolver**, then create a Surah Al-Mulk phrase annotation proof of concept. The first deliverable should contain only new annotation records plus source references, not copied source rows.
