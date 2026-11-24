"""Q23  How hard is this ayah? Which words does it contain, and how common is each?

Usage: python3 queries/q23_ayah_vocabulary.py 1:2
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which dictionary words does this ayah contain, how frequent is each, and how much is covered by common words?'
KIND = 'research'
LIMITS = 'Frequency is counted over the whole Quran by dictionary word (lemma); pronouns and some particles have no lemma and are not counted.'
ARGS = [('ayah', 'ayah as surah:ayah', ...)]
DEMO = {'ayah': '1:2'}
CHECK = lambda a: a['lemma_segments'] == 4 and a['pct_covered_by_top_500'] == 100.0 and a['words_in_ayah'] == 4


def answer(ayah):
    count = collections.Counter(s['lemma']['bw'] for w in words().values() for s in w['segments'] if 'lemma' in s)
    order = sorted(count, key=lambda x: (-count[x], x))
    rank = {lb: i + 1 for i, lb in enumerate(order)}
    rows, nwords = [], 0
    for k, w in words().items():
        if k.rsplit(':', 1)[0] != ayah:
            continue
        nwords += 1
        for s in w['segments']:
            if 'lemma' in s:
                lb = s['lemma']['bw']
                rows.append({'word': k, 'text': w['text_indopak'], 'lemma_bw': lb, 'lemma_ar': s['lemma']['ar'], 'pos': s['pos'], 'gloss': s.get('gloss'),
                             'uses_in_quran': count[lb], 'frequency_rank': rank[lb]})
    n = len(rows)
    pct = lambda N: round(100 * sum(1 for r in rows if r['frequency_rank'] <= N) / n, 1) if n else None
    return {'ayah': ayah, 'words_in_ayah': nwords, 'lemma_segments': n, 'pct_covered_by_top_100': pct(100), 'pct_covered_by_top_500': pct(500),
            'pct_covered_by_top_1000': pct(1000), 'rare_words_5_or_fewer_uses': [r['lemma_ar'] for r in rows if r['uses_in_quran'] <= 5], 'words': rows}


if __name__ == '__main__':
    run(sys.modules[__name__])
