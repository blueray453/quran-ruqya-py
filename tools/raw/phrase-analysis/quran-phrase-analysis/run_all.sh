#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 src/normalize.py --data-dir data --results-dir results
python3 src/analyze.py   --results-dir results
