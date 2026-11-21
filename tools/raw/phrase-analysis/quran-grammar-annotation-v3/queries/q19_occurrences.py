"""Q19  Where else does this root, lemma or word occur in the Quran?

Usage: python3 queries/q19_occurrences.py --root jEl
       python3 queries/q19_occurrences.py --lemma jaEala --limit 10
       python3 queries/q19_occurrences.py --text جعل
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Where else does the word, lemma or root occur?'
KIND = 'research'
LIMITS = 'Root and lemma are Buckwalter strings as in the Treebank; --text searches the normalized (unvocalised) spelling.'
ARGS = [('root', 'root in Buckwalter, e.g. jEl', None), ('lemma', 'lemma in Buckwalter, e.g. jaEala', None),
        ('text', 'normalized Arabic text', None), ('pos', 'part of speech tag', None), ('limit', 'occurrences to list', 20)]
DEMO = {'root': 'jEl', 'limit': 5}
CHECK = lambda a: a['count'] > 100 and len(a['all_words_sample']) == 5


def answer(root=None, lemma=None, text=None, pos=None, limit=20):
    hits = G.find(root=root, lemma=lemma, text=text, pos=pos)
    W = words()
    lem = collections.Counter(s['lemma']['bw'] for k in hits for s in W[k]['segments'] if 'lemma' in s and (not root or s.get('root', {}).get('bw') == root))
    return {'count': len(hits), 'lemmas': dict(lem.most_common(10)),
            'all_words_sample': [{'word': k, 'text': W[k]['text_indopak'], 'gloss': next((s['gloss'] for s in W[k]['segments'] if 'gloss' in s), None),
                                  'sentence_id': W[k]['sentence_id']} for k in hits[:int(limit)]]}


if __name__ == '__main__':
    run(sys.modules[__name__])
