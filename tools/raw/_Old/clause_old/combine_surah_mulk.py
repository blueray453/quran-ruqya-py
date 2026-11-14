#!/usr/bin/env python3
"""Proof of concept: align EQTB and Quranic Arabic Corpus (QAC) for Surah Al-Mulk.

Inputs
------
1) EQTB: ``Primary Quranic.csv`` from the Mendeley dataset.
2) QAC:  ``quranic-corpus-morphology-0.4.txt`` downloaded from the official
   Quranic Arabic Corpus download page.

Outputs
-------
- eqtb_surah_67.csv: EQTB rows for Surah 67.
- qac_surah_67.csv: QAC morphology rows for Surah 67.
- aligned_surah_67.csv: outer join on the four-part Quranic location.
- clause_candidates_surah_67.csv: EQTB rows worth reviewing as possible
  clause/constituent evidence. These are candidates, NOT validated clause labels.
- summary_surah_67.json: alignment counts and warnings.

Important methodological note
-----------------------------
This script uses QAC's downloadable morphology file. The official download page
asks the user to enter a contact email and agree to QAC's terms. That download
is not a complete bulk export of all QAC syntactic tree structures. Therefore,
this proof of concept compares EQTB syntax with QAC morphology/grammatical tags;
it does not claim to merge the full QAC syntactic treebank.

The script preserves source fields under ``eqtb_`` and ``qac_`` prefixes. It
never overwrites one source's analysis with the other's.

Dependencies: Python 3.9+ (standard library only).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

SURAH_DEFAULT = 67
LOCATION_RE = re.compile(r"^\(?\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)\s*\)?$")

# Possible column names encountered in exported/treebank CSVs.
ALIASES = {
    "location": ("location", "loc", "quran_location"),
    "surah": ("chapter_id", "surah", "chapter", "sura"),
    "ayah": ("verse_id", "ayah_id", "ayah", "verse"),
    "word": ("word_id", "word", "token_word_id"),
    "segment": ("tok_id", "token_id", "segment_id", "segment", "token_in_word"),
}

CLAUSE_CONSTITUENT_CODES = {"S", "NS", "VS", "CS", "SC"}
DEPENDENCY_CANDIDATE_CODES = {
    "cond", "rslt", "circ", "caus", "prp", "impv", "pro", "intg", "emph",
    "condition", "result", "conditional", "sub", "relative", "purpose",
}
ARABIC_RELATION_HINTS = ("شرط", "جواب", "حال", "سبب", "تعليل", "صلة", "نهي", "أمر", "استفهام", "توكيد")


def normalized_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")


def first_value(row: Dict[str, str], names: Iterable[str]) -> Optional[str]:
    """Get the first non-empty field using case/spacing-insensitive names."""
    by_norm = {normalized_key(k): v for k, v in row.items() if k is not None}
    for name in names:
        value = by_norm.get(normalized_key(name))
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def parse_location(value: Optional[str]) -> Optional[Tuple[int, int, int, int]]:
    if value is None:
        return None
    match = LOCATION_RE.match(str(value).strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def make_location_from_columns(row: Dict[str, str]) -> Optional[Tuple[int, int, int, int]]:
    parts = []
    for key in ("surah", "ayah", "word", "segment"):
        raw = first_value(row, ALIASES[key])
        if raw is None:
            return None
        # CSV exports occasionally serialize integer columns as e.g. "67.0".
        try:
            number = int(float(raw))
        except ValueError:
            return None
        parts.append(number)
    return tuple(parts)  # type: ignore[return-value]


def location_key(parts: Tuple[int, int, int, int]) -> str:
    return ":".join(str(x) for x in parts)


def detect_text_encoding(path: Path, requested: str = "auto") -> str:
    """Detect common Unicode encodings from a BOM or UTF-16 null-byte pattern.

    CSV exports from spreadsheet applications are often UTF-16 LE with a BOM.
    Python's ``utf-16`` codec consumes that BOM and selects the correct byte order.
    An explicit encoding can be supplied with --eqtb-encoding or --qac-encoding.
    """
    if requested and requested.lower() != "auto":
        return requested

    with path.open("rb") as handle:
        sample = handle.read(8192)

    if sample.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"

    # Detect UTF-16 files that do not include a BOM. ASCII CSV headers and
    # delimiters produce a regular pattern of zero bytes in one byte position.
    if sample and b"\x00" in sample:
        even_nulls = sum(sample[i] == 0 for i in range(0, len(sample), 2))
        odd_nulls = sum(sample[i] == 0 for i in range(1, len(sample), 2))
        if max(even_nulls, odd_nulls) >= max(2, len(sample) // 20):
            return "utf-16-be" if even_nulls > odd_nulls else "utf-16-le"

    return "utf-8-sig"


def sniff_csv_delimiter(path: Path, encoding: str = "auto") -> str:
    resolved_encoding = detect_text_encoding(path, encoding)
    with path.open("r", encoding=resolved_encoding, newline="") as handle:
        sample = handle.read(8192)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def load_eqtb(
    path: Path, surah: int, encoding: str = "auto"
) -> Tuple[List[Dict[str, str]], List[str]]:
    resolved_encoding = detect_text_encoding(path, encoding)
    delimiter = sniff_csv_delimiter(path, resolved_encoding)
    rows: List[Dict[str, str]] = []
    warnings: List[str] = []

    with path.open("r", encoding=resolved_encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("EQTB CSV has no header row.")

        for row_number, raw in enumerate(reader, start=2):
            row = {str(k).strip(): (v or "").strip() for k, v in raw.items() if k is not None}
            raw_location = first_value(row, ALIASES["location"])
            parts = parse_location(raw_location) or make_location_from_columns(row)
            if parts is None:
                # Ignore genuinely empty rows, but report rows that look populated.
                if any(v for v in row.values()):
                    warnings.append(f"EQTB row {row_number}: could not parse a four-part location.")
                continue
            if parts[0] != surah:
                continue

            row["_location_key"] = location_key(parts)
            row["_surah"] = str(parts[0])
            row["_ayah"] = str(parts[1])
            row["_word"] = str(parts[2])
            row["_segment"] = str(parts[3])
            row["_source_row"] = str(row_number)
            rows.append(row)

    if not rows:
        raise ValueError(
            f"No EQTB rows found for Surah {surah}. Check the CSV and its location columns."
        )
    return rows, warnings


def find_qac_header(lines: List[str]) -> Optional[int]:
    for i, line in enumerate(lines):
        upper = line.upper()
        if "LOCATION" in upper and "FORM" in upper and "TAG" in upper:
            return i
    return None


def load_qac_morphology(
    path: Path, surah: int, encoding: str = "auto"
) -> Tuple[List[Dict[str, str]], List[str]]:
    """Parse QAC's tab-separated morphology file (LOCATION, FORM, TAG, FEATURES)."""
    resolved_encoding = detect_text_encoding(path, encoding)
    text = path.read_text(encoding=resolved_encoding)
    lines = text.splitlines()
    header_index = find_qac_header(lines)
    start = header_index + 1 if header_index is not None else 0

    rows: List[Dict[str, str]] = []
    warnings: List[str] = []

    for line_number, line in enumerate(lines[start:], start=start + 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Standard QAC morphology lines are tab-separated. FEATURES can itself
        # contain punctuation, so retain all columns after TAG as one string.
        parts = line.split("\t")
        parts = [part.strip() for part in parts]
        if len(parts) < 3:
            continue

        raw_location = parts[0].strip()
        parsed = parse_location(raw_location)
        if parsed is None:
            # Ignore title/metadata/header lines; report lines that look like data.
            if re.search(r"\d+\s*:\s*\d+\s*:\s*\d+", raw_location):
                warnings.append(f"QAC line {line_number}: unrecognized location {raw_location!r}.")
            continue

        if parsed[0] != surah:
            continue

        # Headerless file or a TSV header with extra columns is also supported.
        form = parts[1] if len(parts) > 1 else ""
        tag = parts[2] if len(parts) > 2 else ""
        features = "\t".join(parts[3:]) if len(parts) > 3 else ""

        rows.append({
            "location": raw_location,
            "form": form,
            "tag": tag,
            "features": features,
            "_location_key": location_key(parsed),
            "_surah": str(parsed[0]),
            "_ayah": str(parsed[1]),
            "_word": str(parsed[2]),
            "_segment": str(parsed[3]),
            "_source_line": str(line_number),
        })

    if not rows:
        raise ValueError(
            "No QAC morphology rows found for the selected surah. "
            "Expected tab-separated rows such as: (67:1:1:1)\tFORM\tTAG\tFEATURES."
        )
    return rows, warnings


def add_occurrence_index(rows: List[Dict[str, str]]) -> None:
    counts: Counter[str] = Counter()
    for row in rows:
        key = row["_location_key"]
        row["_occurrence"] = str(counts[key])
        counts[key] += 1


def count_duplicate_locations(rows: List[Dict[str, str]]) -> Dict[str, int]:
    counts = Counter(row["_location_key"] for row in rows)
    return {key: count for key, count in counts.items() if count > 1}


def prefixed(row: Optional[Dict[str, str]], prefix: str) -> Dict[str, str]:
    if row is None:
        return {}
    return {f"{prefix}{key}": value for key, value in row.items() if not key.startswith("_")}


def build_alignment(
    eqtb_rows: List[Dict[str, str]], qac_rows: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Outer-align rows on the exact 4-part location plus duplicate occurrence."""
    add_occurrence_index(eqtb_rows)
    add_occurrence_index(qac_rows)

    eqtb_index = {(r["_location_key"], r["_occurrence"]): r for r in eqtb_rows}
    qac_index = {(r["_location_key"], r["_occurrence"]): r for r in qac_rows}
    keys = sorted(
        set(eqtb_index) | set(qac_index),
        key=lambda item: tuple(int(x) for x in item[0].split(":")) + (int(item[1]),),
    )

    output: List[Dict[str, str]] = []
    for key, occurrence in keys:
        e = eqtb_index.get((key, occurrence))
        q = qac_index.get((key, occurrence))
        if e and q:
            status = "exact_location_match"
        elif e:
            status = "eqtb_only"
        else:
            status = "qac_only"

        row: Dict[str, str] = {
            "location_key": key,
            "occurrence": occurrence,
            "alignment_status": status,
            "alignment_basis": "exact_surah_ayah_word_segment_coordinate",
        }
        row.update(prefixed(e, "eqtb_"))
        row.update(prefixed(q, "qac_"))
        output.append(row)
    return output


def relation_tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^A-Za-z0-9_]+", (value or "").lower()) if token}


def find_field(row: Dict[str, str], candidates: Iterable[str]) -> str:
    value = first_value(row, candidates)
    return value or ""


def make_clause_candidates(eqtb_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Create a review queue; do not treat these heuristics as final clause labels."""
    candidates: List[Dict[str, str]] = []
    for row in eqtb_rows:
        label = find_field(row, ("constituent_label", "constituent tag", "phrase_tag"))
        relation = find_field(row, ("rel_label", "relation", "dependency_relation"))
        relation_ar = find_field(row, ("rel_label_ar", "relation_ar", "dependency_relation_ar"))
        is_constituent = find_field(row, ("is_constituent", "constituent"))

        label_upper = label.upper()
        label_codes = set(re.findall(r"\b(?:S|NS|VS|CS|SC)\b", label_upper))
        reasons: List[str] = []
        if label_upper.strip() in CLAUSE_CONSTITUENT_CODES:
            reasons.append(f"constituent_label:{label_upper.strip()}")
        else:
            reasons.extend(f"constituent_label:{code}" for code in sorted(label_codes))

        if is_constituent.lower() in {"1", "true", "yes", "y"} and not reasons:
            reasons.append("is_constituent_flag")

        dep_codes = relation_tokens(relation)
        matched_dep = sorted(dep_codes & DEPENDENCY_CANDIDATE_CODES)
        if matched_dep:
            reasons.append("dependency_relation:" + "+".join(matched_dep))
        if any(hint in relation_ar for hint in ARABIC_RELATION_HINTS):
            reasons.append("arabic_dependency_label_hint")

        if reasons:
            candidate = {k: v for k, v in row.items() if not k.startswith("_")}
            candidate["location_key"] = row["_location_key"]
            candidate["candidate_reason"] = ";".join(reasons)
            candidate["review_status"] = "needs_manual_review"
            candidates.append(candidate)
    return candidates


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    # Stable field order: first appearance across rows.
    fieldnames: List[str] = []
    seen = set()
    for row in rows:
        for field in row:
            if field not in seen:
                seen.add(field)
                fieldnames.append(field)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run(
    eqtb_path: Path,
    qac_path: Path,
    output_dir: Path,
    surah: int,
    eqtb_encoding: str = "auto",
    qac_encoding: str = "auto",
) -> Dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    resolved_eqtb_encoding = detect_text_encoding(eqtb_path, eqtb_encoding)
    resolved_qac_encoding = detect_text_encoding(qac_path, qac_encoding)
    eqtb_rows, eqtb_warnings = load_eqtb(eqtb_path, surah, resolved_eqtb_encoding)
    qac_rows, qac_warnings = load_qac_morphology(qac_path, surah, resolved_qac_encoding)

    eqtb_duplicates = count_duplicate_locations(eqtb_rows)
    qac_duplicates = count_duplicate_locations(qac_rows)

    aligned = build_alignment(eqtb_rows, qac_rows)
    candidates = make_clause_candidates(eqtb_rows)

    write_csv(output_dir / f"eqtb_surah_{surah}.csv", eqtb_rows)
    write_csv(output_dir / f"qac_surah_{surah}.csv", qac_rows)
    write_csv(output_dir / f"aligned_surah_{surah}.csv", aligned)
    write_csv(output_dir / f"clause_candidates_surah_{surah}.csv", candidates)

    status_counts = Counter(row["alignment_status"] for row in aligned)
    summary: Dict[str, object] = {
        "surah": surah,
        "surah_name": "Al-Mulk" if surah == 67 else None,
        "inputs": {
            "eqtb_csv": str(eqtb_path),
            "eqtb_encoding": resolved_eqtb_encoding,
            "qac_morphology_txt": str(qac_path),
            "qac_encoding": resolved_qac_encoding,
        },
        "counts": {
            "eqtb_rows": len(eqtb_rows),
            "qac_morphology_rows": len(qac_rows),
            "aligned_rows": len(aligned),
            "exact_location_matches": status_counts.get("exact_location_match", 0),
            "eqtb_only_rows": status_counts.get("eqtb_only", 0),
            "qac_only_rows": status_counts.get("qac_only", 0),
            "clause_review_candidates": len(candidates),
            "eqtb_duplicate_location_keys": len(eqtb_duplicates),
            "qac_duplicate_location_keys": len(qac_duplicates),
        },
        "duplicate_locations": {
            "eqtb": eqtb_duplicates,
            "qac": qac_duplicates,
        },
        "warnings": eqtb_warnings + qac_warnings,
        "interpretation": (
            "Exact matches mean only that the four-part location strings matched. "
            "They do not prove the two sources use identical tokenization or analyses. "
            "Clause candidates are heuristic review items, not validated clause annotations."
        ),
    }
    write_json(output_dir / f"summary_surah_{surah}.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Align EQTB and QAC morphology rows for Surah Al-Mulk (67)."
    )
    parser.add_argument("--eqtb", required=True, type=Path,
                        help="Path to EQTB 'Primary Quranic.csv'.")
    parser.add_argument("--qac", required=True, type=Path,
                        help="Path to QAC quranic-corpus-morphology-0.4.txt.")
    parser.add_argument("--out", type=Path, default=Path("outputs/surah_67"),
                        help="Output directory (default: outputs/surah_67).")
    parser.add_argument("--surah", type=int, default=SURAH_DEFAULT,
                        help="Surah number (default: 67, Al-Mulk).")
    parser.add_argument(
        "--eqtb-encoding", default="auto",
        help="EQTB CSV encoding (default: auto; also accepts utf-16, utf-8-sig, etc.).",
    )
    parser.add_argument(
        "--qac-encoding", default="auto",
        help="QAC text encoding (default: auto; also accepts utf-16, utf-8-sig, etc.).",
    )
    args = parser.parse_args()

    for label, path in (("EQTB", args.eqtb), ("QAC", args.qac)):
        if not path.is_file():
            print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
            return 2

    try:
        summary = run(
            args.eqtb, args.qac, args.out, args.surah,
            eqtb_encoding=args.eqtb_encoding,
            qac_encoding=args.qac_encoding,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary["counts"], ensure_ascii=False, indent=2))
    print(f"\nWrote outputs to: {args.out.resolve()}")
    print("Review clause_candidates_* manually; they are not final clause labels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
