#!/usr/bin/env python3
"""Build an enriched EQTB + QAC dataset for a selected Quran surah.

Default target: Surah Al-Mulk (67).

The script loads the complete EQTB package:
  * Quranic.csv (main token/syntax table)
  * RelLabels.csv
  * CAPoS.csv
  * ConstituentsTags.csv
  * CAMorphFeatures.xlsx
  * CALemmaLexicon.csv
  * CARootLexicon.csv

It also optionally loads the QAC morphology text export. EQTB's original
annotation codes are retained; decoded metadata is added in new columns.

Requirements: Python 3.9+ and openpyxl (for CAMorphFeatures.xlsx).
Install: python -m pip install openpyxl

Important:
  * RelLabels.csv column `rel_en` contains RELATION CODES, not English glosses.
    The script therefore adds the Arabic label but does not invent an English
    gloss for every dependency relation.
  * The VerbMood sheet has swapped English descriptions for JUS and SUBJ.
    The script corrects these two English labels using the Arabic descriptions.
  * EQTB implicit tokens (word_id=0/location='_') are preserved, but are not
    assigned artificial Quranic word coordinates during QAC alignment.
  * `constituents_loc` ranges are sentence-local token_id ranges. The script
    uses (sentence_id, token_id) to extract spans.
  * Clause candidates are extracted constituent spans, not final linguistic
    classifications. Their structural labels come from EQTB's codebook.
"""

from __future__ import annotations

import argparse
import csv
import json
import io
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SURAH_DEFAULT = 67
LOCATION_RE = re.compile(r"^\(?\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)\s*\)?$")
SPAN_RE = re.compile(r"^\[\s*(\d+)\s*-\s*(\d+)\s*\]$")
CLAUSE_CODES = {"S", "NS", "VS", "CS", "SC"}

MORPH_SHEET_TO_COLUMN = {
    "NominalCase": "nominal_case",
    "DerivedNoun": "derived_nouns",
    "NominalState": "nominal_state",
    "Number": "number",
    "Prefixs": "prefix",
    "Suffixs": "suffix",
    "VerbForm": "verb_form",
    "VerbMood": "verb_mood",
    "VerbState": "verb_aspect",
    "VerbVoice": "verb_voice",
    "SpecialGroup": "special_group",
    "Gender": "gender",
    "Person": "person",
}

# Correct translations for two known mismatches in the supplied workbook.
MORPH_EN_OVERRIDES = {
    ("VerbMood", "JUS"): "Jussive mood",
    ("VerbMood", "SUBJ"): "Subjunctive mood",
    ("VerbState", "PERF"): "Perfect verb",
    ("VerbState", "IMPF"): "Imperfect verb",
    ("VerbState", "IMPV"): "Imperative verb",
}


def detect_encoding(path: Path, requested: str = "auto") -> str:
    if requested and requested.lower() != "auto":
        return requested
    sample = path.read_bytes()[:8192]
    if sample.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if sample and b"\x00" in sample:
        even_nulls = sum(sample[i] == 0 for i in range(0, len(sample), 2))
        odd_nulls = sum(sample[i] == 0 for i in range(1, len(sample), 2))
        if max(even_nulls, odd_nulls) >= max(2, len(sample) // 20):
            return "utf-16-be" if even_nulls > odd_nulls else "utf-16-le"
    return "utf-8-sig"


def sniff_delimiter(text: str, choices: str = ",\t;|") -> str:
    try:
        return csv.Sniffer().sniff(text[:20000], delimiters=choices).delimiter
    except csv.Error:
        return "\t" if "\t" in text[:2000] else ","


def read_delimited(path: Path, encoding: str = "auto") -> Tuple[List[Dict[str, str]], str, str]:
    resolved = detect_encoding(path, encoding)
    text = path.read_text(encoding=resolved)
    delimiter = sniff_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError(f"No header row found in {path}")
    rows: List[Dict[str, str]] = []
    for raw in reader:
        row = {}
        for key, value in raw.items():
            if key is None:
                continue
            row[str(key).strip().lstrip("\ufeff")] = "" if value is None else str(value).strip()
        rows.append(row)
    return rows, resolved, delimiter


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def parse_int(value: Any) -> Optional[int]:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def parse_location(value: Any) -> Optional[Tuple[int, int, int, int]]:
    if not value:
        return None
    match = LOCATION_RE.match(str(value).strip())
    if not match:
        return None
    return tuple(int(x) for x in match.groups())  # type: ignore[return-value]


def loc_key(parts: Tuple[int, int, int, int]) -> str:
    return ":".join(str(x) for x in parts)


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: List[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_eqtb(path: Path, surah: int, encoding: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    rows, resolved, delimiter = read_delimited(path, encoding)
    kept: List[Dict[str, str]] = []
    excluded = 0
    for row in rows:
        parts = parse_location(row.get("location", ""))
        chapter = parts[0] if parts else parse_int(row.get("chapter_id", ""))
        if chapter == surah:
            kept.append(row)
        else:
            excluded += 1
    if not kept:
        raise ValueError(f"No EQTB rows found for surah {surah}; check chapter_id/location columns.")
    meta = {
        "path": str(path), "encoding": resolved, "delimiter": "TAB" if delimiter == "\t" else delimiter,
        "rows_in_file": len(rows), "rows_for_surah": len(kept), "rows_other_surahs": excluded,
    }
    return kept, meta


def load_codebook(path: Path, required: bool = True) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required EQTB codebook not found: {path}")
        return [], {"missing": str(path)}
    rows, enc, delim = read_delimited(path)
    return rows, {"path": str(path), "encoding": enc, "delimiter": "TAB" if delim == "\t" else delim, "rows": len(rows)}


def build_lookup(rows: List[Dict[str, str]], code_field: str) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for row in rows:
        code = row.get(code_field, "").strip()
        if code:
            out[norm(code)] = row
    return out


def read_morph_workbook(path: Path) -> Tuple[Dict[str, Dict[str, Dict[str, str]]], Dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError("Reading CAMorphFeatures.xlsx requires openpyxl. Install with: python -m pip install openpyxl") from exc

    wb = load_workbook(path, read_only=True, data_only=True)
    maps: Dict[str, Dict[str, Dict[str, str]]] = {}
    sheet_audit: Dict[str, Any] = {}
    for sheet_name, source_column in MORPH_SHEET_TO_COLUMN.items():
        if sheet_name not in wb.sheetnames:
            sheet_audit[sheet_name] = {"missing": True}
            maps[sheet_name] = {}
            continue
        ws = wb[sheet_name]
        values = list(ws.iter_rows(values_only=True))
        if not values:
            maps[sheet_name] = {}
            sheet_audit[sheet_name] = {"rows": 0}
            continue
        # Most sheets have Tag, Arabic Description, English Description.
        # SpecialGroup contains multiple sub-tables; only its first codebook
        # block (the three EQTB special-group tags) is used for this field.
        header = [str(v).strip() if v is not None else "" for v in values[0]]
        tag_idx = next((i for i, h in enumerate(header) if h.casefold() == "tag"), 1)
        ar_idx = next((i for i, h in enumerate(header) if "arabic description" in h.casefold()), 2)
        en_idx = next((i for i, h in enumerate(header) if "english description" in h.casefold()), 3)
        pattern_idx = next((i for i, h in enumerate(header) if h.casefold() == "pattern"), None)
        mapping: Dict[str, Dict[str, str]] = {}
        for vals in values[1:]:
            if tag_idx >= len(vals) or vals[tag_idx] is None:
                if sheet_name == "SpecialGroup":
                    break
                continue
            tag = str(vals[tag_idx]).strip()
            # The SpecialGroup sheet starts another sub-table after the initial
            # three tag rows. Stop at its first non-codebook/header row.
            if sheet_name == "SpecialGroup" and not (tag.startswith("<") or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", tag)):
                break
            if sheet_name == "SpecialGroup" and tag not in {"<in~", "kaAd", "kaAn"}:
                # Prevent rows from the embedded verb/particle reference tables
                # being interpreted as feature tags.
                break
            ar = str(vals[ar_idx]).strip() if ar_idx < len(vals) and vals[ar_idx] is not None else ""
            en = str(vals[en_idx]).strip() if en_idx < len(vals) and vals[en_idx] is not None else ""
            pattern = str(vals[pattern_idx]).strip() if pattern_idx is not None and pattern_idx < len(vals) and vals[pattern_idx] is not None else ""
            if sheet_name == "VerbMood":
                en = MORPH_EN_OVERRIDES.get((sheet_name, tag), en)
            if sheet_name == "VerbState":
                en = MORPH_EN_OVERRIDES.get((sheet_name, tag), en)
            mapping[norm(tag)] = {"code": tag, "arabic": ar, "english": en, "pattern": pattern}
        maps[sheet_name] = mapping
        sheet_audit[sheet_name] = {"rows": len(mapping), "field": source_column}
    wb.close()
    return maps, {"path": str(path), "sheets": sheet_audit}


MISSING_MORPH_VALUES = {"", "_", "-", "—", "–", "na", "n/a", "null", "none"}


def is_missing_morph_value(value: str) -> bool:
    return norm(value) in MISSING_MORPH_VALUES


def normalize_morph_code(column: str, value: str) -> str:
    """Remove EQTB field namespaces while preserving the original raw value."""
    raw = str(value or "").strip()
    if is_missing_morph_value(raw):
        return ""
    if column == "verb_mood" and raw.upper().startswith("MOOD:"):
        return raw.split(":", 1)[1].strip()
    if column == "special_group" and raw.upper().startswith("SP:"):
        return raw.split(":", 1)[1].strip()
    return raw


def decode_single(value: str, lookup: Dict[str, Dict[str, str]], column: str = "") -> Dict[str, str]:
    code = normalize_morph_code(column, value) if column else ("" if is_missing_morph_value(value) else value.strip())
    if not code:
        return {"ar": "", "en": "", "match": "missing", "lookup_code": ""}
    item = lookup.get(norm(code))
    if not item:
        return {"ar": "", "en": "", "match": "unknown", "lookup_code": code}
    return {"ar": item.get("arabic", ""), "en": item.get("english", ""), "match": "yes", "lookup_code": code}


def split_feature_codes(value: str, lookup: Dict[str, Dict[str, str]]) -> List[str]:
    if is_missing_morph_value(value):
        return []
    # Tags such as l:EMPH+ and f:CAUS+ contain punctuation; preserve complete
    # code strings. Accept common multi-value separators without splitting on
    # punctuation internal to a code.
    parts = [p.strip() for p in re.split(r"[|;,\s]+", value.strip()) if p.strip()]
    if len(parts) == 1:
        return parts
    # Some exports concatenate tags. If it is not separable, try known code
    # tokens longest-first and retain unrecognized residue in the raw field.
    return parts


def enrich_tokens(
    eqtb_rows: List[Dict[str, str]],
    pos_lookup: Dict[str, Dict[str, str]],
    rel_lookup: Dict[str, Dict[str, str]],
    const_lookup: Dict[str, Dict[str, str]],
    morph_maps: Dict[str, Dict[str, Dict[str, str]]],
    lemma_lookup: Dict[str, Dict[str, str]],
    root_lookup: Dict[str, Dict[str, str]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    mapping_counts: Dict[str, Counter] = defaultdict(Counter)
    for original in eqtb_rows:
        row: Dict[str, Any] = dict(original)
        pos_code = original.get("pos", "")
        pos_entry = pos_lookup.get(norm(pos_code)) if pos_code else None
        row["pos_ar_lookup"] = pos_entry.get("pos_ar", "") if pos_entry else ""
        row["pos_en_lookup"] = pos_entry.get("pos_en", "") if pos_entry else ""
        row["pos_codebook_match"] = "yes" if pos_entry else ("no" if pos_code else "")
        if pos_code:
            mapping_counts["pos"][row["pos_codebook_match"]] += 1

        rel_code = original.get("rel_label", "")
        rel = rel_lookup.get(norm(rel_code)) if rel_code else None
        row["rel_label_ar_lookup"] = rel.get("rel_ar", "") if rel else ""
        row["rel_codebook_match"] = "yes" if rel else ("no" if rel_code else "")
        if rel_code:
            mapping_counts["rel_label"][row["rel_codebook_match"]] += 1

        const_code = original.get("constituent_label", "")
        const = const_lookup.get(norm(const_code)) if const_code and const_code != "-" else None
        row["constituent_label_ar_lookup"] = const.get("tag_ar", "") if const else ""
        row["constituent_label_en_lookup"] = const.get("tag_en", "") if const else ""
        row["constituent_codebook_match"] = "yes" if const else ("no" if const_code and const_code != "-" else "")
        if const_code and const_code != "-":
            mapping_counts["constituent_label"][row["constituent_codebook_match"]] += 1

        for sheet_name, col in MORPH_SHEET_TO_COLUMN.items():
            value = original.get(col, "")
            lookup = morph_maps.get(sheet_name, {})
            if col in {"prefix", "suffix"}:
                raw_codes = split_feature_codes(value, lookup)
                decoded_items: List[Dict[str, str]] = []
                matched_codes: List[str] = []
                unknown_codes: List[str] = []
                for code in raw_codes:
                    item = lookup.get(norm(code))
                    if item:
                        decoded_items.append(item)
                        matched_codes.append(code)
                    else:
                        unknown_codes.append(code)
                row[f"{col}_lookup_codes"] = "|".join(raw_codes)
                row[f"{col}_decoded_json"] = json.dumps(decoded_items, ensure_ascii=False) if decoded_items else "[]"
                if not raw_codes:
                    status = "missing"
                elif len(matched_codes) == len(raw_codes):
                    status = "yes"
                elif matched_codes:
                    status = "partial"
                else:
                    status = "unknown"
                row[f"{col}_codebook_match"] = status
                if status != "missing":
                    mapping_counts[col][status] += 1
                else:
                    mapping_counts[col]["missing"] += 1
                if unknown_codes:
                    row[f"{col}_unknown_codes"] = "|".join(unknown_codes)
            else:
                decoded = decode_single(value, lookup, col)
                row[f"{col}_lookup_code"] = decoded["lookup_code"]
                row[f"{col}_ar_lookup"] = decoded["ar"]
                row[f"{col}_en_lookup"] = decoded["en"]
                row[f"{col}_codebook_match"] = decoded["match"]
                if sheet_name == "VerbForm":
                    form_item = lookup.get(norm(decoded["lookup_code"])) if decoded["lookup_code"] else None
                    row["verb_form_pattern_lookup"] = form_item.get("pattern", "") if form_item else ""
                mapping_counts[col][decoded["match"]] += 1

        lemma = original.get("lemma", "").strip()
        lemma_entry = lemma_lookup.get(norm(lemma)) if lemma else None
        row["lemma_in_lexicon"] = "yes" if lemma_entry else ("no" if lemma else "")
        row["lemma_lexicon_size"] = lemma_entry.get("size", "") if lemma_entry else ""
        row["lemma_lexicon_ar"] = lemma_entry.get("lemma_ar", "") if lemma_entry else ""

        root = original.get("root", "").strip()
        root_entry = root_lookup.get(norm(root)) if root else None
        row["root_in_lexicon"] = "yes" if root_entry else ("no" if root else "")
        row["root_lexicon_size"] = root_entry.get("size", "") if root_entry else ""
        row["root_lexicon_ar"] = root_entry.get("root_ar", "") if root_entry else ""
        enriched.append(row)

    return enriched, {k: dict(v) for k, v in mapping_counts.items()}


def parse_qac(path: Optional[Path], surah: int, encoding: str = "auto") -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    if path is None:
        return [], {"provided": False, "rows": 0}
    resolved = detect_encoding(path, encoding)
    lines = path.read_text(encoding=resolved).splitlines()
    rows: List[Dict[str, str]] = []
    warnings: List[str] = []
    for line_no, line in enumerate(lines, start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 3:
            continue
        loc = parse_location(parts[0])
        if not loc:
            continue
        if loc[0] != surah:
            continue
        rows.append({
            "location": parts[0], "form": parts[1], "tag": parts[2],
            "features": "\t".join(parts[3:]) if len(parts) > 3 else "",
            "location_key": loc_key(loc), "surah": str(loc[0]), "ayah": str(loc[1]),
            "word": str(loc[2]), "segment": str(loc[3]), "source_line": str(line_no),
        })
    if not rows:
        raise ValueError(f"QAC file supplied but no Surah {surah} morphology records were found: {path}")
    return rows, {"provided": True, "path": str(path), "encoding": resolved, "rows": len(rows), "warnings": warnings}


def alignment_key(row: Dict[str, str]) -> Optional[str]:
    parts = parse_location(row.get("location", ""))
    if parts and parts[2] > 0:
        return loc_key(parts)
    # Fallback to coordinate columns, while excluding implicit word_id=0.
    nums = [parse_int(row.get(k, "")) for k in ("chapter_id", "verse_id", "word_id", "tok_id")]
    if all(v is not None for v in nums) and nums[2] and nums[2] > 0:
        return loc_key(tuple(nums))  # type: ignore[arg-type]
    return None


def build_alignment(eqtb: List[Dict[str, Any]], qac: List[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    eqtb_by_key: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    qac_by_key: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    implicit: List[Dict[str, Any]] = []
    for row in eqtb:
        key = alignment_key(row)
        if key:
            eqtb_by_key[key].append(row)
        else:
            implicit.append(row)
    for row in qac:
        qac_by_key[row["location_key"]].append(row)
    result: List[Dict[str, Any]] = []
    match_counts = Counter()
    duplicate_eqtb = {k: len(v) for k, v in eqtb_by_key.items() if len(v) > 1}
    duplicate_qac = {k: len(v) for k, v in qac_by_key.items() if len(v) > 1}
    all_keys = sorted(set(eqtb_by_key) | set(qac_by_key), key=lambda s: tuple(int(x) for x in s.split(":")))
    for key in all_keys:
        es, qs = eqtb_by_key.get(key, []), qac_by_key.get(key, [])
        for i in range(max(len(es), len(qs))):
            e = es[i] if i < len(es) else None
            q = qs[i] if i < len(qs) else None
            status = "exact_location_match" if e and q else ("eqtb_only" if e else "qac_only")
            rec: Dict[str, Any] = {"location_key": key, "occurrence": i, "alignment_status": status,
                                   "alignment_basis": "surah:ayah:word:segment; duplicate occurrence order when needed"}
            if e:
                rec.update({f"eqtb_{k}": v for k, v in e.items()})
            if q:
                rec.update({f"qac_{k}": v for k, v in q.items()})
            result.append(rec)
            match_counts[status] += 1
    for e in implicit:
        rec = {"location_key": "", "occurrence": "", "alignment_status": "eqtb_implicit_no_quranic_location",
               "alignment_basis": "implicit EQTB token; no QAC word coordinate"}
        rec.update({f"eqtb_{k}": v for k, v in e.items()})
        result.append(rec)
        match_counts["eqtb_implicit_no_quranic_location"] += 1
    return result, {"status_counts": dict(match_counts), "eqtb_duplicate_locations": duplicate_eqtb,
                    "qac_duplicate_locations": duplicate_qac}


def parse_span(value: str) -> Optional[Tuple[int, int]]:
    match = SPAN_RE.match((value or "").strip())
    if not match:
        return None
    start, end = int(match.group(1)), int(match.group(2))
    return (start, end) if start <= end else None


def make_constituents(eqtb: List[Dict[str, Any]], surah: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    by_sentence: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in eqtb:
        by_sentence[row.get("sentence_id", "")].append(row)
    for sentence_rows in by_sentence.values():
        sentence_rows.sort(key=lambda r: parse_int(r.get("token_id", "")) if parse_int(r.get("token_id", "")) is not None else -1)

    raw_spans: Dict[Tuple[str, int, int, str], Dict[str, Any]] = {}
    warnings: List[str] = []
    for head in eqtb:
        if head.get("is_constituent", "").strip().lower() not in {"1", "true", "yes", "y"}:
            continue
        label = head.get("constituent_label", "").strip().upper()
        span = parse_span(head.get("constituents_loc", ""))
        if not span:
            warnings.append(f"Unparseable constituent span: tid={head.get('tid')} value={head.get('constituents_loc')!r}")
            continue
        sentence = head.get("sentence_id", "")
        key = (sentence, span[0], span[1], label)
        item = raw_spans.get(key)
        if item is None:
            local_tokens = [r for r in by_sentence.get(sentence, [])
                            if (parse_int(r.get("token_id", "")) is not None
                                and span[0] <= parse_int(r.get("token_id", "")) <= span[1])]
            reconstructed = " ".join(r.get("uthmani_token", "") for r in local_tokens if r.get("uthmani_token", ""))
            item = {
                "constituent_id": f"EQTB:{sentence}:{span[0]}-{span[1]}:{label}",
                "surah": surah,
                "sentence_id": sentence,
                "start_token_id": span[0],
                "end_token_id": span[1],
                "span_length": span[1] - span[0] + 1,
                "source_constituent_label": label,
                "constituent_label_ar": head.get("constituent_label_ar_lookup", ""),
                "constituent_label_en": head.get("constituent_label_en_lookup", ""),
                "head_tid_list": [],
                "head_token_id_list": [],
                "head_location_list": [],
                "source_constituents_text": head.get("constituents", ""),
                "reconstructed_token_sequence": reconstructed,
                "token_count_in_span": len(local_tokens),
                "implicit_token_count": sum(1 for r in local_tokens if (parse_int(r.get("word_id", "")) == 0 or not parse_location(r.get("location", "")))),
                "is_clause_candidate": "yes" if label in CLAUSE_CODES else "no",
                "review_status": "needs_linguistic_review" if label in CLAUSE_CODES else "not_clause_candidate",
            }
            raw_spans[key] = item
        item["head_tid_list"].append(head.get("tid", ""))
        item["head_token_id_list"].append(head.get("token_id", ""))
        item["head_location_list"].append(head.get("location", ""))

    constituents = list(raw_spans.values())
    # Attach nearest containing constituent as parent; retain overlaps/nesting.
    for child in constituents:
        candidates = [p for p in constituents
                      if p["sentence_id"] == child["sentence_id"]
                      and p["constituent_id"] != child["constituent_id"]
                      and p["start_token_id"] <= child["start_token_id"]
                      and p["end_token_id"] >= child["end_token_id"]
                      and (p["start_token_id"] < child["start_token_id"] or p["end_token_id"] > child["end_token_id"])]
        if candidates:
            parent = min(candidates, key=lambda p: p["span_length"])
            child["parent_constituent_id"] = parent["constituent_id"]
        else:
            child["parent_constituent_id"] = ""
        child["head_tid_list"] = "|".join(child["head_tid_list"])
        child["head_token_id_list"] = "|".join(child["head_token_id_list"])
        child["head_location_list"] = "|".join(child["head_location_list"])

    clause_candidates = [dict(r) for r in constituents if r["is_clause_candidate"] == "yes"]
    constituent_tokens: List[Dict[str, Any]] = []
    span_by_id = {r["constituent_id"]: r for r in constituents}
    for c in constituents:
        for tok in by_sentence.get(c["sentence_id"], []):
            tid = parse_int(tok.get("token_id", ""))
            if tid is None or not (c["start_token_id"] <= tid <= c["end_token_id"]):
                continue
            constituent_tokens.append({
                "constituent_id": c["constituent_id"],
                "is_clause_candidate": c["is_clause_candidate"],
                "sentence_id": c["sentence_id"],
                "token_id": tid,
                "tid": tok.get("tid", ""),
                "location": tok.get("location", ""),
                "word_id": tok.get("word_id", ""),
                "uthmani_token": tok.get("uthmani_token", ""),
                "pos": tok.get("pos", ""),
                "pos_ar_lookup": tok.get("pos_ar_lookup", ""),
                "rel_label": tok.get("rel_label", ""),
                "rel_label_ar_lookup": tok.get("rel_label_ar_lookup", ""),
                "is_implicit_token": "yes" if (parse_int(tok.get("word_id", "")) == 0 or not parse_location(tok.get("location", ""))) else "no",
            })
    constituents.sort(key=lambda r: (r["sentence_id"], r["start_token_id"], r["end_token_id"], r["source_constituent_label"]))
    clause_candidates.sort(key=lambda r: (r["sentence_id"], r["start_token_id"], r["end_token_id"]))
    return constituents, clause_candidates, constituent_tokens, warnings


def make_dependencies(eqtb: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_sentence_token: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in eqtb:
        by_sentence_token[(row.get("sentence_id", ""), row.get("token_id", ""))].append(row)
    output = []
    for row in eqtb:
        ref = row.get("ref_token_id", "")
        targets = by_sentence_token.get((row.get("sentence_id", ""), ref), []) if ref else []
        output.append({
            "tid": row.get("tid", ""), "surah": row.get("chapter_id", ""),
            "verse": row.get("verse_id", ""), "sentence_id": row.get("sentence_id", ""),
            "token_id": row.get("token_id", ""), "location": row.get("location", ""),
            "uthmani_token": row.get("uthmani_token", ""),
            "pos": row.get("pos", ""), "pos_ar": row.get("pos_ar_lookup", ""),
            "pos_en": row.get("pos_en_lookup", ""),
            "rel_label": row.get("rel_label", ""),
            "rel_label_ar": row.get("rel_label_ar_lookup", ""),
            "ref_token_id": ref,
            "ref_tid_candidates": "|".join(t.get("tid", "") for t in targets),
            "ref_token_text_candidates": "|".join(t.get("uthmani_token", "") for t in targets),
            "ref_resolution": "root_or_no_reference" if not ref or ref == "0" else ("resolved" if targets else "unresolved"),
        })
    return output


def make_lexicon_validation(eqtb: List[Dict[str, Any]], field: str, lookup: Dict[str, Dict[str, str]], kind: str) -> List[Dict[str, Any]]:
    vals = sorted({r.get(field, "").strip() for r in eqtb if r.get(field, "").strip()})
    rows = []
    for value in vals:
        item = lookup.get(norm(value))
        rows.append({
            kind: value,
            "found_in_lexicon": "yes" if item else "no",
            "arabic_from_lexicon": (item or {}).get("lemma_ar" if kind == "lemma" else "root_ar", ""),
            "frequency_size": (item or {}).get("size", ""),
        })
    return rows



def build_morph_code_audit(enriched: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Summarize raw morphology codes, normalized lookup codes and lookup outcomes."""
    counts: Counter = Counter()
    fields = [col for col in MORPH_SHEET_TO_COLUMN.values()]
    for row in enriched:
        for col in fields:
            raw = str(row.get(col, "") or "").strip()
            if col in {"prefix", "suffix"}:
                codes = split_feature_codes(raw, {})
                if not codes:
                    counts[(col, raw or "<EMPTY>", "", "missing")] += 1
                else:
                    status = row.get(f"{col}_codebook_match", "unknown")
                    unknown = set(str(row.get(f"{col}_unknown_codes", "")).split("|")) if row.get(f"{col}_unknown_codes") else set()
                    for code in codes:
                        item_status = "unknown" if code in unknown else "yes"
                        counts[(col, raw, code, item_status)] += 1
            else:
                lookup_code = str(row.get(f"{col}_lookup_code", "") or "")
                status = str(row.get(f"{col}_codebook_match", "") or "missing")
                counts[(col, raw or "<EMPTY>", lookup_code, status)] += 1
    return [
        {"dimension": k[0], "raw_value": k[1], "lookup_code": k[2], "status": k[3], "count": count}
        for k, count in sorted(counts.items())
    ]

def flatten_morph_lookups(maps: Dict[str, Dict[str, Dict[str, str]]]) -> List[Dict[str, str]]:
    rows = []
    for sheet, items in maps.items():
        for code, value in items.items():
            rows.append({"dimension": sheet, "code": value.get("code", code), "arabic": value.get("arabic", ""),
                         "english": value.get("english", ""), "pattern": value.get("pattern", "")})
    return rows


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    aux = args.aux_dir
    required_aux = {
        "relations": aux / "RelLabels.csv",
        "pos": aux / "CAPoS.csv",
        "constituents": aux / "ConstituentsTags.csv",
        "morph_features": aux / "CAMorphFeatures.xlsx",
        "lemma_lexicon": aux / "CALemmaLexicon.csv",
        "root_lexicon": aux / "CARootLexicon.csv",
    }
    missing = [str(p) for p in required_aux.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing EQTB auxiliary files:\n" + "\n".join(missing))

    eqtb_rows, eqtb_info = load_eqtb(args.eqtb, args.surah, args.eqtb_encoding)
    rel_rows, rel_info = load_codebook(required_aux["relations"])
    pos_rows, pos_info = load_codebook(required_aux["pos"])
    const_rows, const_info = load_codebook(required_aux["constituents"])
    lemma_rows, lemma_info = load_codebook(required_aux["lemma_lexicon"])
    root_rows, root_info = load_codebook(required_aux["root_lexicon"])
    morph_maps, morph_info = read_morph_workbook(required_aux["morph_features"])

    rel_lookup = build_lookup(rel_rows, "rel_en")
    pos_lookup = build_lookup(pos_rows, "pos")
    const_lookup = build_lookup(const_rows, "tag")
    lemma_lookup = build_lookup(lemma_rows, "lemma")
    root_lookup = build_lookup(root_rows, "root")

    enriched, decode_counts = enrich_tokens(eqtb_rows, pos_lookup, rel_lookup, const_lookup,
                                            morph_maps, lemma_lookup, root_lookup)
    qac_rows, qac_info = parse_qac(args.qac, args.surah, args.qac_encoding)
    aligned, align_info = build_alignment(enriched, qac_rows)
    constituents, clause_candidates, constituent_tokens, constituent_warnings = make_constituents(enriched, args.surah)
    dependencies = make_dependencies(enriched)
    lemma_validation = make_lexicon_validation(enriched, "lemma", lemma_lookup, "lemma")
    root_validation = make_lexicon_validation(enriched, "root", root_lookup, "root")

    # Morphology view: preserve raw morphology fields and decoded lookup fields.
    morph_fields = ["tid", "sentence_id", "location", "uthmani_token", "pos", "pos_ar_lookup", "pos_en_lookup",
                    "features", "segment", "lemma", "lemma_ar", "root", "root_ar", "verb_form", "verb_form_lookup_code", "verb_form_codebook_match", "verb_form_ar_lookup",
                    "verb_form_en_lookup", "verb_mood", "verb_mood_lookup_code", "verb_mood_codebook_match", "verb_mood_ar_lookup", "verb_mood_en_lookup", "verb_aspect",
                    "verb_aspect_lookup_code", "verb_aspect_codebook_match", "verb_aspect_ar_lookup", "verb_aspect_en_lookup", "verb_voice", "verb_voice_lookup_code", "verb_voice_codebook_match", "verb_voice_ar_lookup", "verb_voice_en_lookup",
                    "nominal_case", "nominal_case_lookup_code", "nominal_case_codebook_match", "nominal_case_ar_lookup", "nominal_case_en_lookup", "nominal_state", "nominal_state_lookup_code", "nominal_state_codebook_match", "nominal_state_ar_lookup",
                    "nominal_state_en_lookup", "derived_nouns", "derived_nouns_lookup_code", "derived_nouns_codebook_match", "derived_nouns_ar_lookup", "derived_nouns_en_lookup", "number",
                    "number_lookup_code", "number_codebook_match", "number_ar_lookup", "number_en_lookup", "gender", "gender_lookup_code", "gender_codebook_match", "gender_ar_lookup", "gender_en_lookup", "person",
                    "person_lookup_code", "person_codebook_match", "person_ar_lookup", "person_en_lookup", "special_group", "special_group_lookup_code", "special_group_codebook_match", "special_group_ar_lookup", "special_group_en_lookup",
                    "prefix", "prefix_lookup_codes", "prefix_codebook_match", "prefix_decoded_json", "suffix", "suffix_lookup_codes", "suffix_codebook_match", "suffix_decoded_json", "lemma_in_lexicon", "lemma_lexicon_size",
                    "root_in_lexicon", "root_lexicon_size"]
    morphology = [{k: r.get(k, "") for k in morph_fields} for r in enriched]

    # Metadata audit: identify codes present in Quranic.csv but absent from lookup.
    unknown_codes: Dict[str, List[str]] = {}
    for field, lookup in [("pos", pos_lookup), ("rel_label", rel_lookup), ("constituent_label", const_lookup)]:
        vals = sorted({r.get(field, "").strip() for r in enriched if r.get(field, "").strip() and r.get(field, "").strip() != "-"})
        unknown_codes[field] = [v for v in vals if norm(v) not in lookup]

    unknown_morphology_codes: Dict[str, List[Dict[str, Any]]] = {}
    for field in MORPH_SHEET_TO_COLUMN.values():
        rows_for_field = [r for r in build_morph_code_audit(enriched) if r["dimension"] == field and r["status"] in {"unknown", "partial"}]
        unknown_morphology_codes[field] = rows_for_field

    write_csv(out / f"eqtb_tokens_enriched_surah_{args.surah}.csv", enriched)
    write_csv(out / f"qac_morphology_surah_{args.surah}.csv", qac_rows)
    write_csv(out / f"eqtb_qac_alignment_surah_{args.surah}.csv", aligned)
    write_csv(out / f"morphology_surah_{args.surah}.csv", morphology)
    write_csv(out / f"dependencies_surah_{args.surah}.csv", dependencies)
    write_csv(out / f"constituents_surah_{args.surah}.csv", constituents)
    write_csv(out / f"clause_candidates_surah_{args.surah}.csv", clause_candidates)
    write_csv(out / f"constituent_tokens_surah_{args.surah}.csv", constituent_tokens)
    write_csv(out / f"lemma_validation_surah_{args.surah}.csv", lemma_validation)
    write_csv(out / f"root_validation_surah_{args.surah}.csv", root_validation)
    write_csv(out / "lookup_morphology_features.csv", flatten_morph_lookups(morph_maps))
    write_csv(out / f"morphology_code_audit_surah_{args.surah}.csv", build_morph_code_audit(enriched))
    write_csv(out / "lookup_relations.csv", [
        {"relation_code": r.get("rel_en", ""), "arabic": r.get("rel_ar", ""), "source_rel_id": r.get("rel_id", "")}
        for r in rel_rows
    ])
    write_csv(out / "lookup_pos.csv", [
        {"pos_code": r.get("pos", ""), "arabic": r.get("pos_ar", ""), "english": r.get("pos_en", ""), "source_pid": r.get("pid", "")}
        for r in pos_rows
    ])
    write_csv(out / "lookup_constituents.csv", [
        {"constituent_code": r.get("tag", ""), "arabic": r.get("tag_ar", ""), "english": r.get("tag_en", ""), "source_pid": r.get("pid", "")}
        for r in const_rows
    ])

    metadata = {
        "relations": rel_rows,
        "pos": pos_rows,
        "constituents": const_rows,
        "morphology_features": morph_maps,
    }
    write_json(out / "eqtb_metadata_lookup.json", metadata)

    label_counts = Counter(r.get("constituent_label", "") for r in enriched if r.get("is_constituent", "") in {"1", "true", "True"})
    summary = {
        "surah": args.surah,
        "surah_name": "Al-Mulk" if args.surah == 67 else "",
        "input_files": {
            "eqtb_main": eqtb_info,
            "auxiliary": {"RelLabels.csv": rel_info, "CAPoS.csv": pos_info, "ConstituentsTags.csv": const_info,
                          "CAMorphFeatures.xlsx": morph_info, "CALemmaLexicon.csv": lemma_info, "CARootLexicon.csv": root_info},
            "qac_morphology": qac_info,
        },
        "counts": {
            "eqtb_token_rows": len(enriched), "qac_morphology_rows": len(qac_rows),
            "alignment_rows": len(aligned), "alignment_status": align_info["status_counts"],
            "eqtb_duplicate_location_keys": len(align_info["eqtb_duplicate_locations"]),
            "qac_duplicate_location_keys": len(align_info["qac_duplicate_locations"]),
            "constituents_total": len(constituents), "constituents_by_label": dict(label_counts),
            "clause_candidate_spans": len(clause_candidates), "constituent_token_memberships": len(constituent_tokens),
            "dependency_rows": len(dependencies), "unique_lemmas_in_surah": len(lemma_validation),
            "unique_roots_in_surah": len(root_validation),
            "lemmas_found_in_lexicon": sum(1 for r in lemma_validation if r["found_in_lexicon"] == "yes"),
            "roots_found_in_lexicon": sum(1 for r in root_validation if r["found_in_lexicon"] == "yes"),
        },
        "codebook_mapping_counts": decode_counts,
        "unknown_codes": unknown_codes,
        "unknown_morphology_codes": unknown_morphology_codes,
        "alignment_details": align_info,
        "warnings": constituent_warnings,
        "methodological_notes": [
            "RelLabels.csv's rel_en column stores relation codes (e.g. cond, rslt, circ), not English glosses; Arabic descriptions are mapped from rel_ar.",
            "VerbMood English descriptions in the workbook are reversed for JUS and SUBJ; output English labels are corrected using Arabic descriptions.",
            "Morphology placeholder values such as '_' are counted as missing, not failed codebook mappings.",
            "EQTB field namespaces MOOD: and SP: are removed only for lookup; original source values are preserved.",
            "QAC input is the morphology export, not a complete QAC syntactic treebank.",
            "Exact location alignment is coordinate-based; duplicate coordinates are paired by within-file occurrence order and must be reviewed.",
            "Implicit EQTB tokens without real Quranic word coordinates are retained and excluded from direct QAC location matching.",
            "Constituent spans use sentence_id + inclusive sentence-local token_id ranges from constituents_loc.",
            "Clause candidates are EQTB constituent spans with labels S, NS, VS, CS, or SC; they require linguistic review and are not final clause labels.",
            "Lexicon membership is a lookup check, not a proof that the source lemma/root analysis is linguistically correct.",
        ],
    }
    write_json(out / f"dataset_summary_surah_{args.surah}.json", summary)
    return summary


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Build an enriched EQTB + QAC dataset for Surah Al-Mulk.")
    parser.add_argument("--eqtb", required=True, type=Path, help="Path to the main EQTB Quranic.csv file.")
    parser.add_argument("--qac", type=Path, default=None, help="Optional QAC morphology 0.4 TSV/TXT file.")
    parser.add_argument("--aux-dir", type=Path, default=script_dir / "eqtb_aux", help="Directory containing the six EQTB auxiliary files.")
    parser.add_argument("--out", type=Path, default=Path("outputs/surah_67_full"), help="Output directory.")
    parser.add_argument("--surah", type=int, default=SURAH_DEFAULT, help="Surah number (default 67).")
    parser.add_argument("--eqtb-encoding", default="auto", help="EQTB encoding (default auto).")
    parser.add_argument("--qac-encoding", default="auto", help="QAC encoding (default auto).")
    args = parser.parse_args()
    try:
        summary = run(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary["counts"], ensure_ascii=False, indent=2))
    print(f"\nWrote enriched dataset to: {args.out.resolve()}")
    if summary["warnings"]:
        print(f"Warnings: {len(summary['warnings'])}; see dataset_summary_surah_{args.surah}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
