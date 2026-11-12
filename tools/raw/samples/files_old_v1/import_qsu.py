#!/usr/bin/env python3
"""Merge QSU (Quran Semantic Units, Mendeley Data v7hyhk7krd, CC BY-NC 3.0) into data/words.csv
and compare its unit boundaries with our clause boundaries.

Usage: python3 scripts/import_qsu.py /path/to/WBS.csv
WBS.csv has one row per word with its location, Arabic text and two flags
(unit_begins, unit_ends). The location may be a single 'surah:ayah:word' column or
separate surah/ayah/word columns; this script accepts either (unverified against the real file).
"""
import sys,os,pandas as pd
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
q=pd.read_csv(sys.argv[1],encoding='utf-8-sig'); q.columns=[c.strip().lower() for c in q.columns]
loc=next((c for c in q.columns if 'loc' in c),None)
if loc: parts=q[loc].astype(str).str.extract(r'(\d+)\D+(\d+)\D+(\d+)').astype(int)
else:   parts=q[[next(c for c in q.columns if c.startswith(k)) for k in ('sur','ay','wo')]].astype(int)
q['word_id']=parts[0].astype(str)+':'+parts[1].astype(str)+':'+parts[2].astype(str)
flag=lambda s:s.astype(str).str.strip().str.lower().isin(['1','true','yes','y','t'])
q['qsu_unit_begins']=flag(q['unit_begins']).astype(int); q['qsu_unit_ends']=flag(q['unit_ends']).astype(int)
q=q[q.word_id.str.startswith('67:')][['word_id','qsu_unit_begins','qsu_unit_ends']]
p=f'{R}/data/words.csv'; w=pd.read_csv(p,encoding='utf-8-sig').fillna('').drop(columns=['qsu_unit_begins','qsu_unit_ends'])
w=w.merge(q,on='word_id',how='left'); w.to_csv(p,index=False,encoding='utf-8-sig')
m=w.dropna(subset=['qsu_unit_begins']); print(len(m),'of',len(w),'Al-Mulk words matched')
t=pd.crosstab(m.is_clause_start,m.qsu_unit_begins,rownames=['our clause start'],colnames=['QSU unit begins']); print(t)
both=((m.is_clause_start==1)&(m.qsu_unit_begins==1)).sum()
print(f'recall of QSU boundaries by our clauses: {both}/{int(m.qsu_unit_begins.sum())} | precision: {both}/{int(m.is_clause_start.sum())}')
