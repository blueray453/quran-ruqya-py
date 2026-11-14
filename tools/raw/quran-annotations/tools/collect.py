#!/usr/bin/env python3
"""tools/collect.py — merge raw LLM annotation output into annotations/surah-NNN.json.

Input: the raw JSON the model returned, one key per ayah ("surah:ayah"), value =
list of clauses, clause = list of phrases {"words": [...], "en": "..."}.

Normalises clause objects, marks merged ayahs `status: auto`, and refuses to
overwrite `reviewed` ayahs unless --force is given.
"""
import argparse, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument('--surah', type=int, required=True)
ap.add_argument('--file', required=True, help='raw LLM output JSON file')
ap.add_argument('--force', action='store_true', help='overwrite reviewed ayahs too')
args = ap.parse_args()

with open(args.file, encoding='utf-8') as fh:
    raw = json.load(fh)

path = os.path.join(ROOT, 'annotations', f'surah-{args.surah:03d}.json')
if os.path.exists(path):
    with open(path, encoding='utf-8') as fh:
        doc = json.load(fh)
else:
    doc = {
        'schema_version': '1.0',
        'conventions_version': '2.0',
        'surah': args.surah,
        'language': 'en',
        'provenance': {
            'generator': 'llm-annotation',
            'note': 'Merged from raw LLM output by tools/collect.py.',
        },
        'ayahs': {},
    }

merged, skipped = 0, 0
for key, clauses in raw.items():
    s, a = key.split(':')
    assert int(s) == args.surah, f'key {key} does not belong to surah {args.surah}'
    prev = doc['ayahs'].get(a)
    if prev and prev.get('status') == 'reviewed' and not args.force:
        print(f'skip {key} (status=reviewed; use --force to overwrite)')
        skipped += 1
        continue
    norm = []
    for cl in clauses:
        words = [w for ph in cl for w in ph['words']]
        norm.append({'words': words, 'phrases': [{'words': ph['words'], 'en': ph['en']} for ph in cl]})
    doc['ayahs'][a] = {'status': 'auto', 'clauses': norm}
    merged += 1

with open(path, 'w', encoding='utf-8') as fh:
    json.dump(doc, fh, ensure_ascii=False, indent=2)

print(f'merged {merged} ayah(s), skipped {skipped} -> {path}')
print(f'next: python3 qa.py --surah {args.surah}')
