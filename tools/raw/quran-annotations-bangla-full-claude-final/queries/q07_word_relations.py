"""Q07  What is the grammatical relationship between this word and the others (function, head, dependents)?

Usage: python3 queries/q07_word_relations.py 67:15:4
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'What is the grammatical relationship between these words?'
KIND = 'original'
LIMITS = 'Relation labels are the Treebank\'s own; a word with several segments has one relation per segment. The head of a root or NonRel node is the node itself.'
ARGS = [('key', 'word key surah:ayah:word', ...)]
DEMO = {'key': '67:15:4'}
CHECK = lambda a: [x['relation'] for x in a['segments']] == ['link', 'gen'] and a['segments'][1]['head']['pos'] == 'P'


def answer(key):
    out = []
    for x in syntax_of_word(key):
        out.append({'segment': x['segment'], 'relation': x['rel'], 'relation_ar': x['rel_ar'],
                    'head': None if x['head_is_self'] else {'word': x['head_word'], 'text': word_text(x['head_word']) if x['head_word'] else None,
                                                            'pos': x['head_pos'], 'implicit': x['head_implicit']},
                    'dependents': [{'word': d['word'], 'text': word_text(d['word']) if d['word'] else '(implicit)', 'relation': d['rel'],
                                    'pos': d['pos']} for d in x['dependents']]})
    return {'word': key, 'text_indopak': word_text(key), 'segments': out}


if __name__ == '__main__':
    run(sys.modules[__name__])
