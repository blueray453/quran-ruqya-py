#!/usr/bin/env bash
# The whole pipeline, one Python file per stage, bound together here.
#   ./run_all.sh            run every stage
#   ./run_all.sh 04 05      run only the named stages (each needs the earlier stages' output)
# Python 3.9+, one dependency: openpyxl (reads CAMorphFeatures.xlsx).
set -euo pipefail
cd "$(dirname "$0")"

stages=("$@"); [ ${#stages[@]} -eq 0 ] && stages=(01 02 03 04 05 06 07)
for s in "${stages[@]}"; do
  case "$s" in
    01) echo "=== 01 normalize        data/ -> build/ (and proves the supplied normalized file is reproduced exactly)"
        python3 pipeline/01_normalize.py ;;
    02) echo "=== 02 build JSON       -> output/ (word layer + sentence layer)"
        python3 pipeline/02_build_json.py ;;
    03) echo "=== 03 validate JSON    lossless round trip, alignment, derived fields"
        python3 pipeline/03_validate_json.py
        echo
        echo ">>> CHECKPOINT: the JSON layers are built and validated."
        echo ">>> Decide which questions must be answerable (docs/QUESTIONS.md), add queries/qNN_*.py scripts, then rely on stages 04-07." ;;
    04) echo "=== 04 generate CSV     POS / function sequence CSVs (from the JSON only)"
        python3 pipeline/04_generate_csv.py ;;
    05) echo "=== 05 analysis         verb forms, derived nouns, frequencies, complete source-issue lists (from the JSON only)"
        python3 pipeline/05_analysis.py ;;
    06) echo "=== 06 docs             docs/QUESTIONS.md and docs/examples/"
        python3 pipeline/06_docs.py ;;
    07) echo "=== 07 query self-test  every question script on a known example"
        python3 queries/_self_test.py ;;
    *)  echo "unknown stage $s (use 01..07)"; exit 2 ;;
  esac
  echo
done
