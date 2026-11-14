import csv
from collections import Counter
from pathlib import Path

path = Path("outputs/surah_67_full/"
            "eqtb_tokens_enriched_surah_67.csv")

with path.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

fields = [
    "verb_mood",
    "special_group",
    "nominal_case",
    "derived_nouns",
    "nominal_state",
    "number",
    "verb_form",
    "verb_aspect",
    "verb_voice",
    "gender",
    "person",
    "prefix",
    "suffix",
]

for field in fields:
    print(f"\n=== {field} ===")

    values = Counter((row.get(field) or "").strip() or "<EMPTY>" for row in rows)

    for value, count in values.most_common(20):
        print(f"{value!r}: {count}")

    match_field = f"{field}_codebook_match"

    matches = Counter((row.get(match_field) or "").strip() or "<EMPTY>" for row in rows)

    print("Mapping status:", dict(matches))
