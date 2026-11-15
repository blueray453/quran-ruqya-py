#!/usr/bin/env python3
"""Merge validated flat chunk output into English + Bangla annotation files.

New raw shape: {"s:a": [{"words": [1,2], "en": "...", "bn": "..."}, ...]}.
Legacy nested clause/phrase raw files are accepted and flattened, but their clause
boundaries are discarded because the new annotation contract has no clause layer.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, expand_words  # noqa: E402


def entry_chunks(entry):
    if 'chunks' in entry:
        return entry['chunks']
    return [phrase for clause in entry.get('clauses', []) for phrase in clause.get('phrases', [])]


def raw_chunks(value):
    if not isinstance(value, list) or not value:
        raise SystemExit('raw ayah must contain a non-empty flat chunk list')
    # Compatibility: old raw output was [clause, clause, ...], each clause a phrase list.
    if isinstance(value[0], list):
        value = [phrase for clause in value for phrase in clause]
    out = []
    for i, item in enumerate(value, 1):
        if not isinstance(item, dict):
            raise SystemExit(f'chunk {i}: expected an object')
        if 'words' not in item:
            raise SystemExit(f'chunk {i}: expected validated word positions; run through tools/run_llm.py first')
        out.append({'words': expand_words(item['words']), **{k: item[k] for k in ('en', 'bn') if k in item}})
    return out


ap = argparse.ArgumentParser()
ap.add_argument('--surah', type=int, required=True)
ap.add_argument('--file', required=True, help='raw LLM output JSON file')
ap.add_argument('--lang', choices=['both', 'en', 'bn'], default='both')
ap.add_argument('--out-dir', default=os.path.join(ROOT, 'annotations'))
ap.add_argument('--model', default=None, help='model id recorded in provenance')
ap.add_argument('--force', action='store_true', help='overwrite reviewed ayahs / bundled sample')
args = ap.parse_args()

with open(args.file, encoding='utf-8') as fh:
    raw = json.load(fh)
en_path = os.path.join(args.out_dir, f'surah-{args.surah:03d}.json')
bn_path = os.path.join(args.out_dir, 'bn', f'surah-{args.surah:03d}.json')


def load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def new_doc(lang):
    return {
        'schema_version': '2.0',
        'conventions_version': '4.0',
        'surah': args.surah,
        'language': lang,
        'provenance': {
            'generator': 'llm-annotation',
            'model': args.model,
            'note': ('Merged flat Arabic chunks by tools/collect.py.' if lang == 'en' else
                     'Bangla gloss-only overlay; chunk spans mirror the English file.'),
        },
        'ayahs': {},
    }


def open_doc(path, lang):
    if os.path.exists(path):
        doc = load(path)
        if doc.get('provenance', {}).get('generator') == 'prototype-replay' and not args.force:
            raise SystemExit(f'abort: {os.path.relpath(path, ROOT)} is the bundled prototype sample; '
                             f'write pilots under runs/<tag>/annotations (or pass --force)')
        if doc.get('schema_version') != '2.0':
            raise SystemExit(f'abort: {path} uses legacy schema {doc.get("schema_version")}; '
                             'write new flat-chunk output to a separate --out-dir')
        return doc
    return new_doc(lang)


def save(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Ayah keys are always written in ascending numeric order. run_llm.py finishes ayahs in
    # pilot processing order (anchor bands first), so the in-memory dict ends up out of
    # order; sorting here also normalises annotation files written by earlier runs.
    if isinstance(doc.get('ayahs'), dict):
        doc['ayahs'] = {k: doc['ayahs'][k] for k in sorted(doc['ayahs'], key=lambda x: int(x))}
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)


def keyed(raw_dict):
    for key, value in raw_dict.items():
        s, a = key.split(':')
        if int(s) != args.surah:
            raise SystemExit(f'key {key} does not belong to surah {args.surah}')
        yield key, a, value


def locked(doc, ayah, key):
    previous = doc['ayahs'].get(ayah)
    if previous and previous.get('status') == 'reviewed' and not args.force:
        print(f'skip {key} (status=reviewed; use --force to overwrite)')
        return True
    return False


def merge_en(raw_en):
    doc = open_doc(en_path, 'en')
    merged = skipped = 0
    for key, ayah, value in keyed(raw_en):
        if locked(doc, ayah, key):
            skipped += 1
            continue
        chunks = raw_chunks(value)
        en_chunks = []
        for i, chunk in enumerate(chunks, 1):
            en = chunk.get('en')
            if not isinstance(en, str) or not en.strip():
                raise SystemExit(f'abort: {key} chunk {i} has empty en')
            en_chunks.append({'words': chunk['words'], 'en': en})
        doc['ayahs'][ayah] = {'status': 'auto', 'chunks': en_chunks}
        merged += 1
    save(en_path, doc)
    print(f'merged {merged} English ayah(s), skipped {skipped} -> {en_path}')


def merge_bn(raw_bn):
    if not os.path.exists(en_path):
        raise SystemExit(f'abort: {en_path} does not exist - the Bangla overlay needs English chunks first')
    en_doc = load(en_path)
    if en_doc.get('schema_version') != '2.0':
        raise SystemExit('abort: English file is not schema 2.0 flat chunks')
    doc = open_doc(bn_path, 'bn')
    merged = skipped = 0
    for key, ayah, fragments in keyed(raw_bn):
        if locked(doc, ayah, key):
            skipped += 1
            continue
        if ayah not in en_doc['ayahs']:
            raise SystemExit(f'abort: {key} has no English annotation')
        if not isinstance(fragments, list) or not all(isinstance(x, str) and x.strip() for x in fragments):
            raise SystemExit(f'abort: {key} - expected a flat list of non-empty Bangla strings')
        chunks = en_doc['ayahs'][ayah]['chunks']
        if len(fragments) != len(chunks):
            raise SystemExit(f'abort: {key} - {len(fragments)} Bangla fragments for {len(chunks)} chunks')
        doc['ayahs'][ayah] = {
            'status': 'auto',
            'chunks': [{'words': chunk['words'], 'bn': fragments[i]} for i, chunk in enumerate(chunks)],
        }
        merged += 1
    save(bn_path, doc)
    print(f'merged {merged} Bangla overlay ayah(s), skipped {skipped} -> {bn_path}')


if args.lang == 'en':
    merge_en(raw)
elif args.lang == 'bn':
    merge_bn(raw)
else:
    raw_en = {key: [{'words': c['words'], 'en': c['en']} for c in raw_chunks(value)]
              for key, value in raw.items()}
    raw_bn = {key: [c['bn'] for c in raw_chunks(value)] for key, value in raw.items()}
    merge_en(raw_en)
    merge_bn(raw_bn)
print(f'next: python3 qa.py --surah {args.surah} --annotations-dir {os.path.relpath(args.out_dir, ROOT)}')
