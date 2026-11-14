#!/usr/bin/env python3
"""Generate clause/phrase annotations (Arabic word ranges + English + Bangla) with an LLM via OpenRouter.

Per surah it writes annotations/surah-NNN.json:
  {"surah":N, "ayahs":{"1":[[ [s,e,"en","bn"],... ],...clauses]}, "status":{"1":{status,warnings,model,prompt_hash,depth}}}
`ayahs` has the same shape the build already reads. Status is auto | needs_human | reviewed (set reviewed by hand after checking).
Resumable: ayahs already auto/reviewed are skipped. Standard library only.

Examples
  export OPENROUTER_API_KEY=...
  python3 scripts/generate_spec.py --data-root /path/to/qul --surah 67 --model <openrouter-model-slug> --dry-run
  python3 scripts/generate_spec.py --data-root /path/to/qul --surahs 1-114 --model <openrouter-model-slug>
  python3 scripts/generate_spec.py ... --retry-failed          # re-run needs_human ayahs
  python3 scripts/generate_spec.py ... --mock-response f.json  # offline test: f.json = {"67:1": clauses, ...}
"""
import argparse,json,os,sys,time,urllib.request,urllib.error
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from spec_lib import *
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap=argparse.ArgumentParser()
ap.add_argument('--data-root',required=True,help='folder laid out like your QUL tree (see spec_lib.load_sources)')
ap.add_argument('--surah',type=int); ap.add_argument('--surahs',help='range like 1-114')
ap.add_argument('--model',default='unset'); ap.add_argument('--batch-words',type=int,default=350)
ap.add_argument('--max-retries',type=int,default=2); ap.add_argument('--temperature',type=float,default=0.2)
ap.add_argument('--out',default=os.path.join(ROOT,'annotations')); ap.add_argument('--dry-run',action='store_true')
ap.add_argument('--retry-failed',action='store_true'); ap.add_argument('--mock-response')
a=ap.parse_args()
if a.surah: surahs=[a.surah]
elif a.surahs: lo,hi=(int(x) for x in a.surahs.split('-')); surahs=list(range(lo,hi+1))
else: sys.exit('give --surah N or --surahs A-B')
if not a.dry_run and not a.mock_response and (not os.environ.get('OPENROUTER_API_KEY') or a.model=='unset'):
    sys.exit('Set OPENROUTER_API_KEY and pass --model <openrouter-model-slug> (or use --dry-run / --mock-response).')
src=load_sources(a.data_root)
sysmsg,phash=system_prompt(os.path.join(ROOT,'annotations','CONVENTIONS.md'),os.path.join(ROOT,'annotations','glossary.json'))
mock=json.load(open(a.mock_response,encoding='utf-8')) if a.mock_response else None
KEY=os.environ.get('OPENROUTER_API_KEY')

def ask(messages,keys):
    if mock is not None: return json.dumps({k:mock[k] for k in keys if k in mock},ensure_ascii=False),{}
    body=json.dumps({'model':a.model,'messages':messages,'temperature':a.temperature}).encode()
    req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=body,
        headers={'Authorization':f'Bearer {KEY}','Content-Type':'application/json'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req,timeout=600) as r: d=json.load(r)
            return d['choices'][0]['message']['content'],d.get('usage',{})
        except urllib.error.HTTPError as e:
            if e.code in (429,500,502,503,504): time.sleep(2**attempt*2); continue
            raise RuntimeError(f'HTTP {e.code}: {e.read()[:300]!r}')
        except (urllib.error.URLError,TimeoutError): time.sleep(2**attempt*2)
    raise RuntimeError('OpenRouter request failed after 5 attempts')

def save(path,obj):
    tmp=path+'.tmp'; json.dump(obj,open(tmp,'w',encoding='utf-8'),ensure_ascii=False,indent=1); os.replace(tmp,path)

os.makedirs(a.out,exist_ok=True); tot=dict(ok=0,failed=0,skipped=0,calls=0)
for s in surahs:
    aw=src['idx'][s]; path=os.path.join(a.out,f'surah-{s:03d}.json')
    doc=json.load(open(path,encoding='utf-8')) if os.path.exists(path) else {'surah':s,'ayahs':{},'status':{}}
    done=lambda n:(lambda st:st in ('auto','reviewed') or (st=='needs_human' and not a.retry_failed))(doc['status'].get(str(n),{}).get('status'))
    for bi,batch in enumerate(make_batches(aw,a.batch_words),1):
        todo=[n for n in batch if not done(n)]
        tot['skipped']+=len(batch)-len(todo)
        if not todo: continue
        prevn=todo[0]-1; pst=doc['status'].get(str(prevn)); prev=None
        if pst and str(prevn) in doc['ayahs']:
            cl=doc['ayahs'][str(prevn)]; prev=dict(key=f'{s}:{prevn}',en=joined(cl,2),bn=joined(cl,3),depth_en=pst['depth']['en'],depth_bn=pst['depth']['bn'])
        words=sum(len(aw[n]) for n in todo); up=user_prompt(src,s,todo,prev)
        if a.dry_run:
            pd=os.path.join(a.out,'_prompts'); os.makedirs(pd,exist_ok=True)
            open(os.path.join(pd,f'surah-{s:03d}-batch-{bi:02d}.txt'),'w',encoding='utf-8').write('=== SYSTEM ===\n'+sysmsg+'\n\n=== USER ===\n'+up)
            print(f'surah {s} batch {bi}: ayahs {todo[0]}-{todo[-1]} ({len(todo)}), {words} words, prompt ~{(len(sysmsg)+len(up))//1000}k chars'); continue
        messages=[{'role':'system','content':sysmsg},{'role':'user','content':up}]; pending=list(todo); errs={}
        for attempt in range(a.max_retries+1):
            reply,usage=ask(messages,[f'{s}:{n}' for n in pending]); tot['calls']+=1
            open(os.path.join(a.out,'usage.jsonl'),'a').write(json.dumps(dict(surah=s,batch=bi,attempt=attempt,model=a.model,**{k:usage.get(k) for k in ('prompt_tokens','completion_tokens')}))+'\n')
            try: got=parse_response(reply)
            except Exception as e: got={}; errs={n:[f'unparseable reply: {e}'] for n in pending}
            failed=[]
            for n in pending:
                vk=f'{s}:{n}'; st_prev=doc['status'].get(str(n-1)); sd=(st_prev or {}).get('depth') if st_prev else {'en':0,'bn':0}
                if n==todo[0] and prev: sd={'en':prev['depth_en'],'bn':prev['depth_bn']}
                if vk not in got:
                    errs[n]=errs.get(n) or ['missing from reply']; failed.append(n)
                    doc['status'][str(n)]=dict(status='needs_human',errors=errs[n],model=a.model,prompt_hash=phash,depth=sd); continue
                r=validate_ayah(len(aw[n]),got[vk],sd)
                if r['errors']: errs[n]=r['errors']; failed.append(n); doc['ayahs'].pop(str(n),None); doc['status'][str(n)]=dict(status='needs_human',errors=r['errors'],model=a.model,prompt_hash=phash,depth=sd); continue
                doc['ayahs'][str(n)]=got[vk]; doc['status'][str(n)]=dict(status='auto',warnings=r['warnings'],model=a.model,prompt_hash=phash,depth=r['depth'])
            pending=failed
            if not pending: break
            messages+=[{'role':'assistant','content':reply},{'role':'user','content':'These ayahs failed validation; return corrected JSON for ONLY these ayahs (same format):\n'+'\n'.join(f'{s}:{n}: '+'; '.join(errs[n]) for n in pending)}]
        tot['ok']+=len(todo)-len(pending); tot['failed']+=len(pending)
        doc['ayahs']={k:doc['ayahs'][k] for k in sorted(doc['ayahs'],key=int)}; save(path,doc)
        print(f'surah {s} batch {bi}: ok {len(todo)-len(pending)}/{len(todo)}'+(f' | needs_human: {pending}' if pending else ''))
print(tot)
