#!/usr/bin/env bash
# Live smoke test: pick a sample of ayahs, annotate them, check the result.
# Stops at the first error and writes runs/$TAG/STOPPED.md. Re-run the same command to resume.
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${MODEL:-anthropic/claude-haiku-5.5}"
TAG="${TAG:-haiku_smoke}"
SEED="${SEED:-2026}"
: "${OPENROUTER_API_KEY:?export OPENROUTER_API_KEY=sk-or-... first}"

mkdir -p "runs/$TAG"
# 1. sample (made once; kept on resume so the same ayahs are used)
if [[ ! -f "runs/$TAG/pilot.txt" ]]; then
  python3 tools/sample_ayahs.py \
    --include '67,2:255,2:282,2:286,4:176,5:106-107' \
    --per-band '1-10:2,11-20:2,21-30:2,31-40:2,41-50:2,51-60:2,61-70:2,71-80:2,81-90:2,91-100:2,101-110:2,111-120:2,121-130:2' \
    --seed "$SEED" --out "runs/$TAG/pilot.txt"
fi

# 2. annotate (resumes automatically; exits 1 and writes STOPPED.md on first error)
python3 tools/annotate.py --tag "$TAG" --model "$MODEL" --pilot "runs/$TAG/pilot.txt" --workers 2

# 3. check
python3 qa.py --annotations-dir "runs/$TAG/annotations" --no-baseline
echo "SMOKE TEST PASSED -> runs/$TAG/annotations/"
