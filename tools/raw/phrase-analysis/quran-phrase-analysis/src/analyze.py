"""Step 2: repeated words/phrases, stand-alone counts, coverage and memorization ranking.

Reads  results/indopak-nastaleeq-wbw-normalized.json   (produced by normalize.py)
Writes into results/:
  quran-phrases-annotation.json          annotation of every repeated unit with exact word locations
  quran-phrases.csv                      same data for spreadsheets
  quran-coverage-by-surah.csv            coverage per surah
  quran-greedy-order-words-and-phrases.csv   memorization order (words + phrases)
  quran-greedy-order-phrases-only.csv        memorization order (phrases of 2+ words only)

Definitions
  unit        a run of n >= 1 consecutive words inside ONE verse (never across a verse boundary)
              that occurs at least twice in the whole Quran (normalized text)
  total       every occurrence of the unit (overlapping occurrences included)
  stand-alone occurrences that are NOT part of a longer repeated unit
  coverage    share of the 77,430 word positions that fall inside at least one unit
"""
import argparse, json, unicodedata, collections, csv, heapq
_ap = argparse.ArgumentParser(); _ap.add_argument('--results-dir', default='results')
OUT = _ap.parse_args().results_dir.rstrip('/') + '/'
normed=json.load(open(OUT+'indopak-nastaleeq-wbw-normalized.json'))
entries=sorted(normed.values(), key=lambda x:(x['surah'],x['ayah'],x['word']))
verses=[];cur=None
for e in entries:
    k=(e['surah'],e['ayah'])
    if k!=cur:
        verses.append({'key':f'{k[0]}:{k[1]}','s':k[0],'locs':[],'norm':[],'text':[]}); cur=k
    if e['normalized']:
        verses[-1]['locs'].append(f"{e['surah']}:{e['ayah']}:{e['word']}"); verses[-1]['norm'].append(e['normalized']); verses[-1]['text'].append(e['text'])
assert len(verses)==6236
TOTAL=sum(len(v['norm']) for v in verses); print('words',TOTAL)
offs=[];o=0
for v in verses: offs.append(o); o+=len(v['norm'])

# repeated units: n=1 (single words) and n>=2 (phrases), all inside one verse
rep={}
n=1
while True:
    d=collections.defaultdict(list)
    for vi,v in enumerate(verses):
        ws=v['norm']
        for i in range(len(ws)-n+1): d[tuple(ws[i:i+n])].append((vi,i))
    r={g:p for g,p in d.items() if len(p)>=2}
    if not r: break
    rep[n]=r; n+=1
print('repeated single words',len(rep[1]),'repeated phrases',sum(len(r) for k,r in rep.items() if k>=2),'max len',max(rep))
rep_pos={n:{p for ps in r.values() for p in ps} for n,r in rep.items()}

PAUSE=set('\u0615\u06d6\u06d7\u06d8\u06d9\u06da\u06db'); ZW=' \u200b\u200c\u200d\u200e\u200f\ufeff\u2002\u2003\u00a0'
def clean_end(w):
    w=w.strip(ZW)
    while w and (w[-1] in PAUSE or w[-1] in ZW): w=w[:-1]
    return w
rows=[]
for n,r in rep.items():
    nxt=rep_pos.get(n+1,set())
    for g,ps in r.items():
        rows.append((g,n,ps,[(vi,i) not in nxt and (vi,i-1) not in nxt for vi,i in ps]))
rows.sort(key=lambda x:(-len(x[2]),-x[1],x[0]))
def vlist(ps,flags=None):
    seen=[];s=set()
    for j,(vi,i) in enumerate(ps):
        if flags is not None and not flags[j]: continue
        if vi not in s: s.add(vi); seen.append(verses[vi]['key'])
    return seen
ann=[];csvrows=[]
for idx,(g,n,ps,alone) in enumerate(rows,1):
    vi0,i0=ps[0]; vt=[x.strip(ZW) for x in verses[vi0]['text'][i0:i0+n]]; vt[-1]=clean_end(vt[-1])
    ph=' '.join(g); tot=len(ps); sa=sum(alone)
    rec={'id':f'U{idx:05d}','type':'word' if n==1 else 'phrase','phrase_normalized':ph,'phrase_nastaleeq':' '.join(vt),
         'word_count':n,'char_count':len(ph),'letter_count':len(ph.replace(' ','')),
         'total_count':tot,'stand_alone_count':sa,'inside_longer_count':tot-sa,
         'verses_total':vlist(ps),'verses_stand_alone':vlist(ps,alone),
         'occurrences':[{'start':verses[vi]['locs'][i],'end':verses[vi]['locs'][i+n-1],'stand_alone':a} for (vi,i),a in zip(ps,alone)]}
    ann.append(rec)
    csvrows.append([rec['id'],rec['type'],n,len(ph),rec['letter_count'],tot,sa,ph,rec['phrase_nastaleeq'],' | '.join(rec['verses_total']),' | '.join(rec['verses_stand_alone'])])
json.dump({'source_files':['indopak-nastaleeq-wbw.json','indopak-nastaleeq.json'],
 'notes':'Units are repeated single words (word_count 1) and repeated phrases (>=2 consecutive words), always inside one verse, occurring >=2 times in normalized text. Locations are surah:ayah:word from the wbw file. stand_alone = occurrence not part of a longer repeated unit. Words occurring once in the Quran are not included.',
 'units':ann},open(OUT+'quran-phrases-annotation.json','w'),ensure_ascii=False,separators=(',',':'))
with open(OUT+'quran-phrases.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['id','type','word_count','char_count_with_spaces','letter_count','total_count','stand_alone_count','phrase_normalized','phrase_nastaleeq','verses_total','verses_stand_alone']); w.writerows(csvrows)

# validation
for r in ann:
    assert r['total_count']==len(r['occurrences'])>=2 and r['stand_alone_count']+r['inside_longer_count']==r['total_count']
    for o in r['occurrences'][:3]:
        s,e=o['start'].rsplit(':',1),o['end'].rsplit(':',1); assert s[0]==e[0]
        assert ' '.join(normed[f'{s[0]}:{k}']['normalized'] for k in range(int(s[1]),int(e[1])+1))==r['phrase_normalized']
print('validation ok; units',len(ann),'words',sum(r['type']=='word' for r in ann),'phrases',sum(r['type']=='phrase' for r in ann))

# coverage
def cov_for(filt):
    c=bytearray(TOTAL)
    for r,(g,n,ps,al) in zip(ann,rows):
        if filt(r):
            for vi,i in ps:
                b=offs[vi]+i
                for k in range(n): c[b+k]=1
    return sum(c),c
allc,call=cov_for(lambda r:True); phc,cph=cov_for(lambda r:r['word_count']>=2)
print(f'words+phrases {allc} = {100*allc/TOTAL:.2f}% | phrases only {phc} = {100*phc/TOTAL:.2f}% | uncovered (once-only words) {TOTAL-allc}')
ps_tot=collections.Counter();pa=collections.Counter();pp=collections.Counter();va=[]
for vi,v in enumerate(verses):
    L=len(v['norm']); a=sum(call[offs[vi]:offs[vi]+L]); p=sum(cph[offs[vi]:offs[vi]+L])
    ps_tot[v['s']]+=L;pa[v['s']]+=a;pp[v['s']]+=p; va.append(a/L)
with open(OUT+'quran-coverage-by-surah.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['surah','words','covered_words_and_phrases','coverage_pct_words_and_phrases','covered_phrases_only','coverage_pct_phrases_only'])
    for s in sorted(ps_tot): w.writerow([s,ps_tot[s],pa[s],round(100*pa[s]/ps_tot[s],2),pp[s],round(100*pp[s]/ps_tot[s],2)])
big=[s for s in ps_tot if ps_tot[s]>=20]; big.sort(key=lambda s:-pa[s]/ps_tot[s])
print('top surahs',[(s,round(100*pa[s]/ps_tot[s],1)) for s in big[:4]],'bottom',[(s,round(100*pa[s]/ps_tot[s],1)) for s in big[-4:]])
print('verses 100% covered',sum(x==1 for x in va),'>=90%',sum(x>=.9 for x in va),'>=75%',sum(x>=.75 for x in va),'>=50%',sum(x>=.5 for x in va))

# greedy ranking
def greedy(filt,fname):
    idxs=[j for j,r in enumerate(ann) if filt(r)]
    cand={j:(ann[j]['word_count'],sorted({offs[vi]+i+k for vi,i in rows[j][2] for k in range(ann[j]['word_count'])})) for j in idxs}
    cov=bytearray(TOTAL)
    gain=lambda j:sum(1 for p in cand[j][1] if not cov[p])
    heap=[(-gain(j)/cand[j][0],j) for j in idxs]; heapq.heapify(heap)
    sel=[];cum=0;cost=0
    while heap:
        _,j=heapq.heappop(heap); gn=gain(j)
        if gn==0: continue
        eff=gn/cand[j][0]
        if heap and eff<-heap[0][0]-1e-12: heapq.heappush(heap,(-eff,j)); continue
        for p in cand[j][1]: cov[p]=1
        cum+=gn;cost+=cand[j][0];sel.append((j,gn,cum,cost))
    with open(OUT+fname,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['rank','id','type','text_nastaleeq','words_in_unit','total_count','new_words_covered','cumulative_words_covered','cumulative_pct_of_quran','cumulative_words_to_learn'])
        for rk,(j,gn,cm,cs) in enumerate(sel,1):
            r=ann[j]; w.writerow([rk,r['id'],r['type'],r['phrase_nastaleeq'],r['word_count'],r['total_count'],gn,cm,round(100*cm/TOTAL,2),cs])
    return sel
sel=greedy(lambda r:True,'quran-greedy-order-words-and-phrases.csv')
print('combined picks',len(sel),'| phrases among them',sum(ann[j]['type']=='phrase' for j,_,_,_ in sel),'| final',f'{100*sel[-1][2]/TOTAL:.2f}%')
for N in (10,50,100,250,500,1000,2000,3000,5000,len(sel)):
    j,gn,cm,cs=sel[min(N,len(sel))-1]; print(f' top {N:>5}: learn {cs:>6} words -> {100*cm/TOTAL:.2f}%')
print('first picks:',[(ann[j]['phrase_nastaleeq'],ann[j]['total_count']) for j,_,_,_ in sel[:8]])
print('first phrase picked at rank',next((k+1 for k,(j,_,_,_) in enumerate(sel) if ann[j]['type']=='phrase'),None))
greedy(lambda r:r['type']=='phrase','quran-greedy-order-phrases-only.csv')

