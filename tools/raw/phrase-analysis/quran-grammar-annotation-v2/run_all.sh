#!/usr/bin/env bash
# Rebuild both annotation layers, validate them, run the learner-question test, then generate the sequence CSVs
# (which are computed from the two JSON layers only). Python 3.9+; the only dependency is openpyxl.
set -euo pipefail
cd "$(dirname "$0")"
python3 src/build_grammar.py
python3 src/validate.py
python3 tests/question_checks.py
python3 src/make_examples.py
python3 src/generate_sequences.py
