"""Q21  Which words belong to this root, and how often and in which forms do they occur?

Usage: python3 queries/q21_root_family.py Elm        (the root in English letters; Elm = علم)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which words belong to this root, and how are they used?'
KIND = 'research'
LIMITS = 'Root and meaning labels come from the Treebank; the gloss is a short word-level label. Words without a root are not included.'
ARGS = [('root', 'root in Buckwalter letters, e.g. Elm', ...)]
DEMO = {'root': 'Elm'}
CHECK = lambda a: a['total_occurrences'] >= 800 and any(w['lemma_bw'] == 'Ealima' for w in a['words'])


def answer(root):
    fam = {}
    surahs = set()
    for k, w, s in ((k, w, s) for k, w in words().items() for s in w['segments']):
        if s.get('root', {}).get('bw') != root:
            continue
        lb = s.get('lemma', {}).get('bw')
        e = fam.setdefault(lb, {'lemma_bw': lb, 'lemma_ar': s.get('lemma', {}).get('ar'), 'count': 0, 'pos': collections.Counter(), 'forms': collections.Counter(),
                                'derived': collections.Counter(), 'glosses': collections.Counter(), 'first_word': k, 'example': w['text_indopak']})
        e['count'] += 1
        e['pos'][s['pos']] += 1
        surahs.add(int(k.split(':')[0]))
        for vf in w['derived']['verb_forms']:
            if vf['segment'] == s['location']:
                e['forms'][vf['value']] += 1
        for d in w['derived']['derived_nouns']:
            if d['segment'] == s['location']:
                e['derived'][d['type']] += 1
        if 'gloss' in s:
            e['glosses'][s['gloss'].strip(' .,"')] += 1
    out = []
    for e in sorted(fam.values(), key=lambda x: -x['count']):
        out.append({'lemma_bw': e['lemma_bw'], 'lemma_ar': e['lemma_ar'], 'count': e['count'], 'word_types': dict(e['pos']), 'verb_forms': dict(e['forms']),
                    'derived_types': dict(e['derived']), 'top_glosses': e['glosses'].most_common(3), 'first_word': e['first_word'], 'example': e['example']})
    return {'root': root, 'total_occurrences': sum(e['count'] for e in fam.values()), 'distinct_words': len(fam), 'surahs': len(surahs), 'words': out}


if __name__ == '__main__':
    run(sys.modules[__name__])
