"""Q04  What grammatical features does the word carry (gender, number, case, tense, voice, person, ...)?

Usage: python3 queries/q04_word_features.py 67:15:3
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

QUESTION = 'What grammatical features does it carry?'
KIND = 'original'
LIMITS = 'Features exist only where the Treebank annotates them (for example case only on nouns). Mood descriptions use the corrected English text.'
ARGS = [('key', 'word key surah:ayah:word', ...)]
DEMO = {'key': '67:15:3'}
CHECK = lambda a: a['segments'][0]['features']['aspect']['tag'] == 'PERF' and a['segments'][0]['features']['person']['tag'] == '3'

SHEET = {'aspect': 'VerbState', 'voice': 'VerbVoice', 'state': 'NominalState', 'case': 'NominalCase', 'person': 'Person',
         'gender': 'Gender', 'number': 'Number', 'derived_noun': 'DerivedNoun', 'special_group': 'SpecialGroup'}


def answer(key):
    R = ref()
    out = []
    for s in words()[key]['segments']:
        f = {}
        for field, sheet in SHEET.items():
            if field in s:
                f[field] = {'tag': s[field], 'meaning': describe(sheet, s[field])}
        if 'mood' in s:
            tag = s['mood'].replace('MOOD:', '')
            f['mood'] = {'tag': s['mood'], 'meaning': R['verb_moods'].get(tag, {}).get('description_en')}
        out.append(dict(seg_summary(s), features_raw=s.get('features_raw'), features=f))
    return {'word': key, 'text_indopak': words()[key]['text_indopak'], 'segments': out}


if __name__ == '__main__':
    run(sys.modules[__name__])
