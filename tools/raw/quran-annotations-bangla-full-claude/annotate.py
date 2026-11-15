#!/usr/bin/env python3
"""Annotate Quran ayahs with Arabic chunks + English + Bangla. One file, stdlib only.

    export OPENROUTER_API_KEY=sk-or-...
    python3 annotate.py --tag haiku_smoke --pilot runs/haiku_smoke/pilot.txt
    python3 annotate.py --tag mulk --surah 67          # any ayahs: --ayahs "2:255,2:282-286"

How it works, per ayah that has no runs/<tag>/raw/SSS-AAA.json yet:
  1. build prompt (CONVENTIONS.md + numbered Arabic words + glosses + reference translations)
  2. call the model, parse its JSON, validate (every word covered once, in order; en/bn present;
     Allah/Rabb/ilah terminology)
  3. valid -> write the raw file.  invalid -> retry (error + exact missing words fed back).
  4. still invalid after the retries -> STOP, write runs/<tag>/STOPPED.md, exit 1.
Run the same command again to resume: finished ayahs are skipped.
Finished ayahs are merged into runs/<tag>/annotations/ (English) and .../bn/ (Bangla).
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
API = 'https://openrouter.ai/api/v1/chat/completions'

# ------------------------------------------------------------------ sources


def load_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


ZERO_WIDTH = re.compile('[\u200b-\u200f\u202a-\u202e\u2060\ufeff]')


class Src:
    """Read-only view of sources/: Arabic words, per-word glosses, reference translations."""

    def __init__(self):
        S = os.path.join(ROOT, 'sources')
        self.text = load_json(os.path.join(S, 'text/indopak.json'))
        self.gloss_en = load_json(os.path.join(S, 'wbw/english-wbw-translation.json'))
        self.gloss_bn = load_json(os.path.join(S, 'wbw/bangla-wbw-translation.json'))
        self.tr_en, self.tr_bn = {}, {}
        for name in sorted(os.listdir(os.path.join(S, 'translation'))):
            if not name.endswith('.json'):
                continue
            data = {k: (v.get('t') if isinstance(v, dict) else v)
                    for k, v in load_json(os.path.join(S, 'translation', name)).items()}
            (self.tr_bn if 'bn-' in name else self.tr_en).update(data)
        self.maxkey = {}  # (surah, ayah) -> highest word number (the last one is the ayah-end marker)
        for k in self.text:
            s, a, w = map(int, k.split(':'))
            self.maxkey[(s, a)] = max(self.maxkey.get((s, a), 0), w)

    def n_words(self, s, a):
        return self.maxkey[(s, a)] - 1

    def words(self, s, a):
        """[(position, arabic, english gloss, bangla gloss)]"""
        return [(w, ' '.join(ZERO_WIDTH.sub('', self.text[f'{s}:{a}:{w}']['text']).split()),
                 self.gloss_en.get(f'{s}:{a}:{w}', '[no gloss]'),
                 self.gloss_bn.get(f'{s}:{a}:{w}', '[no gloss]'))
                for w in range(1, self.n_words(s, a) + 1)]


def parse_spec(lines, src):
    """'67', '2:255', '2:282-286' and # comments -> ordered, de-duplicated [(surah, ayah)]."""
    out, seen = [], set()
    for ln in lines:
        ln = ln.split('#')[0].strip()
        if not ln:
            continue
        if ':' in ln:
            s, rest = ln.split(':', 1)
            lo, _, hi = rest.partition('-')
            items = [(int(s), a) for a in range(int(lo), int(hi or lo) + 1)]
        else:
            items = sorted((s, a) for (s, a) in src.maxkey if s == int(ln))
        for it in items:
            if it in src.maxkey and it not in seen:
                seen.add(it)
                out.append(it)
    return out


# ------------------------------------------------------------------- prompt

BAD_BN = re.compile(r'ঈশ্বর|প্রভু(?!ত্ব)|খোদা(?!ই)')   # খোদাই = "carve", প্রভুত্ব = "dominion": fine
BAD_EN = re.compile(r'\b(?:god|gods|lord|lords|lordship|deity|deities)\b', re.I)
RESPECTFUL = re.compile(r'আপনি|আপনার|আপনাকে|বলুন|ফেরান|দেখুন')
PLAIN = re.compile(r'(?<![\u0980-\u09FF])(?:তুমি|তোমার|তোমাকে|বল|ফিরাও|দেখো)(?![\u0980-\u09FF])')


def ayah_block(src, s, a):
    lines = []
    if a > 1 and f'{s}:{a - 1}' in src.tr_en:
        lines += [f'Previous ayah, English reference translation (context only; do not annotate): '
                  f'"{src.tr_en[f"{s}:{a - 1}"]}"', '']
    lines += [f'### Ayah {s}:{a}',
              'Words (position, Arabic text, English word gloss, Bangla word gloss):']
    for w, ar, ge, gb in src.words(s, a):
        if BAD_BN.search(gb):  # a few source glosses use a banned term (e.g. 67:21 word 11): don't show it
            gb = '(source gloss withheld: uses a prohibited term; translate from the Arabic)'
        lines.append(f'{w} {ar} — {ge} — {gb}')
    ref_bn = src.tr_bn[f'{s}:{a}']
    lines += ['', f'English reference translation: "{src.tr_en[f"{s}:{a}"]}"',
              f'Bangla reference translation: "{ref_bn}"']
    resp, plain = bool(RESPECTFUL.search(ref_bn)), bool(PLAIN.search(ref_bn))
    if resp and not plain:
        lines.append('Bangla address register (taken from the reference): RESPECTFUL - use আপনি / আপনার / '
                     'আপনাকে and respectful imperatives (“বলুন” for “Say”, never “বল” or “তুমি”).')
    elif plain and not resp:
        lines.append('Bangla address register (taken from the reference): PLAIN - use তুমি / তোমার / '
                     'তোমাকে and plain imperatives (“বল” for “Say”), never আপনি.')
    return '\n'.join(lines)


def build_prompt(template, src, s, a, hint=None):
    prompt = template.replace('{AYAH_BLOCKS}', ayah_block(src, s, a)).replace('{KEYS}', f'{s}:{a}')
    if hint:
        prompt += ('\n\nYour previous reply was rejected: ' + '; '.join(hint) +
                   '. Fix this. The "words" of all chunks must cover 1..N exactly once, in order '
                   '([a, b] means words a..b inclusive; chunk k+1 starts right after chunk k ends).')
    return prompt


# ---------------------------------------------------------------- model call

def call_model(model, system, user, temperature, max_tokens, thinking):
    """One OpenRouter chat call (network/5xx errors retried with backoff). -> (text, usage)"""
    system_block = {'type': 'text', 'text': system}
    if model.startswith('anthropic/'):
        system_block['cache_control'] = {'type': 'ephemeral'}
    body = {'model': model, 'temperature': temperature, 'max_tokens': max_tokens,
            'usage': {'include': True},
            'messages': [{'role': 'system', 'content': [system_block]},
                         {'role': 'user', 'content': user}]}
    body['reasoning'] = {'enabled': False} if thinking == 'off' else {'effort': thinking}
    last = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(
                API, data=json.dumps(body).encode('utf-8'),
                headers={'Authorization': f'Bearer {os.environ["OPENROUTER_API_KEY"]}',
                         'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.loads(r.read().decode('utf-8'))
            if 'error' in resp:
                raise RuntimeError(json.dumps(resp['error'])[:400])
            choice = resp['choices'][0]
            text = (choice.get('message') or {}).get('content')
            if not text or not str(text).strip():
                raise RuntimeError(f'empty reply (finish_reason={choice.get("finish_reason")})')
            if choice.get('finish_reason') == 'length':
                raise RuntimeError('reply cut off (finish_reason=length)')
            return text, resp.get('usage', {})
        except urllib.error.HTTPError as exc:
            last = f'HTTP {exc.code}: {exc.read().decode("utf-8", "replace")[:300]}'
            if exc.code == 400 and 'reasoning' in body:   # model rejects the thinking switch: drop it
                body.pop('reasoning')
                continue
            if exc.code not in (408, 429, 500, 502, 503, 504):
                break
        except Exception as exc:  # timeouts, dropped connections
            last = repr(exc)
        time.sleep(2 ** attempt)
    raise RuntimeError(f'API call failed: {last}')


# ---------------------------------------------------------------- validation

def parse_reply(text, key):
    """The model's JSON object -> list of chunks for `key`. Tolerates code fences / chatter around it."""
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    i = t.find('{')
    if i < 0:
        raise ValueError('no JSON object in reply')
    obj, _ = json.JSONDecoder().raw_decode(t, i)
    if not isinstance(obj, dict) or key not in obj:
        raise ValueError(f'reply has no "{key}" entry')
    return obj[key]


def words_of(chunk):
    """[n] or [first, last] (inclusive) or a full list -> list of word numbers."""
    w = chunk['words']
    if not isinstance(w, list) or not w or not all(isinstance(x, int) for x in w):
        raise ValueError(f'bad words {w!r}')
    if len(w) == 2:
        if w[1] < w[0]:
            raise ValueError(f'bad range {w!r}')
        return list(range(w[0], w[1] + 1))
    if w != list(range(w[0], w[0] + len(w))):
        raise ValueError(f'words not contiguous/ascending {w!r}')
    return w


_PLAIN = {ord(c): r for c, r in (('\u2018', "'"), ('\u2019', "'"), ('\u201c', '"'), ('\u201d', '"'),
                                 ('\u2013', '-'), ('\u2014', '-'), ('\u2026', '...'), ('\u00a0', ' '),
                                 ('\u200b', ''), ('\u200c', ''), ('\u200d', ''), ('\ufeff', ''))}
_BN = re.compile('[\u0980-\u09ff]')
_AR = re.compile('[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]')


def validate(chunks, n):
    """-> (errors, clean chunks [{words, en, bn}])"""
    if not isinstance(chunks, list) or not chunks:
        return ['no chunks (expected a non-empty list)'], []
    errs, out, expect = [], [], 1
    for i, c in enumerate(chunks, 1):
        try:
            w = words_of(c)
        except (ValueError, KeyError, TypeError) as e:
            return errs + [f'chunk {i}: {e}'], out
        if w[0] < 1 or w[-1] > n:
            errs.append(f'chunk {i}: words {w[0]}-{w[-1]} are outside the ayah (1-{n})')
        if w[0] != expect:
            errs.append(f'chunk {i}: starts at word {w[0]}, expected {expect} (gap/overlap/reordering)')
        expect = w[-1] + 1
        en = str(c.get('en') or '').translate(_PLAIN).strip()
        bn = str(c.get('bn') or '').translate(_PLAIN).strip()
        if not en:
            errs.append(f'chunk {i}: empty en')
        elif _AR.search(en) or _BN.search(en):
            errs.append(f'chunk {i}: en contains Arabic/Bengali script')
        elif BAD_EN.search(en):
            errs.append(f'chunk {i}: English uses God/Lord/deity; use Allah / Rabb / ilah')
        if not bn:
            errs.append(f'chunk {i}: empty bn')
        elif not _BN.search(bn) or _AR.search(bn):
            errs.append(f'chunk {i}: bn must be Bengali script only')
        elif BAD_BN.search(bn):
            errs.append(f'chunk {i}: Bangla uses ঈশ্বর/প্রভু/খোদা; use আল্লাহ / রব / ইলাহ')
        out.append({'words': w, 'en': en, 'bn': bn})
    if expect != n + 1:
        errs.append(f'tiling ends at word {expect - 1}, ayah has {n} words')
    return errs, out


def coverage_hint(chunks, src, s, a):
    """Name the exact words the model skipped / used twice, with their Arabic."""
    count = {w: 0 for w in range(1, src.n_words(s, a) + 1)}
    try:
        for c in chunks:
            for w in words_of(c):
                if w in count:
                    count[w] += 1
    except Exception:
        return []
    ar = {w: t for w, t, _, _ in src.words(s, a)}
    return ([f'word {w} ({ar[w]}) is not covered by any chunk' for w, c in count.items() if c == 0] +
            [f'word {w} ({ar[w]}) is covered by {c} chunks' for w, c in count.items() if c > 1])


def explain(exc, text):
    """Plain-English reason; for broken JSON, show the exact offending line."""
    if isinstance(exc, json.JSONDecodeError) and text:
        lines = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip()).splitlines()
        bad = lines[exc.lineno - 1] if 0 < exc.lineno <= len(lines) else ''
        return (f'Model reply is not valid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}.\n'
                f'    {bad}\n    {" " * max(exc.colno - 1, 0)}^')
    return str(exc)


# --------------------------------------------------------------------- merge

def merge(run, raw_dir, model):
    """All finished raw ayahs -> annotations/surah-NNN.json (English) and bn/surah-NNN.json (Bangla)."""
    by_surah = {}
    for name in sorted(os.listdir(raw_dir)):
        if name.endswith('.json'):
            raw = load_json(os.path.join(raw_dir, name))
            s, a = map(int, raw['key'].split(':'))
            by_surah.setdefault(s, {})[a] = raw['chunks']
    for s, ayahs in by_surah.items():
        for lang, field, note in (('en', 'en', 'Flat Arabic chunks with English, merged by annotate.py.'),
                                  ('bn', 'bn', 'Bangla overlay; chunk spans mirror the English file.')):
            doc = {'schema_version': '2.0', 'conventions_version': '4.0', 'surah': s, 'language': lang,
                   'provenance': {'generator': 'llm-annotation', 'model': model, 'note': note},
                   'ayahs': {str(a): {'status': 'auto',
                                      'chunks': [{'words': c['words'], field: c[field]} for c in chunks]}
                             for a, chunks in sorted(ayahs.items())}}
            path = os.path.join(run, 'annotations', *(['bn'] if lang == 'bn' else []), f'surah-{s:03d}.json')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tag', required=True, help='run name -> runs/<tag>/')
    ap.add_argument('--pilot', help='file with lines like "67", "2:255", "2:282-286"')
    ap.add_argument('--surah', type=int, action='append')
    ap.add_argument('--ayahs', help='e.g. "2:255,2:282-284"')
    ap.add_argument('--model', default=os.environ.get('MODEL', 'anthropic/claude-haiku-5.5'))
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--retries', type=int, default=2, help='automatic retries per ayah before stopping')
    ap.add_argument('--retry-thinking', default='low', help='thinking for retries: off|low|medium|high')
    args = ap.parse_args()
    if not os.environ.get('OPENROUTER_API_KEY'):
        sys.exit('set OPENROUTER_API_KEY first')

    src = Src()
    spec = open(args.pilot, encoding='utf-8').read().splitlines() if args.pilot else []
    spec += [str(s) for s in (args.surah or [])] + (args.ayahs.split(',') if args.ayahs else [])
    items = parse_spec(spec, src)
    if not items:
        sys.exit('nothing to do: give --pilot / --surah / --ayahs')

    run = os.path.join(ROOT, 'runs', args.tag)
    raw_dir, fail_dir = os.path.join(run, 'raw'), os.path.join(run, 'failures')
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(fail_dir, exist_ok=True)
    stopped_md = os.path.join(run, 'STOPPED.md')
    if os.path.exists(stopped_md):
        os.remove(stopped_md)

    def raw_path(s, a):
        return os.path.join(raw_dir, f'{s:03d}-{a:03d}.json')

    todo = [ay for ay in items if not os.path.exists(raw_path(*ay))]
    print(f'{len(items)} ayahs selected, {len(items) - len(todo)} already done, {len(todo)} to run '
          f'(model {args.model})')

    system = open(os.path.join(ROOT, 'CONVENTIONS.md'), encoding='utf-8').read()
    doc = open(os.path.join(ROOT, 'prompts/annotate_ayah_combined.md'), encoding='utf-8').read()
    template = re.search(r'## Prompt template\s+```\n(.*?)\n```', doc, re.S).group(1)

    stop, lock = threading.Event(), threading.Lock()
    errors = []
    totals = {'cost': 0.0, 'calls': 0, 'done': 0}

    def annotate(ay):
        if stop.is_set():
            return
        s, a = ay
        key, n = f'{s}:{a}', src.n_words(s, a)
        attempts, hint = [], None
        for attempt in range(1, args.retries + 2):
            prompt = build_prompt(template, src, s, a, hint)
            text, usage, reason, chunks = None, {}, None, None
            try:
                text, usage = call_model(args.model, system, prompt, 0.0 if attempt == 1 else 0.3,
                                         max(4000, min(32000, 60 * n + 2000)),
                                         'off' if attempt == 1 else args.retry_thinking)
                model_chunks = parse_reply(text, key)
                errs, chunks = validate(model_chunks, n)
                if errs:
                    reason = 'Validation failed:\n  - ' + '\n  - '.join(errs)
                    hint = coverage_hint(model_chunks, src, s, a) + errs
            except Exception as exc:  # network, empty reply, cut-off, bad JSON
                reason = explain(exc, text)
                hint = [reason.splitlines()[0], 'return one valid JSON object and nothing else']
            with lock:
                totals['calls'] += 1
                totals['cost'] += usage.get('cost') or 0
            attempts.append({'attempt': attempt, 'reason': reason, 'user_prompt': prompt,
                             'raw_model_text': text, 'usage': usage})
            if not reason:
                break
        if reason:
            stop.set()
            path = os.path.join(fail_dir, f'{s:03d}-{a:03d}-{int(time.time())}.json')
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump({'ayah': key, 'model': args.model, 'attempts': attempts}, fh,
                          ensure_ascii=False, indent=2)
            detail = ''.join(f'\n\nAttempt {x["attempt"]}: {x["reason"]}' for x in attempts)
            with lock:
                errors.append((key, f'Failed {len(attempts)} times.{detail}', os.path.relpath(path, ROOT)))
                print(f'  {key}: FAILED after {len(attempts)} attempts')
            return
        if len(attempts) > 1:  # worth knowing: the model needed help
            with lock, open(os.path.join(run, 'retries.jsonl'), 'a', encoding='utf-8') as fh:
                fh.write(json.dumps({'ayah': key, 'attempts': len(attempts),
                                     'first_error': attempts[0]['reason']}, ensure_ascii=False) + '\n')
        tmp = raw_path(s, a) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:  # a raw file exists only for a fully valid ayah
            json.dump({'key': key, 'model': args.model, 'chunks': chunks, 'raw_model_text': text},
                      fh, ensure_ascii=False, indent=2)
        os.replace(tmp, raw_path(s, a))
        with lock:
            totals['done'] += 1
            note = f' (after {len(attempts) - 1} retr{"y" if len(attempts) == 2 else "ies"})' if len(attempts) > 1 else ''
            print(f'  {key}: ok{note} ({totals["done"]}/{len(todo)})')

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(annotate, todo))

    merge(run, raw_dir, args.model)  # also after a stop, so partial work is usable
    print(f'\nthis run: {totals["done"]} ayahs, {totals["calls"]} calls, ${totals["cost"]:.4f}')
    if errors:
        done = sum(os.path.exists(raw_path(*ay)) for ay in items)
        with open(stopped_md, 'w', encoding='utf-8') as fh:
            fh.write(f'# STOPPED: {args.tag}\n\nFinished {done}/{len(items)} ayahs. '
                     f'Nothing after the failure was started.\n\n')
            for key, reason, path in errors:
                fh.write(f'## {key}\n\n{reason}\n\nFull prompts and replies: `{path}`\n\n')
            fh.write('## To continue\n\nFix the cause, then run the exact same command again. '
                     'Finished ayahs are skipped.\n')
        print(f'\nSTOPPED. Details: runs/{args.tag}/STOPPED.md')
        for key, reason, path in errors:
            print(f'\n[{key}] {reason}\n  file: {path}')
        sys.exit(1)
    print(f'ALL DONE: {len(items)}/{len(items)} ayahs -> runs/{args.tag}/annotations/')


if __name__ == '__main__':
    main()
