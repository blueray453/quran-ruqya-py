#!/usr/bin/env python3
"""tools/collect.py — merge raw LLM annotation output into the annotation layer.

  --lang both   (default for the combined pass) raw per ayah = list of clauses, clause =
                list of phrases {"words": [first,last] | [n] | full list, "en": "...", "bn": "..."}.
                Splits into the English file (annotations/surah-NNN.json) and the Bangla
                overlay (annotations/bn/surah-NNN.json) — two files, identical spans.
  --lang en     legacy two-pass: segmentation only ({"words": [...], "en": "..."}).
  --lang bn     legacy two-pass: flat list of Bangla strings, aligned positionally.

Marks merged ayahs `status: auto`; refuses to overwrite `reviewed` ayahs unless --force.
Refuses to touch the bundled prototype-replay sample unless --force (use --out-dir for pilots).
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, expand_words  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--surah', type=int, required=True)
ap.add_argument('--file', required=True, help='raw LLM output JSON file')
ap.add_argument('--lang', choices=['both', 'en', 'bn'], default='both')
ap.add_argument('--out-dir', default=os.path.join(ROOT, 'annotations'),
                help='annotation directory to write (default: annotations/)')
ap.add_argument('--model', default=None, help='model id recorded in provenance')
ap.add_argument('--force', action='store_true', help='overwrite reviewed ayahs / prototype sample')
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
        'schema_version': '1.0',
        'conventions_version': '2.2',
        'surah': args.surah,
        'language': lang,
        'provenance': {
            'generator': 'llm-annotation',
            'model': args.model,
            'note': ('Merged from raw LLM output by tools/collect.py.' if lang == 'en' else
                     'Bangla overlay merged by tools/collect.py; structure mirrors the English file.'),
        },
        'ayahs': {},
    }


def open_doc(path, lang):
    if os.path.exists(path):
        doc = load(path)
        if doc.get('provenance', {}).get('generator') == 'prototype-replay' and not args.force:
            raise SystemExit(f'abort: {os.path.relpath(path, ROOT)} is the bundled prototype sample; '
                             f'write pilots elsewhere with --out-dir (or pass --force)')
        return doc
    return new_doc(lang)


def save(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)


def keyed(raw_dict):
    for key, val in raw_dict.items():
        s, a = key.split(':')
        assert int(s) == args.surah, f'key {key} does not belong to surah {args.surah}'
        yield key, a, val


def locked(doc, a, key):
    prev = doc['ayahs'].get(a)
    if prev and prev.get('status') == 'reviewed' and not args.force:
        print(f'skip {key} (status=reviewed; use --force to overwrite)')
        return True
    return False


def merge_en(raw_en):
    doc = open_doc(en_path, 'en')
    merged = skipped = 0
    for key, a, clauses in keyed(raw_en):
        if locked(doc, a, key):
            skipped += 1
            continue
        norm = []
        for cl in clauses:
            phs = [{'words': expand_words(ph['words']), 'en': ph['en']} for ph in cl]
            norm.append({'words': [w for ph in phs for w in ph['words']], 'phrases': phs})
        doc['ayahs'][a] = {'status': 'auto', 'clauses': norm}
        merged += 1
    save(en_path, doc)
    print(f'merged {merged} en ayah(s), skipped {skipped} -> {en_path}')


def flat_en_phrases(entry):
    return [ph for cl in entry['clauses'] for ph in cl['phrases']]


def merge_bn(raw_bn):
    if not os.path.exists(en_path):
        raise SystemExit(f'abort: {en_path} does not exist - the bn overlay needs the English segmentation first')
    en_doc = load(en_path)
    doc = open_doc(bn_path, 'bn')
    merged = skipped = 0
    for key, a, frags in keyed(raw_bn):
        if locked(doc, a, key):
            skipped += 1
            continue
        if a not in en_doc['ayahs']:
            raise SystemExit(f'abort: {key} has no English annotation')
        if not isinstance(frags, list) or not all(isinstance(x, str) for x in frags):
            raise SystemExit(f'abort: {key} - expected a flat list of Bangla strings')
        phrases = flat_en_phrases(en_doc['ayahs'][a])
        if len(frags) != len(phrases):
            raise SystemExit(f'abort: {key} - {len(frags)} fragments for {len(phrases)} phrases')
        norm, i = [], 0
        for cl in en_doc['ayahs'][a]['clauses']:
            n = len(cl['phrases'])
            norm.append({'words': cl['words'],
                         'phrases': [{'words': ph['words'], 'bn': frags[i + j]}
                                     for j, ph in enumerate(cl['phrases'])]})
            i += n
        doc['ayahs'][a] = {'status': 'auto', 'clauses': norm}
        merged += 1
    save(bn_path, doc)
    print(f'merged {merged} bn ayah(s), skipped {skipped} -> {bn_path}')


if args.lang == 'en':
    merge_en(raw)
elif args.lang == 'bn':
    merge_bn(raw)
else:
    raw_en = {k: [[{'words': ph['words'], 'en': ph['en']} for ph in cl] for cl in v] for k, v in raw.items()}
    raw_bn = {k: [ph['bn'] for cl in v for ph in cl] for k, v in raw.items()}
    merge_en(raw_en)
    merge_bn(raw_bn)
print(f'next: python3 qa.py --surah {args.surah} --annotations-dir {os.path.relpath(args.out_dir, ROOT)}')
