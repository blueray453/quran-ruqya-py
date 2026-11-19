#!/usr/bin/env python3
"""Answer grammar questions directly from the two JSON layers (no CSV needed).

  python3 src/queries.py word 67:15:3
  python3 src/queries.py sentence 10846
  python3 src/queries.py find --root jEl | --lemma jaEala | --pos V | --function Poss | --text جعل
  python3 src/queries.py verbforms
  python3 src/queries.py derived-nouns
  python3 src/queries.py top --by lemma|root|pos|function [--n 20]
  python3 src/queries.py sequences --kind pos_all_segments [--min-len 2] [--top 20]

`sequences` uses the same definition as the original phrase analysis: consecutive complete written words, never
crossing a sentence boundary, kept when they occur at least twice; "stand-alone" counts occurrences that are not
inside a longer repeated sequence (total = stand-alone + inside-longer).
"""
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sequence_engine as E

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output')
KINDS = {'pos_stem': ('pos_sequence', 'stem'), 'pos_all_segments': ('pos_sequence', 'all_segments'),
         'function_all': ('function_sequence', 'all'), 'function_without_NonRel': ('function_sequence', 'without_NonRel'),
         'function_stem': ('function_sequence', 'stem')}
_cache = {}


def load(out_dir=OUT):
    if out_dir not in _cache:
        def j(fn):
            with open(os.path.join(out_dir, fn), encoding='utf-8') as f:
                return json.load(f)
        w = j('indopak-nastaleeq-wbw-grammar-normalized.json')
        s = j('indopak-nastaleeq-sentence-grammar-normalized.json')
        _cache[out_dir] = (w, s)
    return _cache[out_dir]


def stems(word):
    return [s for s in word['segments'] if s['type'] == 'STEM']


def word_view(key, out_dir=OUT):
    """Everything known about one written word, with its syntax nodes joined in from the sentence layer."""
    W, S = load(out_dir)
    w = W['words'][key]
    nodes = []
    for seg in w['segments']:
        sid = seg['syntax_ref']['sentence_id']
        n = S['sentences'][str(sid)]['nodes'][seg['syntax_ref']['token_id']]
        head = S['sentences'][str(sid)]['nodes'][n['head']]
        nodes.append({'segment': seg['location'], 'rel': n['rel'], 'rel_ar': n.get('rel_ar'),
                      'head_token': n['head'], 'head_word': head['word'], 'head_pos': head.get('pos') or head['morphology']['pos']})
    return {'key': key, 'word': w, 'syntax': nodes}


def find(out_dir=OUT, root=None, lemma=None, pos=None, text=None, function=None):
    """Locations of words matching ALL given criteria (root/lemma in Buckwalter as in the Treebank)."""
    W, S = load(out_dir)
    hits = []
    for k, w in W['words'].items():
        segs = w['segments']
        if root and not any(s.get('root', {}).get('bw') == root for s in segs):
            continue
        if lemma and not any(s.get('lemma', {}).get('bw') == lemma for s in segs):
            continue
        if pos and not any(s['pos'] == pos for s in segs):
            continue
        if text and text not in w['text_normalized']:
            continue
        if function and (not segs or function not in w['derived']['projections']['function_all'].split('+')):
            continue
        hits.append(k)
    return hits


def verb_form_table(out_dir=OUT):
    W, _ = load(out_dir)
    rows = collections.OrderedDict((f, {'explicit': 0, 'inferred': 0, 'roots': set(), 'lemmas': set(), 'words': []})
                                   for f in W['reference_data']['verb_forms'])
    root_forms = collections.defaultdict(set)
    for k, w in W['words'].items():
        if not w['segments']:
            continue
        for vf in w['derived']['verb_forms']:
            seg = next(s for s in w['segments'] if s['location'] == vf['segment'])
            r = rows[vf['value']]
            r[vf['basis']] += 1
            r['words'].append(k)
            if 'root' in seg:
                r['roots'].add(seg['root']['bw'])
                root_forms[seg['root']['bw']].add(vf['value'])
            if 'lemma' in seg:
                r['lemmas'].add(seg['lemma']['bw'])
    return rows, root_forms


def derived_noun_table(out_dir=OUT):
    W, _ = load(out_dir)
    t = collections.OrderedDict()
    for k, w in W['words'].items():
        if not w['segments']:
            continue
        for d in w['derived']['derived_nouns']:
            seg = next(s for s in w['segments'] if s['location'] == d['segment'])
            r = t.setdefault(d['type'], {'count': 0, 'roots': set(), 'lemmas': set()})
            r['count'] += 1
            if 'root' in seg:
                r['roots'].add(seg['root']['bw'])
            if 'lemma' in seg:
                r['lemmas'].add(seg['lemma']['bw'])
    return t


def repeated_sequences(seqs, min_count=2, coverage_lengths=(1, 2, 3, 5, 8)):
    """Repeated consecutive sequences over a list of sentences (each a list of labels); see sequence_engine.py.

    Returns (rows, coverage). rows: dicts {length, sequence, total, stand_alone, inside_longer}.
    coverage[L] = share of word positions inside a repeated sequence of length >= L."""
    units, _, _ = E.find_repeated(seqs, min_count)
    rows = [{'length': u['length'], 'sequence': list(u['labels']), 'total': len(u['starts']),
             'stand_alone': sum(u['alone']), 'inside_longer': len(u['starts']) - sum(u['alone'])} for u in units]
    return rows, E.coverage_by_min_length(units, sum(len(x) for x in seqs), coverage_lengths)


def sequences(kind, out_dir=OUT, min_count=2):
    _, S = load(out_dir)
    a, b = KINDS[kind]
    seqs = [s['derived'][a][b] for s in S['sentences'].values() if s['words']]
    return repeated_sequences(seqs, min_count)


# ------------------------------------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out-dir', default=OUT)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('word').add_argument('key')
    sub.add_parser('sentence').add_argument('id')
    f = sub.add_parser('find')
    for x in ('root', 'lemma', 'pos', 'text', 'function'):
        f.add_argument('--' + x)
    sub.add_parser('verbforms')
    sub.add_parser('derived-nouns')
    t = sub.add_parser('top')
    t.add_argument('--by', required=True, choices=['lemma', 'root', 'pos', 'function'])
    t.add_argument('--n', type=int, default=20)
    q = sub.add_parser('sequences')
    q.add_argument('--kind', required=True, choices=list(KINDS))
    q.add_argument('--min-len', type=int, default=2)
    q.add_argument('--top', type=int, default=20)
    a = ap.parse_args()
    W, S = load(a.out_dir)

    if a.cmd == 'word':
        print(json.dumps(word_view(a.key, a.out_dir), ensure_ascii=False, indent=1))
    elif a.cmd == 'sentence':
        print(json.dumps(S['sentences'][a.id], ensure_ascii=False, indent=1))
    elif a.cmd == 'find':
        hits = find(a.out_dir, a.root, a.lemma, a.pos, a.text, a.function)
        print(len(hits), 'words')
        for k in hits[:50]:
            print(k, W['words'][k]['text_indopak'])
        if len(hits) > 50:
            print('...')
    elif a.cmd == 'verbforms':
        rows, rf = verb_form_table(a.out_dir)
        print('%-5s %9s %9s %7s %7s %7s' % ('form', 'explicit', 'inferred', 'total', 'roots', 'lemmas'))
        for f_, r in rows.items():
            print('%-5s %9d %9d %7d %7d %7d' % (f_, r['explicit'], r['inferred'], r['explicit'] + r['inferred'], len(r['roots']), len(r['lemmas'])))
        print('roots used in more than one form:', sum(1 for v in rf.values() if len(v) > 1), 'of', len(rf))
    elif a.cmd == 'derived-nouns':
        print('%-12s %7s %7s %7s' % ('type', 'count', 'roots', 'lemmas'))
        for k, r in sorted(derived_noun_table(a.out_dir).items(), key=lambda x: -x[1]['count']):
            print('%-12s %7d %7d %7d' % (k, r['count'], len(r['roots']), len(r['lemmas'])))
    elif a.cmd == 'top':
        c = collections.Counter()
        for w in W['words'].values():
            for s in w['segments']:
                if a.by == 'lemma' and 'lemma' in s:
                    c[s['lemma']['bw']] += 1
                elif a.by == 'root' and 'root' in s:
                    c[s['root']['bw']] += 1
                elif a.by == 'pos':
                    c[s['pos']] += 1
            if a.by == 'function' and w['segments']:
                c[w['derived']['projections']['function_all']] += 1
        for k, v in c.most_common(a.n):
            print('%7d  %s' % (v, k))
    elif a.cmd == 'sequences':
        rows, cov = sequences(a.kind, a.out_dir)
        print('repeated sequences:', len(rows), '| longest:', max(r['length'] for r in rows))
        print('word positions inside a repeated sequence of length >= L:',
              ', '.join('L=%d: %.1f%%' % (k, 100 * v) for k, v in sorted(cov.items())))
        rows = [r for r in rows if r['length'] >= a.min_len]
        rows.sort(key=lambda r: (-r['total'], r['length']))
        print('%7s %7s %7s  len  sequence' % ('total', 'alone', 'inside'))
        for r in rows[:a.top]:
            print('%7d %7d %7d  %3d  %s' % (r['total'], r['stand_alone'], r['inside_longer'], r['length'], ' '.join(r['sequence'])))


if __name__ == '__main__':
    main()
