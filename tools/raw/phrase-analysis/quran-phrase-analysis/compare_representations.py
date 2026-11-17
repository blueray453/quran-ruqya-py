import sqlite3, json, sys, collections, unicodedata, csv
sys.path.insert(0,'/home/claude/quran-phrase-analysis/src')
from normalize import normalize, MAP
U='/mnt/user-data/uploads/'
n=json.load(open('/mnt/user-data/outputs/indopak-nastaleeq-wbw-normalized.json'))
def q(db,sql):
    c=sqlite3.connect('file:'+U+db+'?mode=ro',uri=True); return c.execute(sql).fetchall()
stem_loc={l:(i,t) for l,i,t in q('word-stem.db','select w.word_location,s.id,s.text from stem_words w join stems s on s.id=w.stem_id')}
lem_loc ={l:(i,t) for l,i,t in q('word-lemma.db','select w.word_location,s.id,s.text from lemma_words w join lemmas s on s.id=w.lemma_id')}
rt_loc  ={l:(i,t) for l,i,t in q('word-root.db','select w.word_location,s.id,s.arabic_trilateral from root_words w join roots s on s.id=w.root_id')}
GLYPH={'18:19:34','73:20:8'}
PAUSE=set('\u0615\u06d6\u06d7\u06d8\u06d9\u06da\u06db'); ZW=' \u200b\u200c\u200d\u200e\u200f\ufeff\u2002\u2003\u00a0'
def exact(t):
    o=[]
    for ch in t:
        if ch in PAUSE or ch in ZW or ch=='\u0640' or 0xE000<=ord(ch)<=0xF8FF: continue
        o.append(MAP.get(ch,ch))
    return unicodedata.normalize('NFC',''.join(o))
entries=sorted(n.values(),key=lambda x:(x['surah'],x['ayah'],x['word']))
verses=collections.OrderedDict()
for e in entries:
    loc=f"{e['surah']}:{e['ayah']}:{e['word']}"
    verses.setdefault((e['surah'],e['ayah']),[])
    if e['normalized'] or loc in GLYPH:
        glyph=loc in GLYPH
        ex = exact(stem_loc[loc][1]) if glyph else exact(e['text'])
        nm = normalize(stem_loc[loc][1]) if glyph else e['normalized']
        verses[(e['surah'],e['ayah'])].append(dict(loc=loc,glyph=glyph,exact=ex,norm=nm,
            stem=stem_loc.get(loc),lemma=lem_loc.get(loc),root=rt_loc.get(loc)))
def seqs(fn,skip_glyph=False):
    return [[fn(t) for t in v if not(skip_glyph and t['glyph'])] for v in verses.values()]
def units(S):
    out={}; cov=[bytearray(len(s)) for s in S]; k=1
    while True:
        d=collections.defaultdict(list)
        for vi,s in enumerate(S):
            for i in range(len(s)-k+1): d[tuple(s[i:i+k])].append((vi,i))
        rep={g:p for g,p in d.items() if len(p)>=2}
        if not rep: break
        for g,p in rep.items():
            out[g]=len(p)
            for vi,i in p:
                for j in range(k): cov[vi][i+j]=1
        k+=1
    return out,cov
def summarize(name,S):
    N=sum(map(len,S)); cnt=collections.Counter(t for s in S for t in s)
    hap=sum(1 for v in cnt.values() if v==1)
    u,cov=units(S)
    ph=[g for g in u if len(g)>=2]
    phrase_cov=0
    # phrase-only coverage
    cphr=[bytearray(len(s)) for s in S]
    for g in ph: pass
    return N,cnt,hap,u,cov
rows=[]
def report(name,S,note=''):
    N=sum(map(len,S)); cnt=collections.Counter(t for s in S for t in s)
    hap_types=sum(1 for v in cnt.values() if v==1)
    u,cov=units(S)
    all_cov=sum(sum(c) for c in cov)
    # phrases only
    cp=[bytearray(len(s)) for s in S]
    for vi,s in enumerate(S):
        pass
    d_k=2
    while True:
        d=collections.defaultdict(list)
        for vi,s in enumerate(S):
            for i in range(len(s)-d_k+1): d[tuple(s[i:i+d_k])].append((vi,i))
        rep=[p for p in d.values() if len(p)>=2]
        if not rep: break
        for p in rep:
            for vi,i in p:
                for j in range(d_k): cp[vi][i+j]=1
        d_k+=1
    ph_cov=sum(sum(c) for c in cp)
    r=dict(representation=name,tokens=N,distinct_types=len(cnt),once_only_types=hap_types,
           pct_types_once=round(100*hap_types/len(cnt),1),
           coverage_words_and_phrases_pct=round(100*all_cov/N,2),
           coverage_phrases_only_pct=round(100*ph_cov/N,2),
           repeated_phrase_types=sum(1 for g in u if len(g)>=2),longest_phrase=d_k-1,note=note)
    rows.append(r); print(r); return u
# 1 baseline = exactly what we published (the 2 glyph words dropped)
u_base=report('normalized_surface (published, 2 glyph words dropped)',seqs(lambda t:t['norm'],skip_glyph=True))
u_fix =report('normalized_surface (2 words restored)',seqs(lambda t:t['norm']))
report('exact_surface_with_diacritics',seqs(lambda t:t['exact']))
report('stem (DB; surface fallback)',seqs(lambda t:('s',t['stem'][0]) if t['stem'] else ('x',t['norm'])))
report('lemma (DB; surface fallback)',seqs(lambda t:('l',t['lemma'][0]) if t['lemma'] else ('x',t['norm'])))
report('root (DB; surface fallback for rootless words)',seqs(lambda t:('r',t['root'][0]) if t['root'] else ('x',t['norm'])))
with open('/mnt/user-data/outputs/representation-comparison.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# effect of the 2 restored words on units
only_base=[(g,c) for g,c in u_base.items() if len(g)>=2 and u_fix.get(g,0)!=c]
print('\nunits whose count changes when the 2 missing words are restored:',len(only_base))
for g,c in only_base[:10]: print('  ',' '.join(g),'| before',c,'| after',u_fix.get(g,0))

print('\n===== AUDIT =====')
toks=[t for v in verses.values() for t in v]
by_norm=collections.defaultdict(collections.Counter)
for t in toks: by_norm[t['norm']][t['exact']]+=1
multi={k:c for k,c in by_norm.items() if len(c)>1}
mt=sum(sum(c.values()) for c in multi.values())
print(f'normalized types with >=2 exact (diacritized) forms: {len(multi)} of {len(by_norm)}; tokens inside them: {mt} ({100*mt/len(toks):.1f}%)')
print('top conflated by token count:')
for k,c in sorted(multi.items(),key=lambda x:-sum(x[1].values()))[:10]:
    print('  ',k,sum(c.values()),dict(c.most_common(4)))
# homographs by lemma: normalized types whose tokens map to >=2 distinct lemmas
lem_by_norm=collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
for t in toks:
    if t['lemma']: lem_by_norm[t['norm']][t['lemma'][0]][t['lemma'][1]]+=1
hom={k:v for k,v in lem_by_norm.items() if len(v)>1}
ht=sum(sum(sum(c.values()) for c in v.values()) for v in hom.values())
print(f'normalized types mapping to >=2 different lemmas: {len(hom)}; tokens inside them: {ht} ({100*ht/len(toks):.1f}%)')
for k,v in sorted(hom.items(),key=lambda x:-sum(sum(c.values()) for c in x[1].values()))[:8]:
    print('  ',k,{list(c)[0]:sum(c.values()) for c in v.values()})
# exact forms that differ only in trivial marks? compare after stripping all Mn marks except shadda/vowels
VOW=set('\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652\u0670')
def core(s): return ''.join(ch for ch in s if unicodedata.category(ch)!='Mn' or ch in VOW)
cm=collections.defaultdict(set)
for t in toks: cm[t['norm']].add(core(t['exact']))
triv=sum(1 for k,c in multi.items() if len(cm[k])<len(c))
print('conflated types whose exact forms collapse further when only vowels/shadda/sukun/dagger-alef are kept:',triv,'of',len(multi))

print('\n===== AYAH-LEVEL CONSISTENCY =====')
vkey={}
for (s,a),v in verses.items(): vkey[f'{s}:{a}']=v
def cmp(db,table,pick,label,fmt=lambda x:x):
    rows_=dict(q(db,f'select verse_key,text from {table}'))
    ok=bad=0;ex=[]
    for k,v in vkey.items():
        words=[pick(t) for t in v if pick(t)]
        mine=' '.join(fmt(w) for w in words)
        theirs=rows_.get(k,'')
        if mine.strip()==theirs.strip(): ok+=1
        else:
            bad+=1
            if len(ex)<2: ex.append((k,mine[:60],theirs[:60]))
    print(label,'match',ok,'mismatch',bad,ex)
cmp('ayah-lemma.db','lemmas',lambda t:t['lemma'][1] if t['lemma'] else None,'ayah-lemma vs word-lemma')
cmp('ayah-stem.db','stems',lambda t:t['stem'][1] if t['stem'] else None,'ayah-stem  vs word-stem ')
cmp('ayah-root.db','roots',lambda t:t['root'][1].replace(' ','') if t['root'] else None,'ayah-root  vs word-root ')

print('\n===== MISMATCH DETAIL =====')
def detail(db,table,pick,label,fmt=lambda x:x):
    rows_=dict(q(db,f'select verse_key,text from {table}'))
    same_len_diff=len_diff=missing=0; tok_ours=tok_theirs=0
    for k,v in vkey.items():
        mine=[fmt(pick(t)) for t in v if pick(t)]
        if k not in rows_: missing+=1; continue
        theirs=rows_[k].split()
        if mine==theirs: continue
        if len(mine)==len(theirs): same_len_diff+=1
        else: len_diff+=1
    print(label,'| verse absent from ayah db:',missing,'| same count but different items:',same_len_diff,'| different token count:',len_diff)
detail('ayah-lemma.db','lemmas',lambda t:t['lemma'][1] if t['lemma'] else None,'lemma')
detail('ayah-stem.db','stems',lambda t:t['stem'][1] if t['stem'] else None,'stem ')
detail('ayah-root.db','roots',lambda t:t['root'][1].replace(' ','') if t['root'] else None,'root ')
# does the word-level lemma DB separate 'man' (who) from 'min' (from)?
c=collections.Counter((t['exact'],t['lemma'][1] if t['lemma'] else None) for t in toks if t['norm']=='من')
print('exact form -> word-level lemma for normalized "من":',c.most_common(8))
# how many tokens get a root / lemma / stem
for nm,k in (('stem','stem'),('lemma','lemma'),('root','root')):
    h=sum(1 for t in toks if t[k]); print(nm,'labelled tokens',h,f'({100*h/len(toks):.1f}%)')
