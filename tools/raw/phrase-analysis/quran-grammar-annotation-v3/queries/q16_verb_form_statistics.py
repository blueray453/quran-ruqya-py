"""Q16  How are Quranic verbs distributed over Forms I-XII? Which roots occur in several forms?

Usage: python3 queries/q16_verb_form_statistics.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'How many verb occurrences, roots and lemmas belong to each form, and which roots use several forms?'
KIND = 'research'
LIMITS = 'Counts verbs only (POS V). Form I is inferred for every unmarked verb. Nouns carrying a form annotation are excluded.'
ARGS = []
DEMO = {}


def CHECK(a):
    m = load()[0]['metadata']['counts']
    return (a['totals']['explicit'], a['totals']['inferred']) == (m['verb_form_explicit'], m['verb_form_inferred_I']) and a['forms']['I']['explicit'] == 0


def answer():
    rows, rf = G.verb_form_table()
    forms = collections.OrderedDict((f, {'explicit': r['explicit'], 'inferred': r['inferred'], 'total': r['explicit'] + r['inferred'],
                                         'distinct_roots': len(r['roots']), 'distinct_lemmas': len(r['lemmas'])}) for f, r in rows.items())
    multi = {r: dict(c) for r, c in rf.items() if len(c) > 1}
    return {'forms': forms, 'totals': {'explicit': sum(r['explicit'] for r in forms.values()), 'inferred': sum(r['inferred'] for r in forms.values())},
            'roots_total': len(rf), 'roots_in_more_than_one_form': len(multi),
            'roots_with_most_forms': sorted(([r, len(c)] for r, c in multi.items()), key=lambda x: -x[1])[:10]}


if __name__ == '__main__':
    run(sys.modules[__name__])
