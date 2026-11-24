"""Q22  How is this verb used? (object, subject, prepositions it goes with)

Usage: python3 queries/q22_verb_patterns.py Ealima          (the verb's dictionary form in English letters; Ealima = عَلِمَ)
       python3 queries/q22_verb_patterns.py "'aAmana"        (quote verbs whose letters contain an apostrophe)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
import study_data as D

QUESTION = 'How is this verb used: with an object, with which kind of subject, with which prepositions?'
KIND = 'research'
LIMITS = 'Counts the Treebank relations around each occurrence. "Object" includes a quoted statement after "said". A verb can have several categories in one use.'
ARGS = [('lemma', 'verb in Buckwalter letters', ...)]
DEMO = {'lemma': 'Ealima'}
CHECK = lambda a: a['occurrences'] == 382 and a['with_object'] > 200 and a['forms'] == {'I': 382}


def answer(lemma):
    X = D.SyntaxIndex()
    n = obj = sa = ss = si = pas = 0
    forms, preps, ex = collections.Counter(), collections.Counter(), None
    for k, w in words().items():
        for vf in w['derived']['verb_forms']:
            s = X.seg[(k, vf['segment'])]
            if s.get('lemma', {}).get('bw') != lemma:
                continue
            node, sid = X.node(s)
            deps = X.dependents(sid, node)
            n += 1
            forms[vf['value']] += 1
            ex = ex or {'word': k, 'text': w['text_indopak']}
            obj += any(d['rel'] == 'Obj' for d in deps)
            pas += any(d['rel'] == 'Pass' for d in deps)
            subj = [d for d in deps if d['rel'] == 'Subj' or d['rel'].lower().startswith('subj')]
            sa += any(not d['implicit'] and d['word'] == k for d in subj)
            ss += any(not d['implicit'] and d['word'] != k for d in subj)
            si += any(d['implicit'] for d in subj)
            for d in deps:
                if d['rel'] == 'link' and node_pos(d) == 'P':
                    sp = X.seg_of(d)
                    preps[D.prep_id(sp) if sp else '(implicit)'] += 1
    return {'verb': lemma, 'occurrences': n, 'forms': dict(forms), 'with_object': obj, 'with_passive_subject': pas, 'subject_attached_to_verb': sa,
            'subject_separate_word': ss, 'subject_implicit': si, 'prepositions': preps.most_common(8), 'first_example': ex}


if __name__ == '__main__':
    run(sys.modules[__name__])
