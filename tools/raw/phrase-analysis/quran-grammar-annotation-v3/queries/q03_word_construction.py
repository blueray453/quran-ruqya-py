"""Q03  How is the written word morphologically constructed (prefixes, stem, suffixes)?

Usage: python3 queries/q03_word_construction.py 67:15:4
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'How is the written word morphologically constructed?'
KIND = 'original'
LIMITS = 'Segment text is Uthmani spelling, so segments cannot be marked on the IndoPak letters themselves.'
ARGS = [('key', 'word key surah:ayah:word', ...)]
DEMO = {'key': '67:15:4'}
CHECK = lambda a: [s['type'] for s in a['segments']] == ['PREFIX', 'STEM'] and a['prefix_tags'] == ['l:P+']


def answer(key):
    w = words()[key]
    P = ref()['features']['Prefixs']['entries']
    segs = []
    for s in w['segments']:
        d = seg_summary(s)
        if 'prefix' in s:
            d['tag'] = s['prefix']
            d['tag_meaning'] = P.get(s['prefix'], {}).get('English Description')
        if 'suffix' in s:
            d['tag'] = s['suffix']
        segs.append(d)
    return {'word': key, 'text_indopak': w['text_indopak'], 'segments': segs,
            'prefix_tags': w['derived']['prefix_tags'], 'suffix_tags': w['derived']['suffix_tags'],
            'pattern': ' + '.join(s['type'] + ':' + s['pos'] for s in w['segments'])}


if __name__ == '__main__':
    run(sys.modules[__name__])
