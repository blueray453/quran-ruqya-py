"""Q14  Which words, roots, parts of speech, functions and particles occur most often?

Usage: python3 queries/q14_frequencies.py --by lemma --n 20      (by: lemma | root | pos | function | particle)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which words, roots and grammatical constructions occur most frequently?'
KIND = 'research'
LIMITS = 'Counts segments (lemma, root, pos, particle) or whole words (function); no frequency weighting by surah or length.'
ARGS = [('by', 'lemma | root | pos | function | particle', 'lemma'), ('n', 'how many', 20)]
DEMO = {'by': 'lemma', 'n': 5}
CHECK = lambda a: a['top'][0]['count'] > 1000


def answer(by='lemma', n=20):
    c, ar = collections.Counter(), {}
    for w in words().values():
        for s in w['segments']:
            if by == 'lemma' and 'lemma' in s:
                c[s['lemma']['bw']] += 1
                ar[s['lemma']['bw']] = s['lemma']['ar']
            elif by == 'root' and 'root' in s:
                c[s['root']['bw']] += 1
                ar[s['root']['bw']] = s['root']['ar']
            elif by == 'pos':
                c[s['pos']] += 1
            elif by == 'particle' and s['pos'] not in G.NOT_PARTICLES:
                c[s['pos']] += 1
        if by == 'function' and w['segments']:
            c[w['derived']['projections']['function_without_NonRel']] += 1
    return {'by': by, 'distinct': len(c), 'top': [{'item': k, 'arabic': ar.get(k), 'count': v} for k, v in c.most_common(int(n))]}


if __name__ == '__main__':
    run(sys.modules[__name__])
