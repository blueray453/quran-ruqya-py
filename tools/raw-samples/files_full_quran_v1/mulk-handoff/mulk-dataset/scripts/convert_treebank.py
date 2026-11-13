#!/usr/bin/env python3
"""One-off conversion: Quranic Treebank (NoorBayan/Quranic, corpus/Quranic.rar -> Quranic.csv, UTF-16 TSV)
-> compact word-level JSON, one file per surah, keyed by word location (same keys as QUL / QPC).

Kept per word: sentence id, segments [text, segment type, pos tag, feature string], and the constituent
spans (PP/VS/NS/CS/SC/S) that START at this word, with their last word.
Dropped: transliterations, colours, Arabic POS duplicates, lemma/root (QUL supplies those), dependency columns
(deferred; the raw file is kept so they can be added later).
Keys are QPC keys. The treebank writes بَعْدَ مَا ("after what") as ONE word in 2:181, 8:6 and 13:37 where QPC has two
words, so every later treebank word in those ayahs is numbered one lower than in QPC. ALIGN below splits the merged word
into its two stem segments (QPC words m and m+1) and shifts the later words, so output keys always equal QPC keys.
Usage: python3 scripts/convert_treebank.py Quranic.csv OUTDIR [--qpc qpc-hafs-word-by-word.json]
  --qpc  also checks the per-ayah word count against QPC (markers excluded) for every ayah present in that file.
"""
import sys,os,re,json,collections as C,pandas as pd
src,out=sys.argv[1],sys.argv[2]; os.makedirs(out,exist_ok=True)
qpc_path=sys.argv[sys.argv.index('--qpc')+1] if '--qpc' in sys.argv else None
ALIGN={'2:181':3,'8:6':4,'13:37':8}      # ayah -> treebank index of the merged word (= QPC words m and m+1)
EXPECTED_TOTAL=77432                      # QPC words, end-of-ayah markers excluded
d=pd.read_csv(src,encoding='utf-16',sep='\t',low_memory=False,
    usecols=['location','chapter_id','sentence_id','uthmani_token','segment','pos','features','constituents_loc','constituent_label'])
d['idx']=d.groupby('sentence_id').cumcount()
m=d.location.astype(str).str.extract(r'\((\d+):(\d+):(\d+):(\d+)\)')
d['wkey']=(m[0]+':'+m[1]+':'+m[2])
stats=C.Counter(); words=C.defaultdict(dict)
for sid,g in d.groupby('sentence_id',sort=False):
    g=g.reset_index(drop=True)
    for _,r in g.iterrows():
        if isinstance(r.wkey,str):
            w=words[int(r.wkey.split(':')[0])].setdefault(r.wkey,{'s':int(sid),'seg':[],'c':[]})
            w['seg'].append([r.uthmani_token,r.segment,r.pos,r.features])
        else: stats['inserted_tokens_skipped']+=1
    for i,r in g[g.constituents_loc!='_'].iterrows():
        for a,b in re.findall(r'\[(\d+)-(\d+)\]',str(r.constituents_loc)):
            ks=[k for k in g.loc[int(a):int(b),'wkey'] if isinstance(k,str)]
            if not ks: stats['spans_without_real_words']+=1; continue
            key=lambda k:[int(x) for x in k.split(':')]
            first,last=min(ks,key=key),max(ks,key=key)
            words[int(first.split(':')[0])][first]['c'].append([r.constituent_label,last]); stats['spans_kept']+=1
def realign(words):
    def rend(k):                          # remap a span-end key if it lies in an ALIGN ayah
        ay,i=k.rsplit(':',1); m=ALIGN.get(ay); i=int(i)
        return k if m is None or i<m else f'{ay}:{m+1}' if i==m else f'{ay}:{i+1}'
    for ws in words.values():
        for w in ws.values(): w['c']=[[lab,rend(e)] for lab,e in w['c']]
    for ay,m in ALIGN.items():
        ws=words[int(ay.split(':')[0])]
        for i in sorted((int(k.rsplit(':',1)[1]) for k in ws if k.rsplit(':',1)[0]==ay),reverse=True):
            k=f'{ay}:{i}'; w=ws[k]
            if i>m: ws[f'{ay}:{i+1}']=ws.pop(k)
            elif i==m:
                cut=next(j for j,x in enumerate(w['seg']) if j>0 and x[1]=='STEM')
                ws[k]=dict(w,seg=w['seg'][:cut],aligned='split'); ws[f'{ay}:{m+1}']={'s':w['s'],'seg':w['seg'][cut:],'c':[],'aligned':'split'}
realign(words)
tot=0
for ch,ws in words.items():
    p=os.path.join(out,f'surah-{ch:03d}.json'); json.dump(ws,open(p,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    tot+=len(ws); 
assert tot==EXPECTED_TOTAL,(tot,EXPECTED_TOTAL)
if qpc_path:
    q=json.load(open(qpc_path,encoding='utf-8')); n=C.Counter(k.rsplit(':',1)[0] for k in q)
    mine=C.Counter(k.rsplit(':',1)[0] for ws in words.values() for k in ws)
    bad=[(a,n[a]-1,mine[a]) for a in n if n[a]-1!=mine[a]]; assert not bad,('word-count mismatch vs QPC',bad[:10]); print('QPC per-ayah count check OK for',len(n),'ayahs')
print('surahs',len(words),'| words',tot,'| bytes total',sum(os.path.getsize(os.path.join(out,f)) for f in os.listdir(out)),dict(stats))
