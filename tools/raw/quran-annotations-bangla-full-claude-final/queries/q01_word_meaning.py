"""Q01  What does this word mean in this Quranic context?

Usage: python3 queries/q01_word_meaning.py 67:15:3
Answer: the word-level gloss of every segment, plus the glosses the same lemma carries elsewhere in the Quran,
so you can see whether this occurrence is typical.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'What does this word mean in this Quranic context?'
KIND = 'partial'
LIMITS = 'Only a word-level gloss from the Treebank exists (on 77,915 segments). There is no contextual translation or lexicon entry in the data.'
ARGS = [('key', 'word key surah:ayah:word', ...)]
DEMO = {'key': '67:15:3'}
CHECK = lambda a: a['segments'][0]['gloss'] == 'made'


def answer(key):
    W = words()
    w = W[key]
    lemmas = {s['lemma']['bw'] for s in w['segments'] if 'lemma' in s}
    other = {}
    for lem in sorted(lemmas):
        c = collections.Counter(s['gloss'] for x in W.values() for s in x['segments']
                                if s.get('lemma', {}).get('bw') == lem and 'gloss' in s)
        other[lem] = c.most_common(8)
    return {'word': key, 'text_indopak': w['text_indopak'],
            'segments': [dict(seg_summary(s), gloss=s.get('gloss')) for s in w['segments']],
            'glosses_of_the_same_lemma_in_the_Quran': other}


if __name__ == '__main__':
    run(sys.modules[__name__])
