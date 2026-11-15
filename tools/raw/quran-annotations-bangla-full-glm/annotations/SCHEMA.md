# Annotation schema 2.0 — flat phrase chunks

The Arabic segmentation is the primary annotation. There is no clause layer.

## English annotation

`annotations/surah-NNN.json`:

```json
{
  "schema_version": "2.0",
  "conventions_version": "4.0",
  "surah": 67,
  "language": "en",
  "provenance": {"generator": "llm-annotation", "model": "..."},
  "ayahs": {
    "1": {
      "status": "auto",
      "chunks": [
        {"words": [1], "en": "Blessed is"},
        {"words": [2], "en": "the One who"}
      ]
    }
  }
}
```

Each `chunks` entry is one contiguous span of Arabic **words**, numbered from 1. `words`
is always expanded to a complete ascending integer list. The English fragment must translate
only that span. Chunks tile the ayah exactly once, in source order.

## Bangla overlay

`annotations/bn/surah-NNN.json` has the same ayah keys and exactly the same `chunks[].words`
spans. Each chunk contains `bn` instead of `en`. The overlay cannot re-segment.

## Status values

`auto`, `needs_human`, and `reviewed`. The English file owns segmentation. Bangla is a
gloss-only overlay.

## Legacy compatibility

The validators and builder can still read schema 1.0 files with `clauses[].phrases[]`. New
LLM runs and new output files use schema 2.0 and a flat `chunks[]` array. Legacy clause
boundaries are not used as a target or QA constraint for new annotations.
