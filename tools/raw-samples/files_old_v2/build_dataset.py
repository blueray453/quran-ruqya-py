#!/usr/bin/env python3
"""Build the Al-Mulk phrase dataset (JSON only).
Inputs : annotations/mulk_spec.json (hand-edited clause/phrase boundaries + English)
         sources/*  (QPC words, Digital Khatt, Sahih Intl, Quranic Arabic Corpus morphology)
         optional: sources/WBS.csv (QSU word-boundary states) -> see import_qsu.py
Output : data/mulk.json  (ayah > clause > phrase > word, morphology inline)
"""
import json,re,csv,os,collections as C
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P=lambda *a:os.path.join(ROOT,*a)
words=json.load(open(P('sources','mulk-qpc-words.json')))
dk=json.load(open(P('sources','mulk-digital-khatt.json')))
en=json.load(open(P('sources','mulk-en-sahih.json')))
spec=json.load(open(P('annotations','mulk_spec.json')))['ayahs']

# ---------- helpers ----------
DIAC=re.compile('[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]')
WAQF=re.compile('[\u06D6-\u06DC]')
def norm_ar(t): return DIAC.sub('',t).replace('ٱ','ا').replace('ى','ي')
ALIAS={'and it is':'and he is'}          # referent-neutral key for وَهُوَ (67:4 refers to the vision)
def tkey(t):
    k=re.sub(r"[“”‘’\"'.,;:!?]","",t).lower().strip()
    k=re.sub(r'\s+',' ',k)
    return ALIAS.get(k,k)

# ---------- morphology (Quranic Arabic Corpus, via mustafa0x/quran-morphology) ----------
NOMINAL=['PRON','REL','DEM','PN','LOC','T']            # only meaningful on pos=N heads
PARTICLE=['NEG','COND','INTG','CERT','RES','ATT','CONJ','REM','CIRC','SUB','ACC','VOC','EXP','EMPH','CAUS','ANS','FUT','INL','PREV','PRP','COM','RSLT','IMPN','AMD','AVR','EXH','EXL','EQ','INC','RET','SUP','SUR','PRO']  # only on pos=P heads
def parse_morph():
    segs=C.defaultdict(list)
    for line in open(P('sources','mulk-quran-morphology.txt'),encoding='utf-8'):
        loc,form,pos,feat=line.rstrip('\n').split('\t'); s,a,w,i=loc.split(':')
        segs[f"{s}:{a}:{w}"].append((form,pos,feat.split('|')))
    out={}
    for k,ss in segs.items():
        pre=[x for x in ss if 'PREF' in x[2]]; suf=[x for x in ss if 'SUFF' in x[2]]
        head=[x for x in ss if 'PREF' not in x[2] and 'SUFF' not in x[2]]
        h=head[0] if head else ss[0]; hf=h[2]
        root=next((f[5:] for f in hf if f.startswith('ROOT:')),''); lem=next((f[4:] for f in hf if f.startswith('LEM:')),'')
        spec_tag=next((t for t in (NOMINAL if h[1]=='N' else PARTICLE if h[1]=='P' else []) if t in hf),None) or ('ADJ' if 'ADJ' in hf else 'PCPL' if 'ACT_PCPL' in hf or 'PASS_PCPL' in hf else None)
        ptags=[next((f for f in x[2] if f not in('PREF',) and not f.startswith('LEM:')),'') for x in pre]
        out[k]=dict(root=root,lemma=lem,pos=h[1],cat=spec_tag or h[1],
                    prefix_tags='+'.join(ptags),definite='DET' in ptags,
                    suffix_pron=any('PRON' in x[2] for x in suf),
                    features='|'.join(f for f in hf if not f.startswith(('ROOT:','LEM:'))),
                    qac_segments=[x[0] for x in ss])
    return out
morph=parse_morph()

# ---------- build ----------
W_rows,PH_rows,CL_rows,ayahs=[],[],[],[]
for a in range(1,31):
    vk=f"67:{a}"; aw={int(v['word']):v for v in words.values() if v['ayah']==str(a)}
    n=max(aw)-1; marker=aw[n+1]['text']                       # last "word" is the ayah-end number
    clauses_spec=spec[str(a)]
    flat=[i for cl in clauses_spec for s,e,_ in cl for i in range(s,e+1)]
    assert flat==list(range(1,n+1)),(a,flat,n)                # phrases tile clauses; clauses tile ayah
    assert all(f"67:{a}:{i}" in morph for i in range(1,n+1)),f'morphology misaligned in {vk}'
    assert f"67:{a}:{n+1}" not in morph,f'morphology has extra word in {vk}'
    ay_clauses=[]; prev_cat=None; WB={}
    for o,cl in enumerate(clauses_spec,1):
        cid=f"{vk}:c{o}"; ph_objs=[]
        for j,(s,e,t) in enumerate(cl,1):
            pid=f"{cid}:p{j}"; wl=list(range(s,e+1))
            for i in wl:
                w=aw[i]; m=morph[f"67:{a}:{i}"]
                bb='A' if i==1 else 'C' if (j==1 and i==s) else 'P' if i==s else 'I'
                W_rows.append(dict(word_id=f"{vk}:{i}",ayah=a,word=i,text=w['text'],text_norm=norm_ar(DIAC.sub('',w['text'])) ,
                    waqf_mark=(WAQF.search(w['text']) or [None])[0] if WAQF.search(w['text']) else '',
                    root=m['root'],lemma=m['lemma'],pos=m['pos'],cat=m['cat'],prefix_tags=m['prefix_tags'],definite=int(m['definite']),
                    suffix_pron=int(m['suffix_pron']),features=m['features'],
                    clause_id=cid,clause_order=o,phrase_id=pid,phrase_order=j,boundary_before=bb,
                    is_clause_start=int(bb in 'AC'),is_phrase_start=int(bb in 'ACP'),
                    prev_word_waqf=int(bool(i>1 and WAQF.search(aw[i-1]['text']))),
                    qsu_unit_begins='',qsu_unit_ends=''))
            txt=' '.join(aw[i]['text'] for i in wl)
            pat=' '.join((morph[f"67:{a}:{i}"]['prefix_tags']+'+' if morph[f"67:{a}:{i}"]['prefix_tags'].replace('DET','').strip('+') else '')+morph[f"67:{a}:{i}"]['cat'] for i in wl)
            ph=dict(phrase_id=pid,clause_id=cid,ayah=a,order=j,word_start=s,word_end=e,n_words=len(wl),
                    text=txt,text_norm=norm_ar(DIAC.sub('',txt)),translation=t,translation_key=tkey(t),
                    pattern=pat,first_cat=morph[f"67:{a}:{s}"]['cat'],last_cat=morph[f"67:{a}:{e}"]['cat'],
                    has_waqf=int(bool(WAQF.search(txt))))
            ph_objs.append(ph); PH_rows.append(ph)
        cs,ce=cl[0][0],cl[-1][1]; ctxt=' '.join(p['text'] for p in ph_objs)
        first=morph[f"67:{a}:{cs}"]; 
        c=dict(clause_id=cid,ayah=a,order=o,word_start=cs,word_end=ce,n_words=ce-cs+1,n_phrases=len(ph_objs),
               text=ctxt,text_norm=norm_ar(DIAC.sub('',ctxt)),translation=' '.join(p['translation'] for p in ph_objs),
               translation_key=' '.join(p['translation_key'] for p in ph_objs),
               pattern=' | '.join(p['pattern'] for p in ph_objs),first_cat=first['cat'],first_prefix=first['prefix_tags'],
               ends_with_waqf=int(bool(WAQF.search(aw[ce]['text']))),is_ayah_final=int(o==len(clauses_spec)))
        CL_rows.append(c); ay_clauses.append((c,ph_objs))
    WB={r['word_id']:r for r in W_rows if r['ayah']==a}
    DROP={'clause_id','phrase_id','clause_order','phrase_order'}
    def wobj(i):
        d={k:v for k,v in WB[f"{vk}:{i}"].items() if k not in DROP}
        d['qsu_unit_begins']=None; d['qsu_unit_ends']=None
        d['waqf_mark']=d['waqf_mark'] or None
        return d
    ayahs.append(dict(verse_key=vk,surah=67,ayah=a,n_words=n,end_marker=marker,text_digital_khatt=dk[vk]['text'],
        translation_sahih=en[vk]['t'],translation_phrased=' '.join(c['translation'] for c,_ in ay_clauses),
        clauses=[dict(c,phrases=[dict(p,words=[wobj(i) for i in range(p['word_start'],p['word_end']+1)]) for p in ps]) for c,ps in ay_clauses]))

json.dump(dict(surah=67,name='Al-Mulk',sources=dict(words='QUL qpc-hafs-word-by-word',ayah_text='QUL digital-khatt-v2',translation='QUL en-sahih-international-simple',morphology='Quranic Arabic Corpus via github.com/mustafa0x/quran-morphology'),ayahs=ayahs),open(P('data','mulk.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(len(W_rows),'words',len(PH_rows),'phrases',len(CL_rows),'clauses')
