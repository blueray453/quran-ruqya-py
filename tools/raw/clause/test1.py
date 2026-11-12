import csv
import json
from pathlib import Path
from collections import Counter

output = Path("outputs/surah_67")

# Load clause candidates
with (output / "clause_candidates_surah_67.csv").open(encoding="utf-8-sig", newline="") as f:
    candidates = list(csv.DictReader(f))

print("Total candidate records:", len(candidates))

# Inspect the available columns
if candidates:
    print("\nAvailable columns:")
    print(*candidates[0].keys(), sep="\n")

# Examine constituent categories
for column in ["constituent_label", "rel_label", "pos"]:
    counts = Counter(row.get(column, "").strip() for row in candidates if row.get(column, "").strip())

    print(f"\n{column}:")
    for label, count in counts.most_common():
        print(f"  {label}: {count}")

# Inspect actual examples
important_columns = [
    "tid",
    "sentence_id",
    "location",
    "uthmani_token",
    "pos",
    "rel_label",
    "ref_token_id",
    "is_constituent",
    "constituent_position",
    "constituent_label",
    "constituents",
    "candidate_reason",
]

print("\nFirst 15 candidates:")
for row in candidates[:15]:
    print({key: row.get(key) for key in important_columns if key in row})

# Inspect duplicate locations
with (output / "summary_surah_67.json").open(encoding="utf-8") as f:
    summary = json.load(f)

print("\nDuplicate EQTB locations:")
print(json.dumps(summary["duplicate_locations"]["eqtb"], ensure_ascii=False, indent=2))
