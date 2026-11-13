# Architecture: Reference Sources + New Annotation Layer

## 1. Principle

Existing datasets are source-of-truth reference layers. Our dataset is an overlay containing only new information. No ETL step should create a second copy of their tokens, text, morphology, lexicons, dependencies, or codebooks as part of the released annotation dataset.

## 2. Runtime view

```text
                 Quranic Linguistic Application
                              |
                    Query / composition layer
                              |
              +---------------+----------------+
              |                                |
      New annotation store              Source adapters
              |                                |
      Phrase annotations                 EQTB (read-only)
      Clause annotations                 QAC (read-only)
      Unit relationships                 Future sources
      Classification labels              Future sources
      Evidence/reviews                    Source codebooks
              |                                |
              +------ source references ------+
```

The app asks the annotation store for a phrase/clause and follows its references through the source adapter to retrieve the Arabic text, word segmentation, morphology, roots, lemmas, POS, dependency relations, or existing constituent labels.

## 3. Reuse-versus-create decision rule

For every intended phrase/clause feature:

1. Search existing sources for the same entity/span and the same annotation meaning.
2. If the exact information already exists and is adequate, reference it. Do not copy or recreate it.
3. If the source has the entity but not the new classification, attach only the new classification to the source reference.
4. If the source does not provide the boundary/entity/relationship, create a new annotation with source-token references only.
5. If the source meaning is ambiguous or mapping is not validated, preserve the source-specific label and mark any crosswalk as provisional.

## 4. Identifiers and source references

### EQTB tokens

The observed safe token coordinate for sentence-local constituent span work is `(sentence_id, token_id)`. `tid` is also present in the main source file and can be retained as an additional source record identifier. Do not assume Quranic `location` uniquely identifies every row: implicit tokens have no ordinary Quranic location.

### EQTB constituents

`constituents_loc` contains inclusive sentence-local token-id spans. Resolve a span using its `sentence_id` and the token range. The constituent head row can also be referenced by its source `tid`.

### QAC morphology

QAC morphology locations are coordinate-based (surah:ayah:word:segment). Use them as source locators. Do not assume an EQTB token id equals a QAC token id.

### Versioning

A source reference must include a dataset key and version/release. Where possible also record a checksum of the source file, so that a changed release does not silently point to a different record.

## 5. Phrase-before-clause workflow

The project workflow uses the existing word/morphology level to help discover phrase structure. Phrase annotations can then support clause discovery and clause annotation.

This is a processing workflow, not a rigid linguistic claim that all clauses are composed only of phrases. Some phrase/clause structures are nested, some clauses may be embedded, and some constructions are better modeled with dependencies or discontinuous spans.

## 6. No-duplication policy

Do not place the following in the new annotation database unless a specific field is itself a new annotation:

- Arabic Quranic text or translations;
- EQTB or QAC token rows;
- morphology or token-level grammatical features;
- roots or lemmas;
- POS labels;
- dependency edge copies;
- EQTB codebook/lexicon records;
- existing constituent spans and labels.

Instead store identifiers such as:

- `source_dataset_key = EQTB`;
- `source_version = ...`;
- `source_entity_type = constituent`;
- `source_record_key = ...`;
- `source_locator = sentence_id:token_id` or source's canonical location.

Only create a new span if the required phrase/clause span is genuinely missing or requires an independently reviewed boundary.

## 7. Phrase and clause entity strategy

A unified `annotation_units` model can represent both phrase and clause units with `unit_level = phrase | clause`. Separate relationship and classification tables attach typed links and labels.

A unit may have:

- one exact source-entity reference (e.g. an EQTB constituent);
- multiple source evidence references;
- one or more token span segments if the boundary is new or cannot be represented by an existing source entity;
- parent/child or other typed relationships;
- multiple classifications across different dimensions.

For a source-exact entity, prefer the source entity reference rather than copying its start/end span. For a new entity, store token references as span endpoints without copying token text.

## 8. App behavior

The app should resolve source data on demand through versioned adapters. Cache only as a technical optimization, not as a second authoritative dataset. Any cache must be rebuildable and clearly separated from the new annotation records.

## 9. Licensing and attribution

Before redistribution, verify the current license and attribution requirements for every source. The EQTB source code's software license does not automatically establish the license of all data files. QAC has specific data-use requirements. Keep source attribution and license metadata in the source registry. The new annotation layer's license should be selected independently after rights review.
