"""Q05  Why does this verb have this form? Which derived form (I-XII) is it, and is that stated or inferred?

Usage: python3 queries/q05_verb_form.py 67:15:3
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Which verb form (I-XII) is this word, and is the form explicitly annotated or inferred?'
KIND = 'derived'
LIMITS = 'Form I is never written in the source: an unmarked verb is inferred to be Form I (the default in the feature guide). Nouns that carry a form annotation are listed separately and are not verbs.'
ARGS = [('key', 'word key surah:ayah:word', ...)]
DEMO = {'key': '67:15:3'}
CHECK = lambda a: a['is_verb'] and (a['verb_forms'][0]['form'], a['verb_forms'][0]['basis']) == ('I', 'inferred')


def answer(key):
    w = words()[key]
    F = ref()['verb_forms']
    forms = []
    for v in w['derived']['verb_forms']:
        f = F[v['value']]
        forms.append({'segment': v['segment'], 'form': v['value'], 'basis': v['basis'], 'pattern': f['pattern'], 'arabic': f['ar'],
                      'description': f['description_en']})
    return {'word': key, 'text_indopak': w['text_indopak'], 'is_verb': w['derived']['is_verb'], 'verb_forms': forms,
            'nominal_form_annotations_not_counted_as_verbs': w['derived']['nominal_form_annotations']}


if __name__ == '__main__':
    run(sys.modules[__name__])
