"""Q13  Which particles occur in the sentence, and how do word order and particles shape it?

Usage: python3 queries/q13_particles_in_sentence.py 10846
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'How do word order and particles affect the sentence?'
KIND = 'partial'
LIMITS = 'The data lists every particle with its POS and syntactic relation and gives the word order as POS and function sequences. It does NOT say what a particle does to the meaning.'
ARGS = [('sentence', 'sentence id', ...)]
DEMO = {'sentence': '10846'}
CHECK = lambda a: any(p['pos'] == 'P' and p['segment'] == '67:15:4:1' for p in a['particles']) and len(a['pos_sequence']) == 6


def answer(sentence):
    s = sentences()[str(sentence)]
    P = ref(1)['pos']
    parts = []
    for n in s['nodes']:
        p = node_pos(n)
        if p in G.NOT_PARTICLES or n['implicit']:
            continue
        sg = next(g for g in words()[n['word']]['segments'] if g['location'] == n['segment'])
        parts.append({'segment': n['segment'], 'text': sg['text_uthmani'], 'pos': p, 'pos_en': P.get(p, {}).get('en'),
                      'relation': n['rel'], 'head_token': n['head']})
    return {'sentence_id': int(sentence), 'text': ' '.join(word_text(k) for k in s['words']), 'particles': parts,
            'pos_sequence': s['derived']['pos_sequence']['all_segments'], 'function_sequence': s['derived']['function_sequence']['without_NonRel']}


if __name__ == '__main__':
    run(sys.modules[__name__])
