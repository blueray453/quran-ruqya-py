#!/usr/bin/env python3
"""Extract clause-like constituent spans from EQTB for Surah Al-Mulk.

Input:
  eqtb_surah_67.csv produced by combine_surah_mulk.py
Optional:
  aligned_surah_67.csv produced by combine_surah_mulk.py

Outputs:
  constituents_surah_67.csv       All EQTB constituent spans, including PP.
  clauses_surah_67.csv            Clause-like spans (S/NS/VS/CS/SC).
  clause_tokens_surah_67.csv      Token rows belonging to each clause span.
  clause_extraction_summary.json  Counts, warnings, and extraction checks.

Important:
- constituents_loc is interpreted as a sentence-local token_id range.
- Tokens are selected using (sentence_id, token_id), not Quranic word location.
- Nested/overlapping constituents are preserved.
- EQTB's `constituents` field is retained as its supplied span text. A diagnostic
  token sequence is also emitted, but is not treated as display-ready Arabic
  because one Arabic word may be split into multiple morphological segments.
- This extracts syntactic constituent candidates; it does not claim that every
  VS/NS/SC/CS label is a fully validated independent clause.

Python 3.9+, standard library only.
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

SPAN_RE = re.compile(r"^\s*\[?\s*(\d+)\s*[-–:]\s*(\d+)\s*\]?\s*$")
LOCATION_RE = re.compile(r"^\(?\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)\s*\)?$")

CLAUSE_LABELS = {"S", "NS", "VS", "CS", "SC"}
ALL_CONSTITUENT_LABELS = CLAUSE_LABELS | {"PP"}
STRUCTURE_MAP = {
    "S": "sentence_constituent_candidate",
    "NS": "nominal_clause_candidate",
    "VS": "verbal_clause_candidate",
    "CS": "conditional_construction_candidate",
    "SC": "subordinate_construction_candidate",
    "PP": "prepositional_phrase",
}


def detect_encoding(path: Path, requested: str = "auto") -> str:
    if requested.lower() != "auto":
        return requested
    sample = path.read_bytes()[:8192]
    if sample.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if sample and b"\x00" in sample:
        even = sum(sample[i] == 0 for i in range(0, len(sample), 2))
        odd = sum(sample[i] == 0 for i in range(1, len(sample), 2))
        if max(even, odd) >= max(2, len(sample) // 20):
            return "utf-16-be" if even > odd else "utf-16-le"
    return "utf-8-sig"


def sniff_delimiter(path: Path, encoding: str) -> str:
    with path.open("r", encoding=encoding, newline="") as f:
        sample = f.read(8192)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def read_csv(path: Path, requested_encoding: str = "auto") -> List[Dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    encoding = detect_encoding(path, requested_encoding)
    delimiter = sniff_delimiter(path, encoding)
    with path.open("r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError(f"No header row found in {path}")
        rows = []
        for raw in reader:
            rows.append({str(k).strip(): (v or "").strip()
                         for k, v in raw.items() if k is not None})
    return rows


def parse_span(value: str) -> Optional[Tuple[int, int]]:
    if not value:
        return None
    match = SPAN_RE.match(value)
    if not match:
        return None
    start, end = int(match.group(1)), int(match.group(2))
    if start > end:
        return None
    return start, end


def safe_int(value: str) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_location(value: str) -> Optional[Tuple[int, int, int, int]]:
    match = LOCATION_RE.match((value or "").strip())
    return tuple(map(int, match.groups())) if match else None


def verse_numbers(rows: Iterable[Dict[str, str]]) -> List[int]:
    values = set()
    for row in rows:
        verse = safe_int(row.get("verse_id", ""))
        if verse is None:
            loc = parse_location(row.get("location", ""))
            if loc:
                verse = loc[1]
        if verse is not None and verse > 0:
            values.add(verse)
    return sorted(values)


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: List[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_optional_alignment(path: Optional[Path], encoding: str) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    """Index QAC morphology by EQTB global tid where possible.

    `aligned_surah_67.csv` is generated by the companion merger. Joining by
    eqtb_tid avoids treating synthetic word_id=0 coordinates as real matches.
    """
    if path is None:
        return {}, []
    rows = read_csv(path, encoding)
    index: Dict[str, Dict[str, str]] = {}
    warnings: List[str] = []
    for row in rows:
        tid = row.get("eqtb_tid", "").strip()
        if not tid:
            continue
        if tid in index:
            warnings.append(f"Multiple alignment rows for EQTB tid={tid}; QAC fields not attached.")
            index.pop(tid, None)
            continue
        index[tid] = row
    return index, warnings


def run(eqtb_path: Path, out_dir: Path, surah: int,
        aligned_path: Optional[Path] = None,
        encoding: str = "auto") -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_csv(eqtb_path, encoding)
    if not rows:
        raise ValueError("EQTB input contains no data rows.")

    required = {"sentence_id", "token_id", "constituent_label", "constituents_loc"}
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(
            "EQTB file is missing required columns: " + ", ".join(missing) +
            ". Use eqtb_surah_67.csv from the combine script, not the candidate-only file."
        )

    # Retain only the requested surah. The generated EQTB export usually has
    # chapter_id, including on inserted/implicit tokens whose location is '_'.
    filtered: List[Dict[str, str]] = []
    for row in rows:
        chapter = safe_int(row.get("chapter_id", ""))
        if chapter is not None:
            if chapter == surah:
                filtered.append(row)
            continue
        loc = parse_location(row.get("location", ""))
        if loc and loc[0] == surah:
            filtered.append(row)
        elif not row.get("location") and not row.get("chapter_id"):
            # Input may already be a surah-only file; retain rows only if it is
            # explicitly supplied as the source for this run.
            filtered.append(row)

    if not filtered:
        raise ValueError(f"No EQTB rows found for Surah {surah}.")

    by_sentence: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    token_lookup: Dict[Tuple[str, int], Dict[str, str]] = {}
    duplicate_local_ids: List[str] = []
    for row in filtered:
        sentence_id = row.get("sentence_id", "").strip()
        token_id = safe_int(row.get("token_id", ""))
        if not sentence_id or token_id is None:
            continue
        key = (sentence_id, token_id)
        if key in token_lookup:
            duplicate_local_ids.append(f"sentence_id={sentence_id}, token_id={token_id}")
        else:
            token_lookup[key] = row
        by_sentence[sentence_id].append(row)

    for sentence_id in by_sentence:
        by_sentence[sentence_id].sort(key=lambda r: safe_int(r.get("token_id", "")) or -1)

    all_constituents: List[Dict[str, object]] = []
    clause_rows: List[Dict[str, object]] = []
    token_rows: List[Dict[str, object]] = []
    warnings: List[str] = []

    qac_by_tid, alignment_warnings = load_optional_alignment(aligned_path, encoding)
    warnings.extend(alignment_warnings)
    warnings.extend([f"Duplicate local token key: {x}" for x in duplicate_local_ids])

    # First pass: collect all syntactic constituent spans (including PP).
    clause_specs: List[Dict[str, object]] = []
    malformed_spans = 0
    incomplete_spans = 0
    for head in filtered:
        if head.get("is_constituent", "").strip().lower() not in {"1", "true", "yes", "y"}:
            continue
        label = head.get("constituent_label", "").strip().upper()
        if label not in ALL_CONSTITUENT_LABELS:
            continue
        sentence_id = head.get("sentence_id", "").strip()
        head_token_id = safe_int(head.get("token_id", ""))
        span = parse_span(head.get("constituents_loc", ""))
        if not sentence_id or head_token_id is None or span is None:
            malformed_spans += 1
            warnings.append(
                f"Could not parse constituent span for tid={head.get('tid', '')}, "
                f"label={label}, value={head.get('constituents_loc', '')!r}."
            )
            continue

        start, end = span
        members = [r for r in by_sentence.get(sentence_id, [])
                   if (safe_int(r.get("token_id", "")) is not None
                       and start <= int(r["token_id"]) <= end)]
        present_ids = {safe_int(r.get("token_id", "")) for r in members}
        expected_ids = set(range(start, end + 1))
        missing_ids = sorted(expected_ids - {x for x in present_ids if x is not None})
        complete = not missing_ids and len(members) == (end - start + 1)
        if not complete:
            incomplete_spans += 1
            warnings.append(
                f"Incomplete span {sentence_id}:[{start}-{end}], label={label}; "
                f"missing token_ids={missing_ids}."
            )

        clause_id = f"{surah}-{sentence_id}-{start}-{end}-{label}"
        head_tid = head.get("tid", "").strip()
        member_tids = [r.get("tid", "").strip() for r in members]
        implicit_members = [
            r for r in members
            if (safe_int(r.get("word_id", "")) == 0
                or not parse_location(r.get("location", "")))
        ]
        member_locations = []
        for member in members:
            loc = parse_location(member.get("location", ""))
            if loc:
                member_locations.append(f"{loc[0]}:{loc[1]}:{loc[2]}:{loc[3]}")
        member_locations = list(dict.fromkeys(member_locations))
        span_text = head.get("constituents", "").strip()
        token_debug = " | ".join(
            f"{r.get('token_id', '')}:{r.get('uthmani_token', '')}"
            for r in members
        )

        spec: Dict[str, object] = {
            "clause_id": clause_id,
            "surah": surah,
            "sentence_id": sentence_id,
            "start_token_id": start,
            "end_token_id": end,
            "span_width": end - start + 1,
            "head_token_id": head_token_id,
            "head_tid": head_tid,
            "head_location": head.get("location", ""),
            "head_pos": head.get("pos", ""),
            "head_rel_label": head.get("rel_label", ""),
            "head_rel_label_ar": head.get("rel_label_ar", ""),
            "head_ref_token_id": head.get("ref_token_id", ""),
            "source_constituent_label": label,
            "proposed_structure_type": STRUCTURE_MAP[label],
            "eqtb_constituent_text": span_text,
            "verse_ids": ",".join(map(str, verse_numbers(members))),
            "member_count": len(members),
            "implicit_token_count": len(implicit_members),
            "contains_implicit_tokens": bool(implicit_members),
            "span_complete": complete,
            "missing_token_ids": ",".join(map(str, missing_ids)),
            "member_tids": ",".join(member_tids),
            "member_quran_locations": ";".join(member_locations),
            "token_id_debug_sequence": token_debug,
            "parent_clause_id": "",
            "nesting_level": 0,
        }
        all_constituents.append(dict(spec))
        if label in CLAUSE_LABELS:
            clause_specs.append({**spec, "_start": start, "_end": end, "_sentence": sentence_id})

    # Parent = smallest strictly larger clause candidate containing this span.
    for child in clause_specs:
        containers = [parent for parent in clause_specs
                      if parent["_sentence"] == child["_sentence"]
                      and parent["clause_id"] != child["clause_id"]
                      and int(parent["_start"]) <= int(child["_start"])
                      and int(parent["_end"]) >= int(child["_end"])
                      and (int(parent["_start"]) < int(child["_start"])
                           or int(parent["_end"]) > int(child["_end"]))]
        if containers:
            parent = min(containers, key=lambda x: int(x["span_width"]))
            child["parent_clause_id"] = parent["clause_id"]

    # Calculate nesting level by following parent ids.
    clause_id_set = {str(r["clause_id"]) for r in clause_specs}
    parent_map = {str(r["clause_id"]): str(r.get("parent_clause_id", ""))
                  for r in clause_specs}
    for row in clause_specs:
        current = str(row["clause_id"])
        seen = set()
        depth = 0
        parent_id = parent_map.get(current, "")
        while parent_id and parent_id in clause_id_set and parent_id not in seen:
            seen.add(parent_id)
            depth += 1
            parent_id = parent_map.get(parent_id, "")
        row["nesting_level"] = depth

    # Emit clauses (no internal helper keys).
    for spec in clause_specs:
        clause = {k: v for k, v in spec.items() if not k.startswith("_")}
        clause["clause_function"] = ""  # Requires linguistic analysis; not inferred from label alone.
        clause["speech_act"] = ""       # Requires separate annotation.
        clause["rhetorical_features"] = ""  # Multi-label; requires separate annotation.
        clause["review_status"] = "needs_linguistic_review"
        clause_rows.append(clause)

        # One row per member token per containing clause. Nested clauses
        # deliberately repeat tokens because a token can belong to multiple spans.
        members = [r for r in by_sentence.get(str(spec["_sentence"]), [])
                   if (safe_int(r.get("token_id", "")) is not None
                       and int(r["token_id"]) >= int(spec["_start"])
                       and int(r["token_id"]) <= int(spec["_end"]))]
        for member in members:
            tid = member.get("tid", "").strip()
            aligned = qac_by_tid.get(tid, {}) if tid else {}
            implicit = (safe_int(member.get("word_id", "")) == 0
                        or not parse_location(member.get("location", "")))
            token_rows.append({
                "clause_id": spec["clause_id"],
                "sentence_id": spec["_sentence"],
                "clause_start_token_id": spec["_start"],
                "clause_end_token_id": spec["_end"],
                "token_id": member.get("token_id", ""),
                "tid": tid,
                "location": member.get("location", ""),
                "verse_id": member.get("verse_id", ""),
                "word_id": member.get("word_id", ""),
                "uthmani_token": member.get("uthmani_token", ""),
                "imlaai_token": member.get("imlaai_token", ""),
                "pos": member.get("pos", ""),
                "rel_label": member.get("rel_label", ""),
                "ref_token_id": member.get("ref_token_id", ""),
                "is_implicit_or_non_quranic_location": implicit,
                "qac_alignment_status": aligned.get("alignment_status", "not_joined"),
                "qac_form": aligned.get("qac_form", ""),
                "qac_tag": aligned.get("qac_tag", ""),
                "qac_features": aligned.get("qac_features", ""),
            })

    # Add parent / nesting information back to constituent inventory as well.
    clause_lookup = {str(r["clause_id"]): r for r in clause_specs}
    for constituent in all_constituents:
        cid = str(constituent["clause_id"])
        if cid in clause_lookup:
            constituent["parent_clause_id"] = clause_lookup[cid].get("parent_clause_id", "")
            constituent["nesting_level"] = clause_lookup[cid].get("nesting_level", 0)

    # Summaries.
    label_counts = Counter(str(r["source_constituent_label"]) for r in all_constituents)
    clause_label_counts = Counter(str(r["source_constituent_label"]) for r in clause_rows)
    sentence_counts = Counter(str(r["sentence_id"]) for r in clause_rows)
    nesting_counts = Counter(str(r["nesting_level"]) for r in clause_rows)

    write_csv(out_dir / f"constituents_surah_{surah}.csv", all_constituents)
    write_csv(out_dir / f"clauses_surah_{surah}.csv", clause_rows)
    write_csv(out_dir / f"clause_tokens_surah_{surah}.csv", token_rows)

    summary: Dict[str, object] = {
        "surah": surah,
        "source_eqtb_file": str(eqtb_path),
        "optional_aligned_file": str(aligned_path) if aligned_path else None,
        "eqtb_rows_in_surah": len(filtered),
        "constituent_spans_extracted": len(all_constituents),
        "clause_like_spans_extracted": len(clause_rows),
        "constituent_counts_by_label": dict(label_counts),
        "clause_counts_by_label": dict(clause_label_counts),
        "clause_records_by_nesting_level": dict(nesting_counts),
        "distinct_sentence_ids_with_clauses": len(sentence_counts),
        "clause_token_membership_rows": len(token_rows),
        "malformed_spans": malformed_spans,
        "incomplete_spans": incomplete_spans,
        "duplicate_sentence_local_token_ids": duplicate_local_ids,
        "warnings": warnings,
        "interpretation": (
            "Spans are extracted from EQTB constituents_loc using sentence_id + token_id. "
            "The result is a syntactic candidate inventory, not a human-validated clause gold standard. "
            "Nested clauses are preserved and may share tokens. VS/NS/CS/SC remain source labels; "
            "grammatical function, speech act, and rhetorical function are left for annotation."
        ),
    }
    summary_path = out_dir / f"clause_extraction_summary_surah_{surah}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract EQTB clause-like spans for Surah Al-Mulk.")
    parser.add_argument("--eqtb", required=True, type=Path,
                        help="Path to eqtb_surah_67.csv from the merge script.")
    parser.add_argument("--aligned", type=Path, default=None,
                        help="Optional aligned_surah_67.csv to attach QAC morphology by EQTB tid.")
    parser.add_argument("--out", type=Path, default=Path("outputs/surah_67/clause_extraction"),
                        help="Output directory.")
    parser.add_argument("--surah", type=int, default=67)
    parser.add_argument("--encoding", default="auto",
                        help="CSV encoding (auto, utf-8-sig, utf-16, etc.).")
    args = parser.parse_args()
    try:
        summary = run(args.eqtb, args.out, args.surah, args.aligned, args.encoding)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({k: summary[k] for k in [
        "eqtb_rows_in_surah", "constituent_spans_extracted",
        "clause_like_spans_extracted", "constituent_counts_by_label",
        "clause_counts_by_label", "malformed_spans", "incomplete_spans"
    ]}, ensure_ascii=False, indent=2))
    print(f"\nWrote extraction outputs to: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
