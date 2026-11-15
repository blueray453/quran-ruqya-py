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
from ayahlib import ROOT, Src, ayah_block, load_json, meaning_flags, normalise, parse_json_object  # noqa: E402

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
        prompt += ('\n\nNote: an earlier attempt at this ayah was not accepted: '
                   + '; '.join(hint[:4]) + '. Fix these.')
    return prompt


# ------------------------------------------------------------------ granularity
def granularity(norm):
    n_w = sum(len(p['words']) for cl in norm for p in cl)
    n_p = sum(len(cl) for cl in norm)
    return n_w, n_p, len(norm), n_w / n_p


def assess(norm, mean_limit, clause_limit):
    """Why an ayah looks too coarse: 'phrases' (long phrases / one phrase per clause) and/or
    'clauses' (a clause longer than clause_limit words). Returns (reasons, long_clauses, mean)."""
    n_w, n_p, n_c, mean = granularity(norm)
    reasons = []
    if mean > mean_limit or (n_p == n_c and n_w >= 6):
        reasons.append('phrases')
    long_cl = [cl for cl in norm if sum(len(p['words']) for p in cl) > clause_limit]
    if long_cl:
        reasons.append('clauses')
    return reasons, len(long_cl), mean


def coarse_hint(norm, reasons, clause_limit):
    n_w, n_p, n_c, mean = granularity(norm)
    msgs = []
    if 'phrases' in reasons:
        big = sorted((p for cl in norm for p in cl), key=lambda p: -len(p['words']))[:3]
        ex = '; '.join(f'"{p["en"]}" is one phrase of {len(p["words"])} Arabic words' for p in big)
        msgs.append(f'your earlier segmentation was too coarse ({n_p} phrases for {n_w} words in {n_c} clauses; the '
                    f'reviewed standard is about 1.6 Arabic words per phrase and 2-3 phrases per clause). '
                    f'Split further INSIDE the existing clauses by adding phrases (keep the clause boundaries as they are; '
                    f'do not create new clauses), e.g. {ex}')
    if 'clauses' in reasons:
        longest = sorted(norm, key=lambda cl: -sum(len(p['words']) for p in cl))[:3]
        ex = '; '.join('"' + ' '.join(p['en'] for p in cl) + f'" is one clause of {sum(len(p["words"]) for p in cl)} words'
                       for cl in longest if sum(len(p['words']) for p in cl) > clause_limit)
        msgs.append(f'some clauses are too long (the reviewed standard is about 4 Arabic words per clause, rarely more than '
                    f'{clause_limit}). Split them at natural boundaries (an exception, alternative, comparison, purpose, '
                    f'condition, relative clause or new verb), e.g. {ex}')
    return msgs


# ------------------------------------------------------------------ model call
def reasoning_param(mode):
    """--reasoning / --long-reasoning / --escalate-reasoning value -> OpenRouter `reasoning` object (or None).
    off | none | minimal | low | medium | high | default | max:N (thinking-token budget)"""
    mode = (mode or 'default').strip().lower()
    if mode == 'default':
        return None
    if mode == 'off':
        return {'enabled': False}
    if mode.startswith('max:'):
        return {'max_tokens': int(mode[4:])}
    if mode in ('none', 'minimal', 'low', 'medium', 'high'):
        return {'effort': mode}
    raise SystemExit(f'unknown reasoning mode {mode!r} (off|none|minimal|low|medium|high|default|max:N)')


_warned = set()


def call_openrouter(args, system, user, temperature, model=None, max_tokens=None, reasoning='off'):
    body = {
        'model': model or args.model,
        'temperature': temperature,
        'max_tokens': max_tokens or args.max_tokens,
        'usage': {'include': True},
        'messages': [
            {'role': 'system', 'content': [dict({'type': 'text', 'text': system},
                                                **({} if args.no_cache else {'cache_control': {'type': 'ephemeral'}}))]},
            {'role': 'user', 'content': user},
        ],
    }
    rp = reasoning_param(reasoning)
    if rp:
        body['reasoning'] = rp
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
            choice = resp['choices'][0]
            text, fr = choice['message'].get('content'), choice.get('finish_reason')
            if not text or not str(text).strip():
                raise RuntimeError(f'empty reply (finish_reason={fr})')
            if fr == 'length':
                raise RuntimeError('reply cut off (finish_reason=length); raise --max-tokens / --long-max-tokens')
            return text, dict(resp.get('usage', {}), finish_reason=fr)
        except urllib.error.HTTPError as e:
            last = f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:300]}'
            if e.code == 400 and 'reasoning' in body:      # model rejects the reasoning setting
                body.pop('reasoning')
                if model not in _warned:
                    _warned.add(model)
                    print(f'  warning: {model or args.model} rejected the reasoning setting; it may reason by default '
                          f'(watch the "reasoning" column in the summary)')
                data = json.dumps(body).encode('utf-8')
                continue
            if e.code not in (408, 429, 500, 502, 503, 504):
                break
        except Exception as e:                              # network / JSON hiccup
            last = repr(e)
        time.sleep(2 ** attempt)
    raise RuntimeError(f'OpenRouter call failed: {last}')


def mock_call(batch, src, temperature=0.0, coarse=False):
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
    if coarse and temperature == 0.0:       # test double for a model that writes one phrase per clause
        out = {k: [[{'ar': ' '.join(p['ar'] for p in cl), 'en': ' '.join(p['en'] for p in cl),
                     'bn': ' '.join(p['bn'] for p in cl)}] for cl in v] for k, v in out.items()}
    return json.dumps(out, ensure_ascii=False), {'prompt_tokens': 0, 'completion_tokens': 0, 'cost': 0}


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tag', required=True, help='run name -> runs/<tag>/')
    ap.add_argument('--pilot', help='spec file: lines like "67", "2:255", "2:282-286", # comments')
    ap.add_argument('--surah', type=int, action='append')
    ap.add_argument('--ayahs', help='comma list, e.g. "2:255,2:282-284"')
    ap.add_argument('--model', default='anthropic/claude-haiku-5.5')
    ap.add_argument('--long-model', default='anthropic/claude-sonnet-5.5',
                    help='ayahs longer than --long-words go one by one to this model (empty = disable)')
    ap.add_argument('--long-words', type=int, default=40)
    ap.add_argument('--escalate-model', default='anthropic/claude-sonnet-5.5',
                    help='ayahs still flagged after the Haiku passes get one run here (empty = disable)')
    ap.add_argument('--max-words', type=int, default=220, help='word cap per request')
    ap.add_argument('--max-ayahs', type=int, default=8)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--max-phrase-words', type=int, default=0, help='optional: reject phrases longer than this (0 = no limit, default)')
    ap.add_argument('--retries', type=int, default=2, help='single-ayah retries for failed validation')
    ap.add_argument('--max-tokens', type=int, default=8000)
    ap.add_argument('--long-max-tokens', type=int, default=16000, help='output budget for long ayahs')
    ap.add_argument('--mock-flaky', action='store_true', help='self-test: model fails at temperature 0 on some batches')
    ap.add_argument('--no-bn-wbw', action='store_true', help='omit Bangla word glosses (saves input tokens)')
    ap.add_argument('--no-cache', action='store_true', help='do not mark CONVENTIONS as cacheable')
    ap.add_argument('--reasoning', default='off', help='thinking for the Haiku passes: off|none|minimal|low|medium|high|default|max:N')
    ap.add_argument('--long-reasoning', default='low', help='thinking for long ayahs (same values)')
    ap.add_argument('--escalate-reasoning', default='low', help='thinking for escalated ayahs (same values)')
    ap.add_argument('--out-dir', help='annotation dir (default runs/<tag>/annotations)')
    ap.add_argument('--no-merge', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--coarse-mean', type=float, default=2.4,
                    help='ayahs above this mean Arabic words/phrase (or one phrase per clause) get one finer re-run')
    ap.add_argument('--max-clause-words', type=int, default=6,
                    help='clauses longer than this also trigger the finer re-run (prototype: max 7, 97%% <= 6)')
    ap.add_argument('--coarse-retries', type=int, default=1, help='0 disables the granularity re-run')
    ap.add_argument('--mock-coarse', action='store_true', help='self-test: mock model answers coarsely first')
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
    long_set = {ay for ay in todo if args.long_model and src.n_words(*ay) > args.long_words}
    long_items = sorted(long_set)
    batches = make_batches([ay for ay in todo if ay not in long_set], src, args.max_words, args.max_ayahs)

    def model_for(ay):
        return args.long_model if ay in long_set else args.model

    if long_items:
        print(f'{len(long_items)} long ayah(s) (> {args.long_words} words) go one by one to {args.long_model}')

    if args.dry_run:
        if batches:
            u = build_user_prompt(template, src, batches[0], not args.no_bn_wbw)
            print(f'--- {len(batches)} batched request(s) + {len(long_items)} long ayah(s) for {args.long_model}; first request user prompt '
                  f'({len(u)} chars, ~{len(u) // 2} tokens; system {len(system)} chars) ---\n{u}')
        return
    if not args.mock_replay and not os.environ.get('OPENROUTER_API_KEY'):
        sys.exit('set OPENROUTER_API_KEY first (export OPENROUTER_API_KEY=...)')

    log = open(os.path.join(run, 'calls.jsonl'), 'a', encoding='utf-8')
    usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'cost': 0.0, 'calls': 0, 'words': 0}

    by_cat = {}

    def run_request(batch, temperature, hint=None, model=None, cat='main'):
        model = model or args.model
        user = build_user_prompt(template, src, batch, not args.no_bn_wbw, hint)
        t0 = time.time()
        rec = {'keys': [f'{s}:{a}' for s, a in batch], 'model': model, 'temperature': temperature, 'cat': cat,
               'hint': hint}
        try:
            if args.mock_replay:
                if args.mock_flaky and temperature == 0.0 and any(a % 5 == 0 for s, a in batch):
                    raise RuntimeError('empty reply (finish_reason=length)')
                text, u = mock_call(batch, src, temperature, args.mock_coarse)
            else:
                mode = {'long': args.long_reasoning, 'escalate': args.escalate_reasoning}.get(cat, args.reasoning)
                text, u = call_openrouter(args, system, user, temperature, model,
                                          args.long_max_tokens if cat == 'long' else args.max_tokens, mode)
        except Exception as e:
            rec.update(seconds=round(time.time() - t0, 1), error=str(e))
            log.write(json.dumps(rec, ensure_ascii=False) + '\n')
            log.flush()
            raise
        rec.update(seconds=round(time.time() - t0, 1), usage=u, reply=text)
        log.write(json.dumps(rec, ensure_ascii=False) + '\n')
        log.flush()
        c = by_cat.setdefault(cat, {'calls': 0, 'cost': 0.0, 'in': 0, 'out': 0, 'reason': 0})
        c['reason'] += (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0
        c['calls'] += 1
        c['cost'] += u.get('cost') or 0
        c['in'] += u.get('prompt_tokens', 0)
        c['out'] += u.get('completion_tokens', 0)
        usage['prompt_tokens'] += u.get('prompt_tokens', 0)
        usage['completion_tokens'] += u.get('completion_tokens', 0)
        usage['cost'] += u.get('cost') or 0
        usage['calls'] += 1
        return parse_json_object(text)

    def settle(batch, temperature, hint=None, model=None, cat='main'):
        """Run one request; store validated ayahs; return [(ayah, errors)] that failed."""
        failed = []
        try:
            reply = run_request(batch, temperature, hint, model, cat)
        except Exception as e:
            print(f'  request {batch[0]}..{batch[-1]} failed: {e}')
            msg = f'your reply could not be used ({str(e)[:120]})'
            if isinstance(e, json.JSONDecodeError) or 'Expecting' in str(e) or 'JSON' in str(e):
                msg += ('; return strictly valid JSON: inside text fragments use only curly quotes “ ” ‘ ’, '
                        'never a straight double quote, and no trailing commas')
            return [(ay, [msg]) for ay in batch]
        for s, a in batch:
            key = f'{s}:{a}'
            errs, norm = (normalise(reply.get(key), src.n_words(s, a), max_phrase_words=args.max_phrase_words,
                          src_words=src.align_words(s, a))
                          if key in reply else (['missing from reply'], []))
            if errs:
                print(f'  {key}: invalid ({errs[0]}{" ..." if len(errs) > 1 else ""})')
                log.write(json.dumps({'keys': [key], 'model': model or args.model, 'validation_errors': errs},
                                     ensure_ascii=False) + '\n')
                log.flush()
                failed.append(((s, a), errs))
                continue
            with open(raw_path(s, a), 'w', encoding='utf-8') as fh:
                json.dump({'key': key, 'model': model or args.model, 'clauses': norm,
                           'coarse': bool(assess(norm, args.coarse_mean, args.max_clause_words)[0]),
                           'reasons': assess(norm, args.coarse_mean, args.max_clause_words)[0],
                           'refined': False, 'escalated': False}, fh, ensure_ascii=False)
            usage['words'] += src.n_words(s, a)
        return failed

    failed = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, f in enumerate(ex.map(lambda b: settle(b, 0.0), batches), 1):
            failed += f
            print(f'batch {i}/{len(batches)} done ({len(f)} failed)')
        for f in ex.map(lambda ay: settle([ay], 0.0, model=args.long_model, cat='long'), long_items):
            failed += f
        if long_items:
            print(f'long ayahs done ({len(long_items)})')
        for attempt in range(args.retries):
            if not failed:
                break
            print(f'retry {attempt + 1}: {len(failed)} ayah(s) alone at temperature 0.3')
            failed = [x for f in ex.map(lambda fe: settle([fe[0]], 0.3, fe[1], model_for(fe[0]), 'long' if fe[0] in long_set else 'main'), failed) for x in f]

    # granularity pass: one finer re-run for ayahs the model segmented too coarsely
    def refine(ay):
        s, a = ay
        d = load_json(raw_path(s, a))
        r1, l1, m1 = assess(d['clauses'], args.coarse_mean, args.max_clause_words)
        try:
            reply = run_request([ay], 0.3, coarse_hint(d['clauses'], r1, args.max_clause_words), model_for(ay),
                                'long' if ay in long_set else 'main')
            errs, norm = normalise(reply.get(f'{s}:{a}'), src.n_words(s, a), max_phrase_words=args.max_phrase_words,
                                   src_words=src.align_words(s, a))
        except Exception as e:
            errs, norm = [str(e)], []
        better = False
        if not errs:
            r2, l2, m2 = assess(norm, args.coarse_mean, args.max_clause_words)
            better = (l2, m2) < (l1, m1)            # fewer over-long clauses first, then finer phrases
        if better:
            d.update(clauses=norm, coarse=bool(r2), reasons=r2, model=model_for(ay))
        d['refined'] = True
        with open(raw_path(s, a), 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False)
        return better

    if args.coarse_retries:
        pend = [ay for ay in items if os.path.exists(raw_path(*ay))
                and load_json(raw_path(*ay)).get('coarse') and not load_json(raw_path(*ay)).get('refined')]
        if pend:
            print(f'granularity: {len(pend)} ayah(s) segmented too coarsely; re-running once at temperature 0.3')
            with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
                gained = sum(ex.map(refine, pend))
            print(f'granularity: {gained}/{len(pend)} came back finer')
    # escalation: ayahs still flagged (too coarse, or meaning possibly dropped/moved/doubled) get one run on a stronger model
    def mflags(s, a, norm):
        return meaning_flags({w: ge for w, ar, ge, gb in src.words(s, a)}, norm)

    def escalate(ay):
        s, a = ay
        d = load_json(raw_path(s, a))
        r1, l1, m1 = assess(d['clauses'], args.coarse_mean, args.max_clause_words)
        f1 = mflags(s, a, d['clauses'])
        hint = coarse_hint(d['clauses'], r1, args.max_clause_words) if r1 else []
        if f1:
            hint.append('your earlier answer may have lost, moved or doubled meaning: ' + '; '.join(f1[:4])
                        + '. Each fragment must translate only its own Arabic words, and every word exactly once')
        try:
            reply = run_request([ay], 0.0, hint, args.escalate_model, 'escalate')
            errs, norm = normalise(reply.get(f'{s}:{a}'), src.n_words(s, a), max_phrase_words=args.max_phrase_words,
                                   src_words=src.align_words(s, a))
        except Exception as e:
            errs, norm = [str(e)], []
        better = False
        if not errs:
            r2, l2, m2 = assess(norm, args.coarse_mean, args.max_clause_words)
            # fewer problems wins, but never by merging phrases into a much coarser segmentation
            better = ((l2 + len(mflags(s, a, norm)), m2) < (l1 + len(f1), m1)
                      and (m2 <= m1 + 0.3 or m2 <= args.coarse_mean))
        if better:
            d.update(clauses=norm, coarse=bool(r2), reasons=r2, model=args.escalate_model)
        d['escalated'] = True
        with open(raw_path(s, a), 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False)
        return better

    n_esc = [0]
    if args.escalate_model:
        pend = []
        for ay in items:
            if os.path.exists(raw_path(*ay)):
                d = load_json(raw_path(*ay))
                if not d.get('escalated') and d.get('model') != args.escalate_model and (
                        d.get('coarse') or mflags(ay[0], ay[1], d['clauses'])):
                    pend.append(ay)
        n_esc[0] = len(pend)
        if pend:
            print(f'escalation: {len(pend)} flagged ayah(s) re-run once on {args.escalate_model}')
            with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
                gained = sum(ex.map(escalate, pend))
            print(f'escalation: {gained}/{len(pend)} came back better')
    left = {}
    for s, a in items:
        if os.path.exists(raw_path(s, a)):
            d = load_json(raw_path(s, a))
            why = list(d.get('reasons') or []) + mflags(s, a, d['clauses'])
            if why:
                left[f'{s}:{a}'] = why
    json.dump(left, open(os.path.join(run, 'flags.json'), 'w'), ensure_ascii=False, indent=1)
    if left:
        print(f'{len(left)} ayah(s) still flagged (runs/{args.tag}/flags.json) - review these first')
    still = [f'{s}:{a}' for s, a in items if os.path.exists(raw_path(s, a)) and load_json(raw_path(s, a)).get('coarse')]
    json.dump({k: load_json(raw_path(*map(int, k.split(':')))).get('reasons') for k in still},
              open(os.path.join(run, 'coarse.json'), 'w'), indent=1)
    if still:
        print(f'{len(still)} ayah(s) coarse' + (' even after the re-run' if args.coarse_retries else '') +
              f' (runs/{args.tag}/coarse.json) - review these first')

    log.close()
    done = [(s, a) for s, a in items if os.path.exists(raw_path(s, a))]
    json.dump({f'{ay[0]}:{ay[1]}': errs for ay, errs in failed}, open(os.path.join(run, 'failed.json'), 'w'), indent=1)
    print(f'\nvalidated {len(done)}/{len(items)} ayahs; failed {len(failed)} (runs/{args.tag}/failed.json)')
    if usage['calls']:
        print(f'this run: {usage["calls"]} calls, {usage["prompt_tokens"]:,} in / {usage["completion_tokens"]:,} out tokens, '
              f'reported cost ${usage["cost"]:.4f}')
        for cat, c in sorted(by_cat.items()):
            share = c['reason'] / c['out'] if c['out'] else 0
            print(f'  {cat:9s} {c["calls"]:4d} calls  {c["in"]:>9,} in  {c["out"]:>8,} out  '
                  f'(reasoning {c["reason"]:,} = {share:.0%})  ${c["cost"]:.4f}')
            if share > 0.25:
                print(f'    ^ {cat}: more than a quarter of the output tokens went on hidden reasoning; '
                      f'lower it with --{"" if cat == "main" else cat + "-"}reasoning minimal (or none)')
        # whole-Quran estimate, step by step (valid for a fresh, uninterrupted run; escalation volume varies)
        full_long = [k for k in src.maxkey if args.long_model and src.n_words(*k) > args.long_words]
        fl_words = sum(src.n_words(*k) for k in full_long)
        nl_words_run = sum(src.n_words(*ay) for ay in todo if ay not in long_set)
        nl_ayahs_run = sum(1 for ay in todo if ay not in long_set)
        lg_words_run = sum(src.n_words(*ay) for ay in long_items)
        parts = []
        if by_cat.get('main') and nl_words_run:
            parts.append(('batched Haiku passes', by_cat['main']['cost'] / nl_words_run * (FULL_QURAN_WORDS - fl_words)))
        if by_cat.get('long') and lg_words_run:
            parts.append((f'{len(full_long)} long ayahs', by_cat['long']['cost'] / lg_words_run * fl_words))
        if by_cat.get('escalate') and n_esc[0] and nl_ayahs_run:
            rate = n_esc[0] / nl_ayahs_run
            parts.append((f'escalation ({rate:.0%} of ayahs)', by_cat['escalate']['cost'] / n_esc[0] * rate
                          * (len(src.maxkey) - len(full_long))))
        if parts:
            print('whole-Quran estimate from this run:')
            for name, v in parts:
                print(f'  {name:32s} ~${v:,.2f}')
            print(f'  {"total":32s} ~${sum(v for _, v in parts):,.2f}')

    if args.no_merge:
        return
    by_surah = {}
    for s, a in done:
        d = load_json(raw_path(s, a))
        by_surah.setdefault(s, {})[f'{s}:{a}'] = d['clauses']
    for s, d in sorted(by_surah.items()):
        mf = os.path.join(run, f'merge-{s:03d}.json')
        json.dump(d, open(mf, 'w', encoding='utf-8'), ensure_ascii=False)
        models = sorted({load_json(raw_path(s, int(k.split(':')[1])))['model'] for k in d})
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools/collect.py'), '--surah', str(s), '--file', mf,
                        '--out-dir', out_dir, '--model', ' + '.join(models)], check=True)


if __name__ == '__main__':
    main()
