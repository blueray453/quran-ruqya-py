"""Q17  Which derived nominal forms (active/passive participles, verbal nouns) occur, and how often?

Usage: python3 queries/q17_derived_nouns.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which derived nominal forms occur, with which roots and lemmas?'
KIND = 'research'
LIMITS = 'Counts nouns and adjectives annotated as ACT_PCPL / PASS_PCPL / VN; they are never counted as verbs.'
ARGS = []
DEMO = {}
CHECK = lambda a: 'ACT_PCPL' in a['types'] and 'V' not in a['types']['ACT_PCPL']['by_pos']


def answer():
    return {'types': {k: {'count': r['count'], 'by_pos': dict(r['by_pos']), 'distinct_roots': len(r['roots']), 'distinct_lemmas': len(r['lemmas'])}
                      for k, r in sorted(G.derived_noun_table().items(), key=lambda x: -x[1]['count'])}}


if __name__ == '__main__':
    run(sys.modules[__name__])
