#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
TAG="smoke_chunks"
rm -rf "runs/${TAG}"
python3 tools/run_llm.py --surah 67 --tag "${TAG}" --mock-replay --workers 1
python3 qa.py --surah 67 --annotations-dir "runs/${TAG}/annotations"
python3 tools/chunker_report.py --surah 67 --annotations-dir "runs/${TAG}/annotations" --out "runs/${TAG}/chunker_report.md"
python3 tools/review_flags.py --annotations-dir "runs/${TAG}/annotations" --out "runs/${TAG}/review_flags.md"
python3 build.py --surah 67 --annotations-dir "runs/${TAG}/annotations" --out-dir "runs/${TAG}/data"
echo
echo "SMOKE TEST PASSED: flat chunks, exact word coverage, Bangla overlay, diagnostic report, and data build."
