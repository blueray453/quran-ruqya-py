import csv
from pathlib import Path
from collections import Counter

OUTPUT = Path("outputs/surah_67")

def read_csv(filename):
    path = OUTPUT / filename

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

eqtb = read_csv("eqtb_surah_67.csv")
candidates = read_csv("clause_candidates_surah_67.csv")

# 1. Inspect ALL constituent heads, not just candidates.
heads = [r for r in eqtb if r.get("is_constituent") == "1"]

print("\n=== ALL EQTB CONSTITUENT HEADS ===")
print("Total:", len(heads))

print("\nLabels:")
for label, count in Counter(r.get("constituent_label", "") for r in heads).most_common():
    print(f"{label}: {count}")

# 2. Count unique constituent spans.
print("\n=== UNIQUE CONSTITUENT SPANS ===")

for label in ["CS", "SC", "VS", "NS", "PP"]:
    records = [r for r in heads if r.get("constituent_label") == label]

    spans = {(r.get("sentence_id"), r.get("constituents_loc")) for r in records if r.get("constituents_loc")}

    print(f"{label}: {len(records)} records, "
          f"{len(spans)} unique spans")

# 3. Display actual span encoding.
print("\n=== CONSTITUENT SPAN EXAMPLES ===")

for label in ["CS", "SC", "VS", "NS", "PP"]:
    print(f"\n--- {label} ---")

    records = [r for r in heads if r.get("constituent_label") == label]

    for r in records[:5]:
        print({
            "sentence_id": r.get("sentence_id"),
            "token_id": r.get("token_id"),
            "location": r.get("location"),
            "constituent_label": r.get("constituent_label"),
            "constituents_loc": r.get("constituents_loc"),
            "constituents": r.get("constituents"),
        })

# 4. Inspect inserted/implicit tokens.
print("\n=== ZERO-WORD LOCATION RECORDS ===")

zero_word = [r for r in eqtb if r.get("word_id") == "0"]

print("Total:", len(zero_word))

for r in zero_word[:30]:
    print({
        "tid": r.get("tid"),
        "token_id": r.get("token_id"),
        "sentence_id": r.get("sentence_id"),
        "sentence_word": r.get("sentence_word"),
        "location": r.get("location"),
        "uthmani_token": r.get("uthmani_token"),
        "trans": r.get("trans"),
        "pos": r.get("pos"),
        "rel_label": r.get("rel_label"),
    })

# 5. Check whether a sentence crosses verse boundaries.
print("\n=== SENTENCE 10823 ===")

sentence = [r for r in eqtb if r.get("sentence_id") == "10823"]

for r in sentence:
    print(r.get("location"), r.get("uthmani_token"), r.get("pos"))
