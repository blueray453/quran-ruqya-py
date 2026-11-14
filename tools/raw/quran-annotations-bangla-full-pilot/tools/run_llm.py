#!/usr/bin/env python3
"""tools/run_llm.py — combined (English + Bangla) annotation pass via OpenRouter.

  export OPENROUTER_API_KEY=sk-or-...
  python3 tools/run_llm.py --pilot pilot.txt --tag pilot1            # run + merge
  python3 tools/run_llm.py --pilot pilot.txt --tag pilot1 --dry-run   # show prompt, no cost
  python3 tools/run_llm.py --surah 67 --tag t --mock-replay           # offline self-test

Stdlib only. Resumable: every validated ayah is stored in runs/<tag>/raw/, so a re-run
only pays for what is missing or failed. The prompt contains no chunker/treebank data.
Output goes to runs/<tag>/annotations/ (never to annotations/) unless --out-dir says so.
"""
import argparse, concurrent.futures as cf, json, os, re, subprocess, sys, time, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, Src, ayah_block, load_json, normalise, parse_json_object  # noqa: E402

API = 'https://openrouter.ai/api/v1/chat/completions'
FULL_QURAN_WORDS = 77432


def parse_spec(lines, src):
    """'67' | '2:255' | '2:255-260' | comments (#) -> ordered list of (surah, ayah)."""
    out, seen = [], set()
    for ln in lines:
        ln = ln.split('#')[0].strip()
        if not ln:
            continue
        if ':' not in ln:
            items = [(int(ln), a) for a in src.ayahs(int(ln))]
        else:
            s, rest = ln.split(':')
            lo, _, hi = rest.partition('-')
            items = [(int(s), a) for a in range(int(lo), int(hi or lo) + 1)]
        for it in items:
            if it not in seen and it in src.maxkey:
                seen.add(it)
                out.append(it)
    return out


def make_batches(items, src, max_words, max_ayahs):
    batches, cur, w = [], [], 0
    for s, a in items:
        n = src.n_words(s, a)
        consecutive = cur and cur[-1][0] == s and cur[-1][1] == a - 1
        if cur and (not consecutive or w + n > max_words or len(cur) >= max_ayahs):
            batches.append(cur)
            cur, w = [], 0
        cur.append((s, a))
        w += n
    if cur:
        batches.append(cur)
    return batches


def load_template():
    txt = open(os.path.join(ROOT, 'prompts/annotate_ayah_combined.md'), encoding='utf-8').read()
    return re.search(r'## Prompt template\s+```\n(.*?)\n```', txt, re.S).group(1)


def build_user_prompt(template, src, batch, bn_wbw, hint=None):
    blocks = [ayah_block(src, s, a, bn_wbw, prev_context=(i == 0)) for i, (s, a) in enumerate(batch)]
    keys = ', '.join(f'{s}:{a}' for s, a in batch)
    prompt = template.replace('{AYAH_BLOCKS}', '\n\n'.join(blocks)).replace('{KEYS}', keys)
    if hint:   # structural problems only (tiling / size / script) - never linguistic or chunker feedback
        prompt += ('\n\nNote: an earlier attempt at this ayah was rejected for structural reasons: '
                   + '; '.join(hint[:4]) + '. Fix these.')
    return prompt


# ------------------------------------------------------------------ model call
def call_openrouter(args, system, user, temperature):
    body = {
        'model': args.model,
        'temperature': temperature,
        'max_tokens': args.max_tokens,
        'usage': {'include': True},
        'messages': [
            {'role': 'system', 'content': [dict({'type': 'text', 'text': system},
                                                **({} if args.no_cache else {'cache_control': {'type': 'ephemeral'}}))]},
            {'role': 'user', 'content': user},
        ],
    }
    if args.reasoning == 'off':
        body['reasoning'] = {'enabled': False}
    data = json.dumps(body).encode('utf-8')
    hdr = {'Authorization': f'Bearer {os.environ["OPENROUTER_API_KEY"]}', 'Content-Type': 'application/json',
           'X-Title': 'quran-annotations'}
    last = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(API, data=data, headers=hdr)
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.loads(r.read().decode('utf-8'))
            if 'error' in resp:
                raise RuntimeError(json.dumps(resp['error'])[:300])
            return resp['choices'][0]['message']['content'], resp.get('usage', {})
        except urllib.error.HTTPError as e:
            last = f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:300]}'
            if e.code == 400 and 'reasoning' in body:      # model rejects the reasoning switch
                body.pop('reasoning')
                data = json.dumps(body).encode('utf-8')
                continue
            if e.code not in (408, 429, 500, 502, 503, 504):
                break
        except Exception as e:                              # network / JSON hiccup
            last = repr(e)
        time.sleep(2 ** attempt)
    raise RuntimeError(f'OpenRouter call failed: {last}')


def mock_call(batch, src):
    """Offline test double: replay the bundled Surah 67 hand-edited prototype."""
    a_doc = load_json(os.path.join(ROOT, 'annotations/surah-067.json'))
    b_doc = load_json(os.path.join(ROOT, 'annotations/bn/surah-067.json'))
    out = {}
    for s, a in batch:
        assert s == 67, 'mock replay only knows surah 67'
        sw = src.align_words(s, a)
        out[f'{s}:{a}'] = [[{'ar': ' '.join(sw[w - 1][2] for w in p['words']),
                             'en': p['en'], 'bn': b_doc['ayahs'][str(a)]['clauses'][ci]['phrases'][pi]['bn']}
                            for pi, p in enumerate(c['phrases'])]
                           for ci, c in enumerate(a_doc['ayahs'][str(a)]['clauses'])]
    return json.dumps(out, ensure_ascii=False), {'prompt_tokens': 0, 'completion_tokens': 0, 'cost': 0}


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tag', required=True, help='run name -> runs/<tag>/')
    ap.add_argument('--pilot', help='spec file: lines like "67", "2:255", "2:282-286", # comments')
    ap.add_argument('--surah', type=int, action='append')
    ap.add_argument('--ayahs', help='comma list, e.g. "2:255,2:282-284"')
    ap.add_argument('--model', default='anthropic/claude-haiku-5.5')
    ap.add_argument('--max-words', type=int, default=220, help='word cap per request')
    ap.add_argument('--max-ayahs', type=int, default=8)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--max-phrase-words', type=int, default=0, help='optional: reject phrases longer than this (0 = no limit, default)')
    ap.add_argument('--retries', type=int, default=2, help='single-ayah retries for failed validation')
    ap.add_argument('--max-tokens', type=int, default=8000)
    ap.add_argument('--no-bn-wbw', action='store_true', help='omit Bangla word glosses (saves input tokens)')
    ap.add_argument('--no-cache', action='store_true', help='do not mark CONVENTIONS as cacheable')
    ap.add_argument('--reasoning', choices=['off', 'default'], default='off')
    ap.add_argument('--out-dir', help='annotation dir (default runs/<tag>/annotations)')
    ap.add_argument('--no-merge', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--mock-replay', action='store_true', help='offline self-test (surah 67 only)')
    args = ap.parse_args()

    src = Src()
    spec = []
    if args.pilot:
        spec += open(args.pilot, encoding='utf-8').read().splitlines()
    spec += [str(s) for s in (args.surah or [])]
    if args.ayahs:
        spec += args.ayahs.split(',')
    items = parse_spec(spec, src)
    if not items:
        sys.exit('nothing to do: give --pilot / --surah / --ayahs')

    run = os.path.join(ROOT, 'runs', args.tag)
    raw_dir = os.path.join(run, 'raw')
    out_dir = os.path.abspath(args.out_dir or os.path.join(run, 'annotations'))
    os.makedirs(raw_dir, exist_ok=True)

    def raw_path(s, a):
        return os.path.join(raw_dir, f'{s:03d}-{a:03d}.json')

    todo = [(s, a) for s, a in items if not os.path.exists(raw_path(s, a))]
    words_total = sum(src.n_words(s, a) for s, a in items)
    print(f'{len(items)} ayahs / {words_total} words selected; {len(items) - len(todo)} already done, {len(todo)} to run')

    system = open(os.path.join(ROOT, 'CONVENTIONS.md'), encoding='utf-8').read()
    template = load_template()
    batches = make_batches(todo, src, args.max_words, args.max_ayahs)

    if args.dry_run:
        if batches:
            u = build_user_prompt(template, src, batches[0], not args.no_bn_wbw)
            print(f'--- {len(batches)} request(s); first request user prompt '
                  f'({len(u)} chars, ~{len(u) // 2} tokens; system {len(system)} chars) ---\n{u}')
        return
    if not args.mock_replay and not os.environ.get('OPENROUTER_API_KEY'):
        sys.exit('set OPENROUTER_API_KEY first (export OPENROUTER_API_KEY=...)')

    log = open(os.path.join(run, 'calls.jsonl'), 'a', encoding='utf-8')
    usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'cost': 0.0, 'calls': 0, 'words': 0}

    def run_request(batch, temperature, hint=None):
        user = build_user_prompt(template, src, batch, not args.no_bn_wbw, hint)
        t0 = time.time()
        text, u = mock_call(batch, src) if args.mock_replay else call_openrouter(args, system, user, temperature)
        log.write(json.dumps({'keys': [f'{s}:{a}' for s, a in batch], 'model': args.model, 'temperature': temperature,
                              'seconds': round(time.time() - t0, 1), 'usage': u, 'reply': text},
                             ensure_ascii=False) + '\n')
        log.flush()
        usage['prompt_tokens'] += u.get('prompt_tokens', 0)
        usage['completion_tokens'] += u.get('completion_tokens', 0)
        usage['cost'] += u.get('cost') or 0
        usage['calls'] += 1
        return parse_json_object(text)

    def settle(batch, temperature, hint=None):
        """Run one request; store validated ayahs; return [(ayah, errors)] that failed."""
        failed = []
        try:
            reply = run_request(batch, temperature, hint)
        except Exception as e:
            print(f'  request {batch[0]}..{batch[-1]} failed: {e}')
            return [(ay, None) for ay in batch]
        for s, a in batch:
            key = f'{s}:{a}'
            errs, norm = (normalise(reply.get(key), src.n_words(s, a), max_phrase_words=args.max_phrase_words,
                          src_words=src.align_words(s, a))
                          if key in reply else (['missing from reply'], []))
            if errs:
                print(f'  {key}: invalid ({errs[0]}{" ..." if len(errs) > 1 else ""})')
                failed.append(((s, a), errs))
                continue
            with open(raw_path(s, a), 'w', encoding='utf-8') as fh:
                json.dump({'key': key, 'model': args.model, 'clauses': norm}, fh, ensure_ascii=False)
            usage['words'] += src.n_words(s, a)
        return failed

    failed = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, f in enumerate(ex.map(lambda b: settle(b, 0.0), batches), 1):
            failed += f
            print(f'batch {i}/{len(batches)} done ({len(f)} failed)')
        for attempt in range(args.retries):
            if not failed:
                break
            print(f'retry {attempt + 1}: {len(failed)} ayah(s) alone at temperature 0.3')
            failed = [x for f in ex.map(lambda fe: settle([fe[0]], 0.3, fe[1]), failed) for x in f]

    log.close()
    done = [(s, a) for s, a in items if os.path.exists(raw_path(s, a))]
    json.dump({f'{ay[0]}:{ay[1]}': errs for ay, errs in failed}, open(os.path.join(run, 'failed.json'), 'w'), indent=1)
    print(f'\nvalidated {len(done)}/{len(items)} ayahs; failed {len(failed)} (runs/{args.tag}/failed.json)')
    if usage['calls']:
        print(f'this run: {usage["calls"]} calls, {usage["prompt_tokens"]:,} in / {usage["completion_tokens"]:,} out tokens, '
              f'reported cost ${usage["cost"]:.4f}')
        if usage['words']:
            k = FULL_QURAN_WORDS / usage['words']
            print(f'extrapolated to the whole Quran ({FULL_QURAN_WORDS:,} words): '
                  f'~{usage["prompt_tokens"] * k / 1e6:.1f}M in / {usage["completion_tokens"] * k / 1e6:.1f}M out tokens, '
                  f'~${usage["cost"] * k:.2f}  (retries inflate this run slightly)')

    if args.no_merge:
        return
    by_surah = {}
    for s, a in done:
        d = load_json(raw_path(s, a))
        by_surah.setdefault(s, {})[f'{s}:{a}'] = d['clauses']
    for s, d in sorted(by_surah.items()):
        mf = os.path.join(run, f'merge-{s:03d}.json')
        json.dump(d, open(mf, 'w', encoding='utf-8'), ensure_ascii=False)
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools/collect.py'), '--surah', str(s), '--file', mf,
                        '--out-dir', out_dir, '--model', args.model], check=True)


if __name__ == '__main__':
    main()
