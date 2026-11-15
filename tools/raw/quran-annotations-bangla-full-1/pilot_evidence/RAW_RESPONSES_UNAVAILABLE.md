# Historical v5 pilot evidence and raw-response limitation

The user supplied the merged annotation archive `gpt6_luna_smoke.tar.gz` and the terminal
output from the v5 live smoke test.

The archive contains final merged English annotations, final Bangla overlays, and a review
report. It does **not** contain the original OpenRouter API requests, unparsed model text,
provider response payloads, or per-attempt JSON. Therefore the exact historical raw model
responses and prompts cannot be reconstructed honestly from these files.

The numbered Arabic source text *is* available from this project’s pinned
`sources/text/indopak.json`, along with English/Bangla word-by-word glosses and full-ayah
reference translations. `source_trace.jsonl` and `final_chunks_with_arabic.jsonl` reconstruct
the exact source-word spans beside the merged output. These are source-linked final annotation
evidence, **not** raw model responses.

For the v6 evidence copy only, terminology was normalized in the final English fragments:
`Lord` → `Rabb`, and `deity` → `ilah`, where those terms occurred in chunks whose Arabic source
supports those mappings. The original uploaded TAR remains the unchanged record of the v5
merged output.

## Four v5 invalid responses resolved by retry

The supplied terminal log records four initial structural validation failures, then one retry
round for four ayahs at temperature 0.3, followed by `validated 45/45 ayahs; failed 0`. The four
initial failures and their successful resolution are recorded in
`historical_retry_events.jsonl` and summarized in `historical_retry_insights.md`.

The initial error messages are recoverable from the terminal log. The raw initial outputs and
raw retry outputs are not present in the supplied TAR/log, so each historical event explicitly
marks raw response payloads as unavailable. V6 live runs now archive full prompts, raw model
text, provider payloads, and validation outcomes under `runs/<tag>/attempts/` and link them from
`retry_events.jsonl`.
