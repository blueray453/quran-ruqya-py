#!/usr/bin/env python3
"""Validate source hashes and core internal consistency of generated CSV files."""
import argparse, csv, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read_rows(path):
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', type=Path, default=ROOT/'data_sources')
    ap.add_argument('--csv-dir', type=Path, default=ROOT/'output/csv')
    args = ap.parse_args()

    required = [
        'quran_chunk_occurrences.csv','quran_chunk_members.csv','quran_dependency_edges.csv',
        'quran_chunk_curriculum_links.csv','quran_chunk_hierarchy.csv','quran_chunk_type_frequency.csv',
        'grammatical_chunk_pattern_frequency.csv','six_core_phrase_pattern_summary.csv',
        'repeated_lexical_chunk_types.csv','repeated_lexical_chunk_occurrences.csv',
        'curriculum_concept_map.csv','source_alignment_audit.csv','teacher_review_queue.csv',
        'dataset_summary.csv','data_dictionary.csv','source_manifest.csv'
    ]
    missing = [x for x in required if not (args.csv_dir/x).is_file()]
    if missing:
        raise SystemExit('Missing required CSVs: ' + ', '.join(missing))

    manifest = read_rows(args.csv_dir/'source_manifest.csv')
    hash_errors = []
    for row in manifest:
        p = args.data_dir/row['file_name']
        if not p.is_file():
            hash_errors.append(f"Missing source: {p.name}")
        elif sha256(p) != row['sha256']:
            hash_errors.append(f"SHA-256 mismatch: {p.name}")
    if hash_errors:
        raise SystemExit('\n'.join(hash_errors))

    summary_rows = read_rows(args.csv_dir/'dataset_summary.csv')
    summary = {r['metric']: int(r['value']) for r in summary_rows}
    checks = {
        'quran_chunk_occurrences.csv': 'grammar_chunk_occurrences',
        'quran_chunk_members.csv': 'grammar_chunk_members',
        'quran_dependency_edges.csv': 'dependency_edges_exported',
        'quran_chunk_curriculum_links.csv': 'distinct_curriculum_links',
        'quran_chunk_hierarchy.csv': 'strict_chunk_containment_links',
        'teacher_review_queue.csv': 'teacher_review_candidates',
    }
    for filename, metric in checks.items():
        actual = len(read_rows(args.csv_dir/filename))
        expected = summary.get(metric)
        if actual != expected:
            raise SystemExit(f'{filename}: {actual} rows, summary says {expected}')

    six = read_rows(args.csv_dir/'six_core_phrase_pattern_summary.csv')
    expected_names = {'Murakkab Tawsifi','Murakkab Idafi','Murakkab Jarri','Murakkab Ishari','Murakkab Atfi','Murakkab Badali (candidate)'}
    actual_names = {r['ilmhub_construction'] for r in six}
    if actual_names != expected_names or len(six) != 6:
        raise SystemExit(f'Six-phrase taxonomy mismatch: {sorted(actual_names)}')

    occ = read_rows(args.csv_dir/'quran_chunk_occurrences.csv')
    badali = [r for r in occ if r['chunk_family'] == 'badali_candidate']
    if any(r['certainty'].lower() in {'confirmed','high','direct'} and not r['review_required'] for r in badali):
        raise SystemExit('Badali candidate unexpectedly marked as confirmed/no-review')

    result = {
        'status': 'PASS',
        'source_files_verified': len(manifest),
        'csv_tables_verified': len(required),
        'row_checks': checks,
        'six_core_patterns': len(six),
        'badali_candidate_rows': len(badali),
        'whole_word_annotations': summary.get('whole_word_annotations'),
        'treebank_sentences': summary.get('treebank_sentences'),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
