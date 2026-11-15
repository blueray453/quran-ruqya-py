# v7.1 changes for quran-annotations-bangla-full-chatgpt

Validated against the v6 tree: `py_compile` clean, offline smoke test passed,
10/10 regression tests passed, mock retry paths (`--mock-invalid-once`,
`--mock-flaky`) resolved correctly, and the patch was round-trip applied to a
pristine copy and byte-compared.

## What changed

1. **Strict JSON schema** (`tools/run_llm.py`)
   - New `annotation_schema(key)`: minimal strict schema (types, required,
     `additionalProperties: false`) declaring the single `surah:ayah` key.
   - Attached via `response_format` on every single-ayah request (main, long,
     retry, coarse refine, escalate). Multi-ayah batches cannot declare dynamic
     keys, so they run without the schema and the run prints a note once
     (use `--max-ayahs 1` for full enforcement).
   - Deliberately no `minLength`/`minItems`: some strict-mode implementations
     reject those keywords. Emptiness/coverage stay with the existing validator.
   - `--no-schema` disables it; attempts record `response_schema`.

2. **Self-healing 400 fallback** (`call_openrouter`)
   - On HTTP 400 the request is retried with optional params dropped one at a
     time, in order: `response_format` -> `reasoning` -> `temperature`.
   - Practical effect: running `--reasoning low` on a GPT-6-family model (which
     accepts sampling params only at effort none/off) no longer hard-fails; the
     temperature is dropped automatically with a one-time warning. Same for
     providers that reject schema mode.

3. **`--retry-temperature` (default 0.3)** — retry and coarse-refine temperature
   is now a flag instead of a magic constant, so the one honest open question
   from v6 (did 0.3 matter, or did the hint?) is directly A/B-testable.

4. **`smoke_test.sh` honours `MODEL` env var** — `MODEL=z-ai/glm-4.6 ./smoke_test.sh`
   runs the identical pilot on another model. `TAG` already was env-driven.

5. **New `tools/compare_runs.py`** — compares run dirs on the metrics that
   matter: first-pass invalids by error class (parse vs boundary), retry
   resolution, review flags, coarse flags, chunk-size distribution, cost.
   Usage: `python3 tools/compare_runs.py runs/BASE runs/A [runs/B ...]`

## Apply

From the project root (`quran-annotations-bangla-full-chatgpt/`):

    patch -p1 < /path/to/v71.patch
    cp /path/to/compare_runs.py tools/

## Run matrix — one variable per run (seed 2026 pilot, ~$0.02–0.03 each)

Baseline for every comparison: the existing v6 run (2 first-pass invalids,
21 review flags, 19 coarse flags, $0.0187).

    ./smoke_test_offline.sh                                # 0. no API cost, must pass
    TAG=luna_schema_smoke ./smoke_test.sh                  # 1. schema ON (only change vs v6)
    TAG=glmflash_smoke MODEL=z-ai/glm-5.3-flash ./smoke_test.sh   # 2. model swap vs run 1
    TAG=glm46_smoke   MODEL=z-ai/glm-4.6      ./smoke_test.sh     # 3. model swap vs run 1
    python3 tools/run_llm.py --ayahs 2:196,2:255,2:282,4:12 --tag luna_reason_low \
        --reasoning low --long-reasoning low               # 4. reasoning lever on hard ayahs
    python3 tools/compare_runs.py runs/gpt6_luna_v6_smoke runs/luna_schema_smoke \
        runs/glmflash_smoke runs/glm46_smoke

After each run: compare flags with `compare_runs.py`, and for any new model
have a Bangla reader spot-check ~10 `bn` fragments (register, honorifics,
terminology) — mechanical QA checks coverage and terminology, not quality.

If a candidate matches or beats the baseline, run the full Quran with
`--max-ayahs 1 --schema` (schema needs single-ayah requests) and keep
`--escalate-model` on a different model family as an independent second
opinion on flagged ayahs.

## Housekeeping

- `rm -rf runs/gpt6_luna_v7_smoke` — declared void; do not ship it in evidence
  archives.
- `runs/` inside any tarball adds ~2 MB of noise; exclude it from future archives
  or archive only `annotations/` + `raw/` + event logs.
