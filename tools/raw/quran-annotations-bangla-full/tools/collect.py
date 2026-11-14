#!/usr/bin/env python3
"""tools/collect.py — merge raw LLM annotation output into the annotation layer.

Two languages, two file kinds (Bangla is a SEPARATE overlay file, never a slot
inside the English file):

  default / --lang en   raw output per ayah = list of clauses, clause = list of
                        phrases {"words": [...], "en": "..."}; merged into
                        annotations/surah-NNN.json (creates the segmentation).

  --lang bn             raw output per ayah = a FLAT list of Bangla strings, one
                        per phrase, in phrase order (gloss-only pass; the model
                        never re-segments). Merged into
                        annotations/bn/surah-NNN.json, mirroring the English
                        file's clause/phrase word spans exactly. Requires the
                        English annotation to exist; aborts on phrase-count
                        mismatch.

Normalises clause objects, marks merged ayahs `status: auto`, and refuses to
overwrite `reviewed` ayahs unless --force is given.
"""
import argparse, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument('--surah', type=int, required=True)
ap.add_argument('--file', required=True, help='raw LLM output JSON file')
ap.add_argument('--lang', choices=['en', 'bn'], default='en',
                help='en = segmentation pass (default); bn = Bangla gloss-only overlay pass')
ap.add_argument('--force', action='store_true', help='overwrite reviewed ayahs too')
args = ap.parse_args()

with open(args.file, encoding='utf-8') as fh:
    raw = json.load(fh)

en_path = os.path.join(ROOT, 'annotations', f'surah-{args.surah:03d}.json')
bn_path = os.path.join(ROOT, 'annotations', 'bn', f'surah-{args.surah:03d}.json')


def load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def new_doc(lang):
    return {
        'schema_version': '1.0',
        'conventions_version': '2.1',
        'surah': args.surah,
        'language': lang,
        'provenance': {
            'generator': 'llm-annotation',
            'note': ('Merged from raw LLM output by tools/collect.py (--lang %s).' % lang
                     if lang == 'en' else
                     'Bangla overlay, merged from raw gloss-only LLM output by '
                     'tools/collect.py (--lang bn); structure mirrors the English file.'),
        },
        'ayahs': {},
    }


def flat_en_phrases(en_entry):
    return [ph for cl in en_entry['clauses'] for ph in cl['phrases']]


if args.lang == 'en':
    path = en_path
    doc = load(path) if os.path.exists(path) else new_doc('en')

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

else:  # bn — gloss-only overlay pass
    if not os.path.exists(en_path):
        raise SystemExit(f'abort: {os.path.relpath(en_path, ROOT)} does not exist — '
                         f'the bn pass needs the English segmentation first')
    en_doc = load(en_path)
    doc = load(bn_path) if os.path.exists(bn_path) else new_doc('bn')

    merged, skipped = 0, 0
    for key, frags in raw.items():
        s, a = key.split(':')
        assert int(s) == args.surah, f'key {key} does not belong to surah {args.surah}'
        prev = doc['ayahs'].get(a)
        if prev and prev.get('status') == 'reviewed' and not args.force:
            print(f'skip {key} (status=reviewed; use --force to overwrite)')
            skipped += 1
            continue
        if a not in en_doc['ayahs']:
            raise SystemExit(f'abort: {key} has no English annotation — the bn pass is '
                             f'gloss-only and cannot create ayahs')
        if not isinstance(frags, list) or not all(isinstance(x, str) for x in frags):
            raise SystemExit(f'abort: {key} — expected a flat list of Bangla strings, got '
                             f'{type(frags).__name__}')
        phrases = flat_en_phrases(en_doc['ayahs'][a])
        if len(frags) != len(phrases):
            raise SystemExit(f'abort: {key} — {len(frags)} fragments for {len(phrases)} phrases; '
                             f're-segmentation is forbidden, return exactly one fragment per phrase')
        norm, i = [], 0
        for cl in en_doc['ayahs'][a]['clauses']:
            n_here = len(cl['phrases'])
            norm.append({'words': cl['words'],
                         'phrases': [{'words': ph['words'], 'bn': frags[i + j]}
                                     for j, ph in enumerate(cl['phrases'])]})
            i += n_here
        doc['ayahs'][a] = {'status': 'auto', 'clauses': norm}
        merged += 1

    os.makedirs(os.path.dirname(bn_path), exist_ok=True)
    with open(bn_path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)

    print(f'merged {merged} bn ayah(s), skipped {skipped} -> {bn_path}')
    print(f'next: python3 qa.py --surah {args.surah}')
