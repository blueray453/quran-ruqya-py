#!/usr/bin/env python3
"""Merge QSU units (Mendeley Data v7hyhk7krd, CC BY-NC 3.0) into data/mulk.json and compare with our clauses.

QSU.csv columns: index,start_location,end_location,text_diacritics,text_clean  (locations are surah:ayah:word).
Units are hierarchical/overlapping: the same text appears at several granularities, and some span ayahs.
Usage: python3 scripts/import_qsu.py [QSU.csv or slice]   (default: sources/qsu_mulk_slice.csv; only surah 67 rows are used)
Word fields written: qsu_unit_begins/ends (any level), qsu_leaf_begins/ends (finest level only).
"""
import sys,os,json,pandas as pd
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src=next((a for a in sys.argv[1:] if not a.startswith('--')),f'{R}/sources/qsu_mulk_slice.csv')
q=pd.read_csv(src,encoding='utf-8-sig',usecols=['index','start_location','end_location'])
loc=lambda s:tuple(int(x) for x in s.split(':'))
U=[(i,loc(a),loc(b)) for i,a,b in zip(q['index'],q.start_location,q.end_location)]
U=[u for u in U if u[1][0]==67 or u[2][0]==67]
pos=lambda t:(t[1],t[2])                                   # (ayah, word) within surah 67
S=[(i,pos(a),pos(b)) for i,a,b in U if a[0]==67 and b[0]==67]
leaf=[u for u in S if not any(v is not u and v[1]>=u[1] and v[2]<=u[2] for v in S)]
begins={u[1] for u in S}; ends={u[2] for u in S}; lb={u[1] for u in leaf}; le={u[2] for u in leaf}
p=f'{R}/data/mulk.json'; J=json.load(open(p,encoding='utf-8')); rows=[]
for a in J['ayahs']:
    for c in a['clauses']:
        for ph in c['phrases']:
            for w in ph['words']:
                k=(w['ayah'],w['word'])
                w['qsu_unit_begins']=int(k in begins); w['qsu_unit_ends']=int(k in ends)
                w['qsu_leaf_begins']=int(k in lb); w['qsu_leaf_ends']=int(k in le); rows.append(w)
json.dump(J,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
df=pd.DataFrame(rows); ay1=df.word==1; inner=~ay1
print(f'{len(S)} QSU units in surah 67 ({len(leaf)} finest-level); our clauses: {int(df.is_clause_start.sum())}')
for name,col in (('any-level starts','qsu_unit_begins'),('finest-level starts','qsu_leaf_begins')):
    both=int(((df.is_clause_start==1)&(df[col]==1)).sum()); q_n=int(df[col].sum()); o_n=int(df.is_clause_start.sum())
    print(f'{name}: QSU {q_n} | ours {o_n} | both {both} | our clauses recover {both}/{q_n} QSU boundaries')
print('\nInside-ayah boundaries (word>1):')
q_in=set(df[inner&(df.qsu_unit_begins==1)].word_id); o_in=set(df[inner&(df.is_clause_start==1)].word_id)
print(f'  QSU {len(q_in)} | ours {len(o_in)} | both {len(q_in&o_in)} | QSU-only {sorted(q_in-o_in)}')
print('\nAyah starts QSU does NOT treat as a boundary (merged with previous ayah):',sorted(set(df[ay1&(df.qsu_unit_begins==0)].ayah)))
print('Our clause boundaries QSU lacks (sample categories):'); m=df[inner&(df.is_clause_start==1)&(df.qsu_unit_begins==0)]
print('  count',len(m),'| by prev-word waqf:',m.prev_word_waqf.value_counts().to_dict(),'| by prefix:',m.prefix_tags.replace('','(none)').value_counts().head(6).to_dict())
