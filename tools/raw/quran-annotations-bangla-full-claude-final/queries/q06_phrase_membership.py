"""Q06  Which words belong together with this word in a phrase or clause?

Usage: python3 queries/q06_phrase_membership.py 67:15:4
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which words belong together in a phrase?'
KIND = 'original'
LIMITS = 'Only the constituents the Treebank marks (NS, VS, CS, PP, SC, S) are available; idafa and adjective-noun phrases are visible through the relations (see Q07, Q15), not as constituents.'
ARGS = [('key', 'word key surah:ayah:word', ...)]
DEMO = {'key': '67:15:4'}
CHECK = lambda a: any(c['tag'] == 'PP' and c['words'] == ['67:15:4'] for c in a['constituents'])


def answer(key):
    s = sentence_of_word(key)
    T = ref(1)['constituent_tags']
    cons = [{'tag': c['tag'], 'tag_en': T.get(c['tag'], {}).get('en'), 'words': c['words'],
             'text': ' '.join(word_text(x) for x in c['words']), 'treebank_text': c['text'],
             'token_span': c['token_span']} for c in s['constituents'] if key in c['words']]
    return {'word': key, 'sentence_id': s['sentence_id'], 'constituents': cons}


if __name__ == '__main__':
    run(sys.modules[__name__])
