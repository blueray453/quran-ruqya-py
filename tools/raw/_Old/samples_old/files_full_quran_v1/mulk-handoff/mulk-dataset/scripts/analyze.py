#!/usr/bin/env python3
"""Frequency + rule mining on data/mulk.json (flattened with pandas in memory)."""
import pandas as pd,os,sys,json
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J=json.load(open(f'{R}/data/mulk.json',encoding='utf-8'))
wr,pr,cr=[],[],[]
for a in J['ayahs']:
    for c in a['clauses']:
        cr.append({k:v for k,v in c.items() if k!='phrases'})
        for p in c['phrases']:
            pr.append({k:v for k,v in p.items() if k!='words'})
            for x in p['words']: wr.append(dict(x,clause_id=c['clause_id'],phrase_id=p['phrase_id']))
w,ph,cl=(pd.DataFrame(r).fillna('') for r in (wr,pr,cr))
for df in (ph,cl):
    df['translation_key']=df.translation_keys.map(lambda d:d['en']); df['translation_key_bn']=df.translation_keys.map(lambda d:d['bn'])
pd.set_option('display.width',200,'display.max_colwidth',60,'display.max_rows',200)

print('=== 1. FREQUENCY')
for name,df in (('clauses',cl),('phrases',ph)):
    g=df.groupby('text_norm').agg(n=('text','size'),example=('text','first'),translations=('translation_key',lambda s:' / '.join(sorted(set(s))))).query('n>1').sort_values('n',ascending=False)
    print(f'\n{name}: {len(df)} total, {df.text_norm.nunique()} distinct by Arabic, {df.translation_key.nunique()} distinct by translation')
    print(g.to_string())
print('\nphrase translation_key frequency (top):'); print(ph.translation_key.value_counts().head(8).to_string())
print('\nphrase patterns (top):'); print(ph.pattern.value_counts().head(10).to_string())
print('\nclause patterns repeated:'); print(cl.pattern.value_counts().loc[lambda s:s>1].to_string())
# consistency: same Arabic -> same translation_key ?
inc=ph.groupby('text_norm').translation_key.nunique().loc[lambda s:s>1]
print('\nArabic phrases with >1 English key:',len(inc),list(inc.index))
inc_bn=ph.groupby('text_norm').translation_key_bn.nunique().loc[lambda s:s>1]
print('Arabic phrases with >1 Bangla key:',len(inc_bn),list(inc_bn.index))

print('\n=== 2. RULE MINING (boundary before each non-initial word)')
b=w[w.word>1].copy(); b['k']=b.boundary_before
b['pre1']=b.prefix_tags.str.split('+').str[0]
prev=w.set_index('word_id'); b['prev_cat']=[prev.loc[f"67:{a}:{n-1}",'cat'] for a,n in zip(b.ayah,b.word)]
b['prev_suffix_pron']=[int(prev.loc[f"67:{a}:{n-1}",'suffix_pron']) for a,n in zip(b.ayah,b.word)]
print(b.k.value_counts().to_dict())
def mine(col,min_n=4,purity=.9):
    t=pd.crosstab(b[col],b.k); t['n']=t.sum(axis=1)
    for kk in 'CPI':
        if kk not in t: t[kk]=0
    rows=[]
    for v,r in t.iterrows():
        if v=='' or r.n<min_n: continue
        best=max('CPI',key=lambda x:r[x])
        rows.append((col,v,int(r.n),best,r[best]/r.n,int(r.C),int(r.P),int(r.I)))
    return pd.DataFrame(rows,columns=['feature','value','n','predicts','accuracy','C','P','I'])
tab=pd.concat([mine(c) for c in ('cat','pre1','prev_cat','prev_word_waqf')])
tab['accuracy']=(tab.accuracy*100).round(1)
print('\nAll features with n>=4 (C=clause start, P=phrase start, I=inside phrase):'); print(tab.sort_values(['accuracy','n'],ascending=False).to_string(index=False))
# explicit rules
def rule(name,mask,target):
    s=b[mask]; hit=s.k.isin(list(target)).sum(); print(f'{name:70s} {hit}/{len(s)} = {100*hit/max(len(s),1):.1f}%')
print('\nExplicit rules')
rule('C1 previous word has waqf mark -> clause start',b.prev_word_waqf==1,'C')
rule('C2a NEG or COND particle -> clause start',b.cat.isin(['NEG','COND']),'C')
rule('C2b INTG particle (هل/ألم/أمن) -> clause start',b.cat=='INTG','C')
rule('C2c CERT/SUB/ANS/RET/SUR/RES particle -> clause start',b.cat.isin(['CERT','SUB','ANS','RET','SUR','RES']),'C')
rule('C3 prefix is REM (resumption و/ف) -> clause start',b.pre1=='REM','C')
rule('C4 prefix is CIRC (circumstantial و) -> inside clause (not C)',b.pre1=='CIRC','PI')
rule('C5 prefix is CONJ -> clause start',b.pre1=='CONJ','C')
rule('C6 prefix is CONJ and head is noun-like -> phrase level (not C)',(b.pre1=='CONJ')&b.cat.isin(['N','ADJ','PN','PCPL','REL']),'PI')
rule('C7 definite word never starts a clause',b.definite==1,'PI')
rule('P1  word after a bare preposition (no pronoun suffix) stays in phrase',(b.prev_cat=='P')&(b.prev_suffix_pron==0),'I')
rule('P1b preposition+pronoun word (فيها, عليهم) ends its phrase/clause',(b.prev_cat=='P')&(b.prev_suffix_pron==1),'PC')
rule('P2  relative pronoun after a non-verb joins the preceding word',(b.cat=='REL')&(b.prev_cat!='V'),'I')
rule('P2b relative pronoun after a verb starts a new phrase',(b.cat=='REL')&(b.prev_cat=='V'),'P')
rule('P3  verb after a pronoun-suffixed word begins a new phrase/clause',(b.cat=='V')&(b.prev_suffix_pron==1),'PC')
print('\nclause size 2-6 words:',cl.n_words.between(2,6).sum(),'/',len(cl),'| phrase size 1-3 words:',ph.n_words.le(3).sum(),'/',len(ph))
