"""Q09  Where do the sentence and clause boundaries lie? Does the sentence cross ayahs?

Usage: python3 queries/q09_sentence_boundaries.py --key 67:15:3 | --ayah 67:15 | --sentence 10846
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Where are the sentence and clause boundaries?'
KIND = 'original'
LIMITS = 'Boundaries are the Treebank\'s sentence ids (which are syntactic units, not punctuation). 26 sentences are prefix-only fragments that own no written word.'
ARGS = [('key', 'a word key surah:ayah:word', None), ('ayah', 'an ayah surah:ayah', None), ('sentence', 'a sentence id', None)]
DEMO = {'key': '67:15:3'}
CHECK = lambda a: a['sentences'][0]['sentence_id'] == 10846 and (a['sentences'][0]['first_word'], a['sentences'][0]['last_word']) == ('67:15:1', '67:15:6')


def answer(key=None, ayah=None, sentence=None):
    S, W = sentences(), words()
    ids = []
    if sentence:
        ids = [str(sentence)]
    elif key:
        ids = sorted({str(sg['syntax_ref']['sentence_id']) for sg in W[key]['segments']}, key=int)
        ids = [str(W[key]['sentence_id'])] + [i for i in ids if i != str(W[key]['sentence_id'])]
    elif ayah:
        ids = sorted({str(W[k]['sentence_id']) for k in W if k.rsplit(':', 1)[0] == ayah}, key=int)
    out = []
    for i in ids:
        s = S[i]
        out.append({'sentence_id': int(i), 'first_word': s['span']['first_word'], 'last_word': s['span']['last_word'],
                    'ayahs': s['span']['ayahs'], 'crosses_ayah': s['span']['crosses_ayah'], 'word_count': s['derived']['word_count'],
                    'text': ' '.join(word_text(k) for k in s['words']), 'prefix_only_fragment': s['derived']['is_prefix_only_fragment'],
                    'constituents': [{'tag': c['tag'], 'words': [c['first_word'], c['last_word']]} for c in s['constituents']]})
    return {'sentences': out}


if __name__ == '__main__':
    run(sys.modules[__name__])
