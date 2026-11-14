#!/usr/bin/env python3
"""Merge QSU (Quran Semantic Units, Mendeley Data v7hyhk7krd, CC BY-NC 3.0) into data/mulk.json
(word-level qsu_unit_begins / qsu_unit_ends) and compare QSU unit starts with our clause starts.

Usage: python3 scripts/import_qsu.py /path/to/WBS.csv [--dry-run]
WBS.csv: one row per word with its location, Arabic text, unit_begins and unit_ends flags.
Location may be one 'surah:ayah:word' column or separate surah/ayah/word columns
(column handling is unverified against the real file).
"""
import sys,os,json,pandas as pd
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
q=pd.read_csv(sys.argv[1],encoding='utf-8-sig'); q.columns=[c.strip().lower() for c in q.columns]
loc=next((c for c in q.columns if 'loc' in c),None)
if loc: parts=q[loc].astype(str).str.extract(r'(\d+)\D+(\d+)\D+(\d+)').astype(int)
else:   parts=q[[next(c for c in q.columns if c.startswith(k)) for k in ('sur','ay','wo')]].astype(int)
q['word_id']=parts[0].astype(str)+':'+parts[1].astype(str)+':'+parts[2].astype(str)
flag=lambda s:s.astype(str).str.strip().str.lower().isin(['1','true','yes','y','t']).astype(int)
qs={r.word_id:(int(a),int(b)) for r,a,b in zip(q.itertuples(),flag(q['unit_begins']),flag(q['unit_ends'])) if r.word_id.startswith('67:')}
p=f'{R}/data/mulk.json'; J=json.load(open(p,encoding='utf-8'))
n=hit=ours=theirs=0
for a in J['ayahs']:
    for c in a['clauses']:
        for ph in c['phrases']:
            for w in ph['words']:
                if w['word_id'] in qs:
                    w['qsu_unit_begins'],w['qsu_unit_ends']=qs[w['word_id']]; n+=1
                    mine=w['is_clause_start']; hit+=mine and w['qsu_unit_begins']; ours+=mine; theirs+=w['qsu_unit_begins']
print(f'{n} Al-Mulk words matched | our clause starts {ours} | QSU unit starts {theirs} | both {hit}')
print(f'recall of QSU boundaries by our clauses: {hit}/{theirs} | precision: {hit}/{ours}')
if '--dry-run' not in sys.argv: json.dump(J,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=1); print('mulk.json updated')
