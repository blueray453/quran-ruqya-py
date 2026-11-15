#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

MODEL="openai/gpt-6-luna"
TAG="${TAG:-gpt6_luna_smoke}"
SEED="${SEED:-2026}"

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  cat >&2 <<'EOF'
ERROR: OPENROUTER_API_KEY is not set.

Create an API key in OpenRouter, then run:
  export OPENROUTER_API_KEY="sk-or-..."
  ./smoke_test.sh

This is the LIVE smoke test and makes paid model calls. For an offline-only
pipeline check (no API key and no model calls), run:
  ./smoke_test_offline.sh
EOF
  exit 2
fi

# The required examples count toward the two-per-band target.
INCLUDE='2:255,2:282,2:286,4:176,5:106-107'
BANDS='1-10:2,11-20:2,21-30:2,31-40:2,41-50:2,51-60:2,61-70:2,71-80:2,81-90:2,91-100:2,101-110:2,111-120:2,121-130:2'

rm -rf "runs/${TAG}"
mkdir -p "runs/${TAG}"

printf '\n=== 1. Build stratified pilot sample ===\n'
python3 tools/sample_ayahs.py \
  --include "$INCLUDE" \
  --per-band "$BANDS" \
  --seed "$SEED" \
  --out "runs/${TAG}/pilot.txt"

printf '\n=== 2. Live annotation via OpenRouter: %s ===\n' "$MODEL"
python3 tools/run_llm.py \
  --pilot "runs/${TAG}/pilot.txt" \
  --tag "$TAG" \
  --model "$MODEL" \
  --long-model '' \
  --escalate-model '' \
  --max-ayahs 1 \
  --workers 2 \
  --reasoning low \
  --long-reasoning low \
  --retries 1 \
  --coarse-retries 0

printf '\n=== 3. Verify every selected ayah received a validated response ===\n'
python3 - "$TAG" <<'PY'
import json, sys
from pathlib import Path

tag = sys.argv[1]
run = Path('runs') / tag
expected = []
for line in (run / 'pilot.txt').read_text(encoding='utf-8').splitlines():
    key = line.split('#', 1)[0].strip()
    if key:
        expected.append(key)
failed = json.loads((run / 'failed.json').read_text(encoding='utf-8'))
missing = [key for key in expected
           if not (run / 'raw' / (f'{int(key.split(":")[0]):03d}-{int(key.split(":")[1]):03d}.json')).exists()]
if failed or missing:
    print('FAIL: failed ayahs:', json.dumps(failed, ensure_ascii=False))
    print('FAIL: missing raw results:', missing)
    raise SystemExit(1)
print(f'PASS: {len(expected)} selected ayahs have validated model responses')
PY

printf '\n=== 4. QA: Arabic coverage, English chunks, Bangla overlay, source integrity ===\n'
python3 qa.py --annotations-dir "runs/${TAG}/annotations" --no-baseline

printf '\n=== 5. Review flags and diagnostic reports ===\n'
python3 tools/review_flags.py --annotations-dir "runs/${TAG}/annotations" --out "runs/${TAG}/review_flags.md"
python3 tools/chunker_report.py --annotations-dir "runs/${TAG}/annotations" --out "runs/${TAG}/chunker_report.md"

printf '\n=== 6. Build reader data ===\n'
python3 build.py --annotations-dir "runs/${TAG}/annotations" --out-dir "runs/${TAG}/data"

printf '\nLIVE SMOKE TEST PASSED\n'
printf 'Model: %s\nSample manifest: runs/%s/pilot.txt\nResults: runs/%s/\n' "$MODEL" "$TAG" "$TAG"
printf 'Review: runs/%s/review_flags.md\n' "$TAG"
printf 'API usage/cost is reported by run_llm.py above.\n'
