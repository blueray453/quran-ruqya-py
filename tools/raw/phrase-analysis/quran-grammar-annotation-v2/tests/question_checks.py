#!/usr/bin/env python3
"""Acceptance test: the JSON layers must answer the 15 learner questions without opening any source file.

Each check uses ayah 67:15 / sentence 10846 (and corpus-wide queries) and asserts a known, hand-verified answer.
Run after build + validate:  python3 tests/question_checks.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import queries as q

W, S = q.load()
words, sents = W['words'], S['sentences']
fails = []


def check(n, text, cond):
    print(('PASS ' if cond else 'FAIL ') + f'Q{n:<2} {text}')
    if not cond:
        fails.append(n)


v = q.word_view('67:15:3')
seg = v['word']['segments'][0]
check(1, 'meaning of 67:15:3 (word-level gloss)', seg.get('gloss') == 'made')
check(2, 'root, lemma, POS of 67:15:3', (seg['root']['bw'], seg['lemma']['bw'], seg['pos']) == ('jEl', 'jaEala', 'V'))
w4 = words['67:15:4']
check(3, 'morphological construction of 67:15:4 (prefix + stem)',
      [s['type'] for s in w4['segments']] == ['PREFIX', 'STEM'] and w4['derived']['prefix_tags'] == ['l:P+'])
check(4, 'features of 67:15:3 (aspect, person, gender, number)',
      (seg['aspect'], seg['person'], seg['gender'], seg['number']) == ('PERF', '3', 'M', 'S'))
vf = v['word']['derived']['verb_forms'][0]
check(5, 'why this form: verb form + whether explicit or inferred', (vf['value'], vf['basis']) == ('I', 'inferred')
      and any(f['basis'] == 'explicit' for w in words.values() if w['segments'] for f in w['derived']['verb_forms']))
hits = q.find(root='jEl')
check(6, 'other occurrences of the same root / lemma', '67:15:3' in hits and len(hits) > 100
      and len(q.find(lemma='jaEala')) > 50)
s = sents['10846']
pp = next(c for c in s['constituents'] if c['tag'] == 'PP')
check(7, 'words that belong together (PP constituent around 67:15:4)', pp['words'] == ['67:15:4'])
obj = v  # case + relation + head: why 67:15:5 is accusative
w5 = q.word_view('67:15:5')
case = next(sg['case'] for sg in w5['word']['segments'] if 'case' in sg)
rel = next(x for x in w5['syntax'] if x['rel'] == 'Obj')
check(8, 'grammatical relation behind the case of 67:15:5 (ACC, object of the verb 67:15:3)',
      case == 'ACC' and rel['head_word'] == '67:15:3' and rel['head_pos'] == 'V')
check(9, 'sentence boundary of 10846', (s['span']['first_word'], s['span']['last_word']) == ('67:15:1', '67:15:6'))
rels = {n['word']: n['rel'] for n in s['nodes'] if n['word'] and n['rel'] != 'NonRel'}
check(10, 'grammatical elements (object, subject node, link) of 10846',
      rels['67:15:5'] == 'Obj' and any(n['rel'] == 'Subj' for n in s['nodes']) and rels['67:15:4'] in ('link', 'gen'))
n5 = s['nodes'][5]
check(11, 'syntactic connection: pronoun (token 5) is genitive and depends on the preposition (token 4)',
      n5['rel'] == 'gen' and s['nodes'][n5['head']]['pos'] == 'P')
imp = [n for n in s['nodes'] if n['implicit']]
check(12, 'implicit element (unspoken subject) kept and anchored', len(imp) == 1 and imp[0]['anchor']['after_word'] == '67:15:3'
      and '67:15:3' in s['words'] and all(n['word'] is None for n in imp))
check(13, 'particles and relations visible for the sentence (link, root, Pred, sub, ...)',
      {'link', 'root', 'Pred', 'sub'} <= {n['rel'] for n in s['nodes']})
cross = [x for x in sents.values() if x['span']['crosses_ayah']]
check(13, 'sentences keep original boundaries across ayahs (836 cross an ayah boundary)', len(cross) == 836)
top = {}
for w in words.values():
    for sg in w['segments']:
        if 'lemma' in sg:
            top[sg['lemma']['bw']] = top.get(sg['lemma']['bw'], 0) + 1
check(14, 'most frequent lemmas computable', len(top) > 4000 and max(top.values()) > 1000)
ex = q.find(function='Poss')
check(15, 'other Quranic examples of a construction (genitive/possessor relation)',
      len(ex) > 1000 and all(words[k]['derived']['projections']['function_all'] for k in ex[:10]))

print()
print('%d of 16 checks failed' % len(fails) if fails else 'all question checks passed')
sys.exit(1 if fails else 0)
