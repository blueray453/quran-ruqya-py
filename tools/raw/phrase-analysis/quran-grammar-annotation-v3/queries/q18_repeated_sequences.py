"""Q18  Which POS / function sequences repeat, and where?   (needs stage 04: output/sequences/)

Usage: python3 queries/q18_repeated_sequences.py --kind pos --id P00001
       python3 queries/q18_repeated_sequences.py --kind function --sequence "link gen Poss"
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which grammatical sequences recur, how often, and where (total vs stand-alone)?'
KIND = 'research'
LIMITS = 'Reads the sequence annotation JSON written by stage 04 (default projections: all-segment POS, function without NonRel). Never crosses sentence boundaries.'
ARGS = [('kind', 'pos | function', 'pos'), ('id', 'unit id such as P00001 / F00001', None), ('sequence', 'labels separated by spaces', None), ('limit', 'occurrences to show', 5)]
DEMO = {'kind': 'pos', 'id': 'P00001'}
CHECK = lambda a: a['unit']['total_count'] == a['unit']['stand_alone_count'] + a['unit']['inside_longer_count'] > 0


def answer(kind='pos', id=None, sequence=None, limit=5):
    path = os.path.join(G.OUT, 'sequences', 'quran-%s-sequences-annotation.json' % kind)
    if not os.path.exists(path):
        return {'error': 'run pipeline/04_generate_csv.py first (missing %s)' % path}
    with open(path, encoding='utf-8') as f:
        A = json.load(f)
    unit = next((u for u in A['units'] if u['id'] == id or (sequence and ' '.join(u['sequence']) == sequence)), None)
    if unit is None:
        return {'error': 'no repeated unit found'}
    n, alone = unit['length'], set(unit['stand_alone_occurrences'])
    occ = [{'sentence_id': A['sentence_index'][s], 'start_word': A['word_index'][s], 'end_word': A['word_index'][s + n - 1],
            'text': ' '.join(word_text(k) for k in A['word_index'][s:s + n]), 'stand_alone': s in alone}
           for s in unit['occurrences'][:int(limit)]]
    return {'projection': A['metadata']['projection'], 'unit': {k: unit[k] for k in ('id', 'length', 'sequence', 'total_count', 'stand_alone_count',
                                                                                       'inside_longer_count', 'sentences_total', 'sentences_stand_alone')},
            'first_occurrences': occ}


if __name__ == '__main__':
    run(sys.modules[__name__])
