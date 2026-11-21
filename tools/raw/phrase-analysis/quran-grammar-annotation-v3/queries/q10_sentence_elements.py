"""Q10  What are the subject, predicate, object and other grammatical elements of a sentence?

Usage: python3 queries/q10_sentence_elements.py 10846
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'What are the subject, predicate, object and other grammatical elements?'
KIND = 'original'
LIMITS = 'Relation labels are the Treebank\'s (Subj, Pred, Obj, Poss, Adj, link, gen, ...); implicit elements are included and marked.'
ARGS = [('sentence', 'sentence id', ...)]
DEMO = {'sentence': '10846'}
CHECK = lambda a: any(x['word'] == '67:15:5' for x in a['elements']['Obj']) and any(x['implicit'] for x in a['elements']['Subj'])


def answer(sentence):
    s = sentences()[str(sentence)]
    el = collections.OrderedDict()
    for n in s['nodes']:
        if n['rel'] == 'NonRel':
            continue
        text = n['morphology']['text_uthmani'] if n['implicit'] else next(sg['text_uthmani'] for sg in words()[n['word']]['segments'] if sg['location'] == n['segment'])
        el.setdefault(n['rel'], []).append({'token_id': n['token_id'], 'word': n['word'], 'text': text, 'pos': node_pos(n),
                                            'head_token': n['head'], 'implicit': n['implicit']})
    return {'sentence_id': int(sentence), 'text': ' '.join(word_text(k) for k in s['words']), 'elements': el}


if __name__ == '__main__':
    run(sys.modules[__name__])
