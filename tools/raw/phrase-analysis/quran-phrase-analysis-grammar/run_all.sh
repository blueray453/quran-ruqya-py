#!/usr/bin/env bash
# Runs the whole pipeline: normalization, main analysis, exact-diacritics analysis, database comparison.
set -euo pipefail
cd "$(dirname "$0")"
python3 src/normalize.py --data-dir data --results-dir results
python3 src/analyze.py   --results-dir results                                   # main (normalized spelling)
python3 src/analyze.py   --results-dir results --field exact --out-dir results/exact-diacritics   # strict spelling
python3 src/compare_representations.py --data-dir data --results-dir results     # lemma / stem / root comparison
