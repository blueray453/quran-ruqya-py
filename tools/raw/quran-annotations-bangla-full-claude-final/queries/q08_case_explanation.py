"""Q08  Why does this word have its particular grammatical case?

Usage: python3 queries/q08_case_explanation.py 67:15:5
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'Why does each word have its particular grammatical case?'
KIND = 'derived'
LIMITS = 'The source has the case, the relation and the head but no explanation text. The "reason" is a rule applied by this project to those three annotations (grammar_data.CASE_RULES); a case/relation pair without a rule returns no reason instead of a guess.'
ARGS = [('key', 'word key surah:ayah:word', ...)]
DEMO = {'key': '67:15:5'}
CHECK = lambda a: any('object of the verb' in (x['derived_reason'] or '') for x in a['segments'])


def answer(key):
    w = words()[key]
    syn = {x['segment']: x for x in syntax_of_word(key)}
    out = []
    for s in w['segments']:
        if 'case' not in s:
            continue
        x = syn[s['location']]
        head = word_text(x['head_word']) if x['head_word'] else None
        out.append({'segment': s['location'], 'text_uthmani': s['text_uthmani'], 'case': s['case'], 'case_meaning': describe('NominalCase', s['case']),
                    'relation': x['rel'], 'head_word': x['head_word'], 'head_text': head, 'head_pos': x['head_pos'],
                    'derived_reason': G.case_explanation(s['case'], x['rel'], x['head_pos'], head)})
    return {'word': key, 'text_indopak': w['text_indopak'], 'segments': out}


if __name__ == '__main__':
    run(sys.modules[__name__])
