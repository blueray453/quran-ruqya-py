#!/usr/bin/env python3
"""Shared helpers for annotation generation: sources, batching, prompts, validation. Standard library only."""
import json,re,os,hashlib,collections as C
LATIN=re.compile('[A-Za-z]'); BENGALI=re.compile('[\u0980-\u09FF]')
EN_OPEN,EN_CLOSE='“','”'            # English: outer “ ” (inner ‘ ’ are not tracked: ’ is also the apostrophe)
BN_OPEN,BN_CLOSE='‘“','’”'          # Bangla: outer ‘ ’, inner “ ”
END_EN=tuple('.?!;:,”’'); END_BN=tuple('।?!;:,’”')
MAX_PHRASE_WORDS=8

def txt(v): return v if isinstance(v,str) or v is None else v.get('text')

def load_sources(root):
    """root = folder laid out like your QUL tree."""
    L=lambda *p:json.load(open(os.path.join(root,*p),encoding='utf-8'))
    src=dict(qpc=L('quran-script','wbw','qpc-hafs-word-by-word.json'),
             sahih=L('english-translation','en-sahih-international-simple.json'),
             zak=L('bangla-translation','bn-dr-abu-bakr-muhammad-zakaria-simple.json'),
             en_wbw=L('english-translation','english-wbw-translation.json'),
             bn_wbw=L('bangla-translation','bangali-word-by-word-translation.json'))
    idx=C.defaultdict(lambda:C.defaultdict(list))
    for k in src['qpc']:
        s,a,w=(int(x) for x in k.split(':')); idx[s][a].append((w,txt(src['qpc'][k])))
    src['idx']={s:{a:sorted(ws)[:-1] for a,ws in d.items()} for s,d in idx.items()}   # last entry per ayah = end marker
    return src

def make_batches(ayah_words,max_words):
    """Consecutive ayahs of one surah, up to max_words words per batch; an ayah is never split."""
    out,cur,n=[],[],0
    for a in sorted(ayah_words):
        w=len(ayah_words[a])
        if cur and n+w>max_words: out.append(cur); cur,n=[],0
        cur.append(a); n+=w
    if cur: out.append(cur)
    return out

def system_prompt(conventions_path,glossary_path):
    s=open(conventions_path,encoding='utf-8').read()
    if os.path.exists(glossary_path):
        g=json.load(open(glossary_path,encoding='utf-8'))
        s+='\n\n## Terminology glossary (use these renderings consistently)\n'+'\n'.join(f"- {x['ar']} -> EN: {x['en']} | BN: {x['bn']}" for x in g)
    return s,hashlib.sha1(s.encode('utf-8')).hexdigest()[:10]

def joined(clauses,i): return ' '.join(p[i] for cl in clauses for p in cl)

def user_prompt(src,surah,ayahs,prev=None):
    L=[]
    if prev:
        L.append(f"PREVIOUS AYAH (context only, do not annotate) {prev['key']}\nEN: {prev['en']}\nBN: {prev['bn']}\n"
                 f"Quotes still open at its end: EN {prev['depth_en']}, BN {prev['depth_bn']}\n")
    L.append('ANNOTATE THESE AYAHS:\n')
    for a in ayahs:
        ws=src['idx'][surah][a]; vk=f'{surah}:{a}'
        L.append(f'### {vk} ({len(ws)} words)')
        for i,t in ws:
            L.append(f"{i} {t} | EN gloss: {src['en_wbw'].get(f'{vk}:{i}') or '-'} | BN gloss: {src['bn_wbw'].get(f'{vk}:{i}') or '-'}")
        L.append(f"Reference EN (Sahih International): {src['sahih'][vk]['t']}")
        L.append(f"Reference BN (Zakaria): {src['zak'][vk]['t']}\n")
    L.append('Return ONLY one JSON object with one key per ayah above (e.g. "%d:%d"), as specified.'%(surah,ayahs[0]))
    return '\n'.join(L)

def parse_response(s):
    s=re.sub(r'^```(?:json)?\s*|\s*```$','',s.strip())
    i,j=s.find('{'),s.rfind('}')
    if i<0 or j<0: raise ValueError('no JSON object found')
    return json.loads(s[i:j+1])

def depth(text,start,opens,closes):
    d,neg=start,False
    for ch in text:
        if ch in opens: d+=1
        elif ch in closes:
            d-=1
            if d<0: d,neg=0,True
    return d,neg

def validate_ayah(n,clauses,start_depth=None):
    """-> dict(errors, warnings, depth). errors make the ayah unusable; warnings are for review."""
    start_depth=start_depth or {'en':0,'bn':0}; err,warn=[],[]
    if not isinstance(clauses,list) or not clauses: return dict(errors=['must be a non-empty list of clauses'],warnings=[],depth=start_depth)
    expect=1
    for ci,cl in enumerate(clauses,1):
        if not isinstance(cl,list) or not cl: err.append(f'clause {ci}: must be a non-empty list of phrases'); continue
        for pi,ph in enumerate(cl,1):
            w=f'clause {ci} phrase {pi}'
            if not(isinstance(ph,list) and len(ph)==4): err.append(f'{w}: must be [start,end,"english","bangla"]'); continue
            s,e,en,bn=ph
            if not all(isinstance(x,int) and not isinstance(x,bool) for x in (s,e)): err.append(f'{w}: start/end must be integers'); continue
            if s!=expect: err.append(f'{w}: starts at word {s} but the next uncovered word is {expect}')
            if e<s: err.append(f'{w}: end {e} < start {s}'); continue
            expect=e+1
            if e-s+1>MAX_PHRASE_WORDS: warn.append(f'{w}: {e-s+1} words (long phrase)')
            if not(isinstance(en,str) and en.strip()) or not(isinstance(bn,str) and bn.strip()): err.append(f'{w}: english and bangla must be non-empty strings'); continue
            if not LATIN.search(en) or BENGALI.search(en): err.append(f'{w}: english must be Latin script only')
            if not BENGALI.search(bn) or LATIN.search(bn): err.append(f'{w}: bangla must be Bengali script only (no Latin letters)')
    if expect!=n+1: err.append(f'words 1..{n} must be covered exactly once, but coverage ends at word {expect-1}')
    if err: return dict(errors=err,warnings=warn,depth=start_depth)
    en_t,bn_t=joined(clauses,2),joined(clauses,3)
    if not en_t.rstrip().endswith(END_EN): warn.append('english does not end with punctuation')
    if not bn_t.rstrip().endswith(END_BN): warn.append('bangla does not end with punctuation')
    de,ne=depth(en_t,start_depth['en'],EN_OPEN,EN_CLOSE); db,nb=depth(bn_t,start_depth['bn'],BN_OPEN,BN_CLOSE)
    if ne: warn.append('english closes a quote that was never opened')
    if nb: warn.append('bangla closes a quote that was never opened')
    if de>3 or db>3: warn.append('more than 3 quotes open')
    return dict(errors=[],warnings=warn,depth={'en':de,'bn':db})
