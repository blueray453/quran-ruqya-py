#!/usr/bin/env bash
# The whole pipeline, one Python file per stage, bound together here.
#   ./run_all.sh            run every stage
#   ./run_all.sh 07 08      run only the named stages (each needs the earlier stages' output)
# Python 3.9+, one dependency: openpyxl (reads CAMorphFeatures.xlsx).
set -euo pipefail
cd "$(dirname "$0")"

stages=("$@"); [ ${#stages[@]} -eq 0 ] && stages=(01 02 03 04 05 06 07 08 09 10 11 12)
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
        echo ">>> Decide which questions must be answerable (docs/QUESTIONS.md), add queries/qNN_*.py scripts, then rely on stages 04-12." ;;
    04) echo "=== 04 sequences        POS / function sequence tables + memorization orders (output/sequences, output/memorization-order)"
        python3 pipeline/04_generate_csv.py ;;
    05) echo "=== 05 analysis         verb forms, derived nouns, frequencies, source-issue lists (output/analysis)"
        python3 pipeline/05_analysis.py ;;
    06) echo "=== 06 phrases          repeated Arabic words / phrases + memorization orders (output/phrases)"
        python3 pipeline/06_phrases.py ;;
    07) echo "=== 07 lexicon tables   root families, forms, paradigms, pronouns, affixes, hapax ... (output/lexicon)"
        python3 pipeline/07_lexicon_tables.py ;;
    08) echo "=== 08 syntax tables    case, valency, prepositions, idafa, particles, implicit, constituents (output/syntax)"
        python3 pipeline/08_syntax_tables.py ;;
    09) echo "=== 09 reading tables   surah / ayah vocabulary load + memorization orders for words, roots, verbs, ayahs"
        python3 pipeline/09_reading_tables.py ;;
    10) echo "=== 10 validate tables  every table reconciled with the JSON and with the other tables"
        python3 pipeline/10_validate_tables.py ;;
    11) echo "=== 11 docs             docs/QUESTIONS.md and docs/examples/"
        python3 pipeline/11_docs.py ;;
    12) echo "=== 12 query self-test  every question script on a known example"
        python3 queries/_self_test.py ;;
    *)  echo "unknown stage $s (use 01..12)"; exit 2 ;;
  esac
  echo
done
