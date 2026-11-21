"""Q15  Where can I find other Quranic examples of a grammatical construction?

Usage: python3 queries/q15_examples_of_construction.py --relation Poss
       python3 queries/q15_examples_of_construction.py --pos_sequence "P N"
       python3 queries/q15_examples_of_construction.py --function_sequence "link gen"
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which Quranic examples should I study to learn a particular grammatical concept?'
KIND = 'research'
LIMITS = 'A construction is found by relation label (e.g. Poss = idafa possessor, Adj = adjective) or by a POS / function sequence inside one sentence; nothing is ranked by pedagogical value.'
ARGS = [('relation', 'relation label such as Poss, Adj, Obj, Subj', None), ('pos_sequence', 'space-separated POS labels (all-segments projection)', None),
        ('function_sequence', 'space-separated function labels (without NonRel)', None), ('limit', 'examples to show', 10)]
DEMO = {'relation': 'Poss', 'limit': 3}
CHECK = lambda a: a['total'] > 1000 and len(a['examples']) == 3


def answer(relation=None, pos_sequence=None, function_sequence=None, limit=10):
    S = sentences()
    ex, total = [], 0
    if relation:
        for sid, s in S.items():
            for n in s['nodes']:
                if n['rel'] == relation and n['word']:
                    total += 1
                    if len(ex) < int(limit):
                        h = s['nodes'][n['head']]
                        ex.append({'word': n['word'], 'text': word_text(n['word']), 'head_word': h.get('word'), 'sentence_id': int(sid)})
    else:
        seq = (pos_sequence or function_sequence or '').split()
        key = ('pos_sequence', 'all_segments') if pos_sequence else ('function_sequence', 'without_NonRel')
        for sid, s in S.items():
            lab = s['derived'][key[0]][key[1]]
            for i in range(len(lab) - len(seq) + 1):
                if lab[i:i + len(seq)] == seq:
                    total += 1
                    if len(ex) < int(limit):
                        ws = s['words'][i:i + len(seq)]
                        ex.append({'first_word': ws[0], 'last_word': ws[-1], 'text': ' '.join(word_text(k) for k in ws), 'sentence_id': int(sid)})
    return {'total': total, 'examples': ex}


if __name__ == '__main__':
    run(sys.modules[__name__])
