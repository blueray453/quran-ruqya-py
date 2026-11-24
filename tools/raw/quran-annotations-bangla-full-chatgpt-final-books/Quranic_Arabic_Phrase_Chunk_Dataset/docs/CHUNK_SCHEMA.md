# Chunk dataset schema and query examples

## Stable unit model

A **chunk occurrence** is a specific span or relation-derived teaching unit in one Quran location. `chunk_id` identifies that occurrence within this build. It is not a global lexical or grammar type ID.

The dataset distinguishes:

- `chunk_family`: evidence/teaching layer (for example `source_constituent`, `idafi`, `jarri`, `fa_il`, `conditional`).
- `construction_type`: learner-facing construction label where one can be mapped.
- `source_type`: origin of the row, such as an explicit source constituent or a dependency relation.
- `certainty` / `review_required` / `review_reason`: whether the mapping is direct evidence, a conservative candidate, or requires a teacher.
- `member_word_ids`: ordered written-word IDs covered by the chunk.
- `source_relations`: relation labels that support a dependency-derived chunk.

## Occurrence table

`quran_chunk_occurrences.csv` has one row per explicit Treebank constituent or selected dependency-derived unit. Important columns:

| Column | Meaning |
|---|---|
| `chunk_id` | Unique ID for one located occurrence |
| `chunk_family` | Dataset family, such as `idafi`, `tawsifi`, `jarri`, `atfi`, `ishari`, `badali_candidate`, `source_constituent`, `fa_il`, `maf_ul_bih` |
| `construction_type` | Pedagogical construction name, if mapped |
| `chunk_level` | Broad layer such as phrase, clause, sentence or lexical pattern |
| `source_type` | Source annotation / relation method |
| `certainty` | Mapping confidence/evidence class used by this build |
| `source_sentence_id` | Treebank sentence record ID |
| `source_label` | Original QAC constituent tag or relation label |
| `surah`, `ayahs` | Quran reference; `ayahs` may be multiple for a cross-ayah source span |
| `start_word_id`, `end_word_id` | First and last ordered word IDs |
| `word_count` | Number of written words represented |
| `is_contiguous_word_span` | Whether the member words occupy one contiguous span |
| `crosses_ayah` | Whether members cross an ayah boundary |
| `member_word_ids` | Ordered member word IDs, JSON array in CSV cell |
| `member_text_indopak`, `member_text_uthmani`, `member_text_normalized` | Ordered member text representations |
| `span_text_*` | Rendered span forms |
| `head_word_id`, `dependent_word_id` | Dependency pair endpoints when relation-derived |
| `head_pos`, `dependent_pos` | Source POS values of relation endpoints |
| `same_written_word` | Whether two relation endpoints occupy one written word but distinct segments |
| `review_required`, `review_reason` | Explicit review status |

## Member table

`quran_chunk_members.csv` has one row per written-word member inside a chunk. A written word may contain multiple morphological segments. The `segment_id`, `token_id`, `segment_type`, `features_raw`, `prefix_tags` and `suffix_tags` fields preserve that distinction. `member_role` says how the word functions in this chunk; POS/feature fields remain source annotations.

## Source dependency table

`quran_dependency_edges.csv` includes all overt non-root dependency edges used in extraction. It preserves source relation name and endpoints. It is an audit/reference table, not a list of phrases.

## Hierarchy and curriculum link tables

- `quran_chunk_hierarchy.csv`: strict span containment only. A parent-child link is a navigation aid and does not itself establish a grammatical dependency.
- `quran_chunk_curriculum_links.csv`: many-to-many concept map from occurrence IDs to curriculum IDs. A link is a retrieval/use suggestion, not a claim that the chunk demonstrates every sub-rule in full.
- `curriculum_concept_map.csv`: curriculum IDs and the intended teaching use.

## Repeated lexical chunk tables

- `repeated_lexical_chunk_types.csv`: one row per repeated contiguous n-gram phrase type; normalized and exact-diacritic matching remain separate.
- `repeated_lexical_chunk_occurrences.csv`: one row per specific occurrence of a repeated lexical type.

These strings are practice candidates. They do not receive a grammar construction label merely because they repeat.

## Python query examples

From the project root:

```python
import csv
from pathlib import Path

csv_dir = Path("output/csv")
with (csv_dir / "quran_chunk_occurrences.csv").open(encoding="utf-8-sig", newline="") as f:
    chunks = list(csv.DictReader(f))

# Retrieve conservative Idafah examples.
idafi = [r for r in chunks if r["chunk_family"] == "idafi"]

# Retrieve nominal and verbal sentence spans as separate source tags.
sentence_spans = [
    r for r in chunks
    if r["chunk_family"] == "source_constituent"
    and r["source_label"] in {"NS", "VS"}
]

# Retrieve teacher-review Badali candidates; do not use as confirmed answer keys.
badali_candidates = [r for r in chunks if r["chunk_family"] == "badali_candidate"]

# Get all chunk-member rows for a selected occurrence.
chunk_id = idafi[0]["chunk_id"]
with (csv_dir / "quran_chunk_members.csv").open(encoding="utf-8-sig", newline="") as f:
    members = [r for r in csv.DictReader(f) if r["chunk_id"] == chunk_id]
```

For large tables, stream with `csv.DictReader` and filter row by row rather than loading the complete file into memory.
