#!/usr/bin/env bash
# Rebuild both annotation layers, validate them, and run the learner-question acceptance test.
# Python 3.9+; the only dependency is openpyxl (reads CAMorphFeatures.xlsx).
set -euo pipefail
cd "$(dirname "$0")"
python3 src/build_grammar.py
python3 src/validate.py
python3 tests/question_checks.py
python3 src/make_examples.py
