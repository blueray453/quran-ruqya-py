"""Q12  Which grammatical elements are implicit (understood but not written)?

Usage: python3 queries/q12_implicit_elements.py --sentence 10846 | --ayah 67:15
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which grammatical elements are implicit?'
KIND = 'original'
LIMITS = 'Only the 11,157 implicit nodes the Treebank annotates (unwritten subjects, verbs, pronouns). They have no IndoPak word; the anchor says between which written words they sit.'
ARGS = [('sentence', 'a sentence id', None), ('ayah', 'an ayah surah:ayah', None)]
DEMO = {'sentence': '10846'}
CHECK = lambda a: len(a['implicit']) == 1 and a['implicit'][0]['after_word'] == '67:15:3' and a['implicit'][0]['relation'] == 'Subj'


def answer(sentence=None, ayah=None):
    S = sentences()
    if sentence:
        ids = [str(sentence)]
    elif ayah:
        ids = sorted({str(words()[k]['sentence_id']) for k in words() if k.rsplit(':', 1)[0] == ayah}, key=int)
    else:
        ids = list(S)
    out = []
    for i in ids:
        for n in S[i]['nodes']:
            if n['implicit']:
                out.append({'sentence_id': int(i), 'text': n['morphology']['text_uthmani'], 'pos': node_pos(n), 'relation': n['rel'],
                            'head_token': n['head'], 'after_word': n['anchor']['after_word'], 'before_word': n['anchor']['before_word']})
    return {'count': len(out), 'implicit': out if sentence or ayah else out[:25]}


if __name__ == '__main__':
    run(sys.modules[__name__])
