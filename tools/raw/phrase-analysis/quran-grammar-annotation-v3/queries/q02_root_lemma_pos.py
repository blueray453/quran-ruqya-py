"""Q02  What is the root, lemma and part of speech of this word?

Usage: python3 queries/q02_root_lemma_pos.py 67:15:3
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'What is its root, lemma and part of speech?'
KIND = 'original'
LIMITS = 'Prefixes, pronoun suffixes and many particles have no root or lemma in the source. The root/lemma meaning is not part of the data.'
ARGS = [('key', 'word key surah:ayah:word', ...)]
DEMO = {'key': '67:15:3'}
CHECK = lambda a: (a['segments'][0]['root']['bw'], a['segments'][0]['lemma']['bw'], a['segments'][0]['pos']) == ('jEl', 'jaEala', 'V')


def answer(key):
    R = ref()
    out = []
    for s in words()[key]['segments']:
        p = R['pos'].get(s['pos'], {})
        out.append({'segment': s['location'], 'type': s['type'], 'pos': s['pos'], 'pos_en': p.get('en'), 'pos_ar': s.get('pos_ar'),
                    'lemma': s.get('lemma'), 'root': s.get('root'),
                    'root_lexicon_size': R['roots'].get(s.get('root', {}).get('bw'), {}).get('size'),
                    'lemma_lexicon_size': R['lemmas'].get(s.get('lemma', {}).get('bw'), {}).get('size')})
    return {'word': key, 'text_indopak': words()[key]['text_indopak'], 'segments': out}


if __name__ == '__main__':
    run(sys.modules[__name__])
