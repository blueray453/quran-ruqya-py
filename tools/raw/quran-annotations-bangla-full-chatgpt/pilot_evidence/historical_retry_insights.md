# v5 retry insights

The v5 log contains four validation failures that were subsequently resolved by the first
single-ayah retry round:

| Ayah | Initial validation failure | Type |
|---|---|---|
| 67:30 | Chunk 4 starts at word 4; expected word 6 | gap / overlap / reordering |
| 2:233 | Chunk 10 starts at word 18; expected word 20 | gap / overlap / reordering |
| 4:12 | Chunk 3 starts at word 3; expected word 6 | gap / overlap / reordering |
| 24:31 | Chunk 31 starts at word 50; expected word 55 | gap / overlap / reordering |

All four ayahs were included in the retry round (`retry 1: 4 ayah(s) alone at temperature
0.3`) and the run subsequently reported 45/45 validated, zero failed. The final merged
annotations for these ayahs are present in `final_annotations/`.

## What this suggests

- The model sometimes omits or jumps over source-word positions when producing a long ordered
  chunk list.
- Strict tiling validation is doing its job: these responses were rejected rather than merged.
- Single-ayah retry resolved the structural issue in this run.
- The supplied historical evidence does not let us compare the raw invalid response with the
  raw successful retry; neither payload was archived.

V6 addresses the evidence gap by writing every request/response under `attempts/`, and each
invalid event in `retry_events.jsonl` points to the raw attempt file and the successful retry
attempt file. This permits later analysis of whether retries fix span alignment, translations,
chunk boundaries, or only formatting.
