#!/usr/bin/env python3
"""One-off conversion: Quranic Treebank (NoorBayan/Quranic, corpus/Quranic.rar -> Quranic.csv, UTF-16 TSV)
-> compact word-level JSON, one file per surah, keyed by word location (same keys as QUL / QPC).

Kept per word: sentence id, segments [text, segment type, pos tag, feature string], and the constituent
spans (PP/VS/NS/CS/SC/S) that START at this word, with their last word.
Dropped: transliterations, colours, Arabic POS duplicates, lemma/root (QUL supplies those), dependency columns
(deferred; the raw file is kept so they can be added later).
Usage: python3 scripts/convert_treebank.py Quranic.csv OUTDIR
"""
import sys,os,re,json,collections as C,pandas as pd
src,out=sys.argv[1],sys.argv[2]; os.makedirs(out,exist_ok=True)
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
tot=0
for ch,ws in words.items():
    p=os.path.join(out,f'surah-{ch:03d}.json'); json.dump(ws,open(p,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    tot+=len(ws); 
print('surahs',len(words),'| words',tot,'| bytes total',sum(os.path.getsize(os.path.join(out,f)) for f in os.listdir(out)),dict(stats))
