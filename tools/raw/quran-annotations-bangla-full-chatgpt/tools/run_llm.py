#!/usr/bin/env python3
"""Run flat Arabic phrase-chunk annotation through OpenRouter.

Offline smoke test:
  python3 tools/run_llm.py --surah 67 --tag smoke_chunks --mock-replay

Live run:
  export OPENROUTER_API_KEY=sk-or-...
  python3 tools/run_llm.py --ayahs 67:1-3 --tag pilot_chunks

The model returns one flat list of {words,en,bn} chunks per ayah. Source word positions
are validated directly; exact Arabic spelling is reconstructed from the source text.
No clause segmentation or clause-size scoring is performed.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time
import uuid
import threading
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, Src, ayah_block, load_json, meaning_flags, normalise, parse_json_object  # noqa: E402

API = 'https://openrouter.ai/api/v1/chat/completions'
FULL_QURAN_WORDS = 77432
_warned = set()


def parse_spec(lines, src):
    """Parse '67', '2:255', '2:255-260', and # comments into ordered ayahs."""
    out, seen = [], set()
    for ln in lines:
        ln = ln.split('#')[0].strip()
        if not ln:
            continue
        if ':' not in ln:
            items = [(int(ln), a) for a in src.ayahs(int(ln))]
        else:
            s, rest = ln.split(':', 1)
            lo, _, hi = rest.partition('-')
            items = [(int(s), a) for a in range(int(lo), int(hi or lo) + 1)]
        for it in items:
            if it not in seen and it in src.maxkey:
                seen.add(it)
                out.append(it)
    return out


def make_batches(items, src, max_words, max_ayahs):
    batches, cur, words = [], [], 0
    for s, a in items:
        n = src.n_words(s, a)
        consecutive = cur and cur[-1][0] == s and cur[-1][1] == a - 1
        if cur and (not consecutive or words + n > max_words or len(cur) >= max_ayahs):
            batches.append(cur)
            cur, words = [], 0
        cur.append((s, a))
        words += n
    if cur:
        batches.append(cur)
    return batches


def load_template():
    path = os.path.join(ROOT, 'prompts/annotate_ayah_combined.md')
    txt = open(path, encoding='utf-8').read()
    match = re.search(r'## Prompt template\s+```\n(.*?)\n```', txt, re.S)
    if not match:
        raise RuntimeError(f'prompt template not found in {path}')
    return match.group(1)


def build_user_prompt(template, src, batch, bn_wbw=True, hint=None):
    blocks = [ayah_block(src, s, a, bn_wbw, prev_context=(i == 0))
              for i, (s, a) in enumerate(batch)]
    keys = ', '.join(f'{s}:{a}' for s, a in batch)
    prompt = template.replace('{AYAH_BLOCKS}', '\n\n'.join(blocks)).replace('{KEYS}', keys)
    if hint:
        prompt += ('\n\nReview note from the validator: ' + '; '.join(hint[:5]) +
                   '. Reconsider only the affected chunk boundaries and preserve all Arabic words exactly once.')
    return prompt


# --------------------------------------------------------------- chunk granularity

def granularity(chunks):
    n_words = sum(len(c['words']) for c in chunks)
    n_chunks = len(chunks)
    mean = n_words / n_chunks if n_chunks else 0.0
    sizes = [len(c['words']) for c in chunks]
    return n_words, n_chunks, mean, sizes


def granularity_score(chunks, review_chunk_words):
    """Lower is finer without rewarding arbitrary clause splitting (there are no clauses)."""
    _, _, mean, sizes = granularity(chunks)
    over = [n for n in sizes if n > review_chunk_words]
    excess = sum(n - review_chunk_words for n in over)
    return (len(over), excess, round(mean, 5))


def assess(chunks, mean_limit, review_chunk_words):
    n_words, n_chunks, mean, sizes = granularity(chunks)
    reasons = []
    if mean > mean_limit:
        reasons.append('mean_chunk_size')
    if any(n > review_chunk_words for n in sizes):
        reasons.append('large_chunk')
    return reasons, mean


def coarse_hint(chunks, reasons, review_chunk_words):
    if not reasons:
        return []
    n_words, n_chunks, mean, sizes = granularity(chunks)
    big = sorted(chunks, key=lambda c: -len(c['words']))[:4]
    examples = '; '.join(
        f'"{c["en"]}" spans {len(c["words"])} Arabic words ({c["words"][0]}-{c["words"][-1]})'
        for c in big if len(c['words']) > 2
    )
    return [
        f'the earlier output averaged {mean:.2f} Arabic words across {n_chunks} chunks for {n_words} words',
        f'review larger spans (especially those above {review_chunk_words} words) and split only where Arabic syntax '
        f'or local meaning allows; keep required grammatical dependencies intact',
        f'current larger chunks: {examples}' if examples else 'inspect the whole segmentation for unnecessarily merged spans',
        'do not create clause groups and do not split a word internally; exact coverage and Arabic order are mandatory',
    ]


# ------------------------------------------------------------------ model call

def auto_budget(words):
    """Output-token cap (~60 tokens per source word plus headroom)."""
    return max(4000, min(32000, 60 * words + 2000))


def reasoning_param(mode):
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


def call_openrouter(args, system, user, temperature, model=None, max_tokens=None, reasoning='off'):
    model = model or args.model
    system_block = {'type': 'text', 'text': system}
    # OpenRouter's explicit cache_control marker is documented for Anthropic;
    # OpenAI models such as GPT-6 Luna use provider-managed automatic caching.
    if not args.no_cache and model.startswith('anthropic/'):
        system_block['cache_control'] = {'type': 'ephemeral'}
    body = {
        'model': model,
        'temperature': temperature,
        'max_tokens': max_tokens or args.max_tokens,
        'usage': {'include': True},
        'messages': [
            {'role': 'system', 'content': [system_block]},
            {'role': 'user', 'content': user},
        ],
    }
    rp = reasoning_param(reasoning)
    if rp:
        body['reasoning'] = rp
    last = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(
                API, data=json.dumps(body).encode('utf-8'),
                headers={'Authorization': f'Bearer {os.environ["OPENROUTER_API_KEY"]}',
                         'Content-Type': 'application/json', 'X-Title': 'quran-phrase-chunks'},
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                resp = json.loads(response.read().decode('utf-8'))
            if 'error' in resp:
                raise RuntimeError(json.dumps(resp['error'])[:400])
            choice = resp['choices'][0]
            message = choice.get('message') or {}
            content = message.get('content')
            finish = choice.get('finish_reason')
            if not content or not str(content).strip():
                raise RuntimeError(f'empty reply (finish_reason={finish})')
            if finish == 'length':
                raise RuntimeError('reply cut off (finish_reason=length); raise --max-tokens / --long-max-tokens')
            usage = dict(resp.get('usage', {}), finish_reason=finish)
            return content, usage, resp
        except urllib.error.HTTPError as exc:
            last = f'HTTP {exc.code}: {exc.read().decode("utf-8", "replace")[:400]}'
            if exc.code == 400 and 'reasoning' in body:
                body.pop('reasoning')
                if model not in _warned:
                    _warned.add(model)
                    print(f'  warning: {model} rejected the reasoning setting; retrying without it')
                continue
            if exc.code not in (408, 429, 500, 502, 503, 504):
                break
        except Exception as exc:
            last = repr(exc)
        time.sleep(2 ** attempt)
    raise RuntimeError(f'OpenRouter call failed: {last}')


def _prototype_chunks(s, a, src):
    """Flatten the bundled old prototype for the offline smoke test."""
    en_doc = load_json(os.path.join(ROOT, 'annotations/surah-067.json'))
    bn_doc = load_json(os.path.join(ROOT, 'annotations/bn/surah-067.json'))
    entry = en_doc['ayahs'][str(a)]
    bn_entry = bn_doc['ayahs'][str(a)]
    if 'chunks' in entry:
        en_chunks = entry['chunks']
    else:
        en_chunks = [p for cl in entry['clauses'] for p in cl['phrases']]
    if 'chunks' in bn_entry:
        bn_chunks = bn_entry['chunks']
    else:
        bn_chunks = [p for cl in bn_entry['clauses'] for p in cl['phrases']]
    if len(en_chunks) != len(bn_chunks):
        raise RuntimeError(f'prototype English/Bangla chunk count differs for {s}:{a}')
    source = src.words(s, a)
    out = []
    for en, bn in zip(en_chunks, bn_chunks):
        positions = en['words']
        out.append({'words': positions, 'en': en['en'], 'bn': bn['bn']})
    return out


def mock_call(batch, src, coarse=False):
    out = {}
    for s, a in batch:
        assert s == 67, 'mock replay only contains the bundled Surah 67 sample'
        chunks = _prototype_chunks(s, a, src)
        if coarse:
            chunks = [{'words': [1, src.n_words(s, a)],
                       'en': ' '.join(c['en'] for c in chunks),
                       'bn': ' '.join(c['bn'] for c in chunks)}]
        out[f'{s}:{a}'] = chunks
    return json.dumps(out, ensure_ascii=False), {'prompt_tokens': 0, 'completion_tokens': 0, 'cost': 0}


# -------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tag', required=True, help='run name -> runs/<tag>/')
    ap.add_argument('--pilot', help='spec file: lines like "67", "2:255", "2:282-286", # comments')
    ap.add_argument('--surah', type=int, action='append')
    ap.add_argument('--ayahs', help='comma list, e.g. "2:255,2:282-284"')
    ap.add_argument('--model', default='openai/gpt-6-luna', help='OpenRouter model for all ayahs (default: openai/gpt-6-luna)')
    ap.add_argument('--long-model', default='',
                    help='optional separate model for ayahs longer than --long-words (empty = use --model for every length)')
    ap.add_argument('--long-words', type=int, default=40)
    ap.add_argument('--escalate-model', default='',
                    help='optional model for flagged ayahs (empty = disable additional model calls)')
    ap.add_argument('--max-words', type=int, default=220, help='source-word cap per batched request')
    ap.add_argument('--max-ayahs', type=int, default=8)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--max-phrase-words', type=int, default=0,
                    help='strictly reject chunks above this word count (0 = no hard limit; recommended)')
    ap.add_argument('--review-chunk-words', type=int, default=4,
                    help='soft review threshold for unusually large chunks (not a hard split rule)')
    ap.add_argument('--retries', type=int, default=2, help='single-ayah retries for failed validation')
    ap.add_argument('--max-tokens', type=int, default=0, help='output cap per request (0 = automatic)')
    ap.add_argument('--long-max-tokens', type=int, default=0, help='output cap for long ayahs (0 = automatic)')
    ap.add_argument('--mock-flaky', action='store_true', help='self-test: make some mock requests fail once')
    ap.add_argument('--mock-invalid-once', action='store_true', help='self-test: return one structurally invalid mock reply, then a valid retry')
    ap.add_argument('--no-bn-wbw', action='store_true', help='omit Bangla word glosses from the prompt')
    ap.add_argument('--no-cache', action='store_true', help='do not mark conventions as cacheable')
    ap.add_argument('--reasoning', default='off', help='normal pass: off|none|minimal|low|medium|high|default|max:N')
    ap.add_argument('--long-reasoning', default='low', help='long ayahs (same values)')
    ap.add_argument('--escalate-reasoning', default='low', help='escalation (same values)')
    ap.add_argument('--out-dir', help='annotation directory (default runs/<tag>/annotations)')
    ap.add_argument('--no-merge', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--coarse-mean', type=float, default=2.0,
                    help='soft mean words/chunk threshold that triggers a finer review pass')
    ap.add_argument('--coarse-retries', type=int, default=1, help='one chunk-granularity refinement pass; 0 disables')
    ap.add_argument('--mock-coarse', action='store_true', help='self-test: make mock answer one coarse chunk per ayah')
    ap.add_argument('--mock-replay', action='store_true', help='offline test using the bundled Surah 67 prototype')
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
    if args.review_chunk_words < 2 or args.coarse_mean <= 0:
        sys.exit('--review-chunk-words must be >=2 and --coarse-mean must be positive')

    run = os.path.join(ROOT, 'runs', args.tag)
    raw_dir = os.path.join(run, 'raw')
    out_dir = os.path.abspath(args.out_dir or os.path.join(run, 'annotations'))
    os.makedirs(raw_dir, exist_ok=True)

    def raw_path(s, a):
        return os.path.join(raw_dir, f'{s:03d}-{a:03d}.json')

    attempts_dir = os.path.join(run, 'attempts')
    os.makedirs(attempts_dir, exist_ok=True)
    retry_events_path = os.path.join(run, 'retry_events.jsonl')
    log_lock = threading.Lock()
    retry_lock = threading.Lock()
    pending_retry_events = {}
    retry_attempt_counts = {}

    def persist_attempt(record):
        attempt_id = record.setdefault('attempt_id', uuid.uuid4().hex)
        record.setdefault('recorded_at_unix', time.time())
        path = os.path.join(attempts_dir, f'{attempt_id}.json')
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(record, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return attempt_id, os.path.relpath(path, run)

    def append_call_log(record):
        with log_lock:
            log.write(json.dumps(record, ensure_ascii=False) + '\n')
            log.flush()

    def append_retry_event(record):
        with retry_lock:
            with open(retry_events_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + '\n')
                fh.flush()

    def mark_invalid(key, attempt_id, attempt_path, errors, attempt_number, category):
        event_id = uuid.uuid4().hex
        raw_available = False
        if attempt_path:
            try:
                saved = load_json(os.path.join(run, attempt_path))
                raw_available = bool(saved.get('response_captured') and saved.get('raw_model_text'))
            except Exception:
                raw_available = False
        event = {
            'event_id': event_id,
            'event': 'invalid_model_response',
            'ayah': key,
            'attempt_id': attempt_id,
            'attempt_file': attempt_path,
            'attempt_number': attempt_number,
            'category': category,
            'validation_errors': errors,
            'resolved': False,
            'raw_model_response_available': raw_available,
            'note': 'The complete request and any returned raw model response are stored in the referenced attempts file.'
        }
        append_retry_event(event)
        pending_retry_events.setdefault(key, []).append(event)

    def resolve_invalid(key, resolving_attempt_id, resolving_attempt_file, attempt_number):
        events = pending_retry_events.pop(key, [])
        for original in events:
            append_retry_event({
                'event_id': uuid.uuid4().hex,
                'event': 'invalid_response_resolved_by_retry',
                'ayah': key,
                'original_event_id': original['event_id'],
                'original_attempt_id': original['attempt_id'],
                'resolving_attempt_id': resolving_attempt_id,
                'resolving_attempt_file': resolving_attempt_file,
                'resolved_on_retry_number': attempt_number,
                'status': 'resolved',
                'validation_errors': original['validation_errors'],
                'raw_original_response_available': original.get('raw_model_response_available', False),
                'raw_resolution_response_available': True,
            })

    todo = [(s, a) for s, a in items if not os.path.exists(raw_path(s, a))]
    words_total = sum(src.n_words(s, a) for s, a in items)
    print(f'{len(items)} ayahs / {words_total} words selected; {len(items) - len(todo)} already done, {len(todo)} to run')

    system = open(os.path.join(ROOT, 'CONVENTIONS.md'), encoding='utf-8').read()
    template = load_template()
    long_set = {ay for ay in todo if args.long_model and src.n_words(*ay) > args.long_words}
    long_items = sorted(long_set)
    regular_items = [ay for ay in todo if ay not in long_set]
    batches = make_batches(regular_items, src, args.max_words, args.max_ayahs)
    if long_items:
        print(f'{len(long_items)} long ayah(s) (> {args.long_words} words) will run individually via {args.long_model}')
    if args.dry_run:
        if batches:
            user_prompt = build_user_prompt(template, src, batches[0], not args.no_bn_wbw)
            print(f'--- {len(batches)} batched request(s) + {len(long_items)} individual long ayah(s); '
                  f'first user prompt ({len(user_prompt)} chars; system {len(system)} chars) ---\n{user_prompt}')
        elif long_items:
            user_prompt = build_user_prompt(template, src, [long_items[0]], not args.no_bn_wbw)
            print(f'--- first long-ayah prompt ({len(user_prompt)} chars; system {len(system)} chars) ---\n{user_prompt}')
        return
    if not args.mock_replay and not os.environ.get('OPENROUTER_API_KEY'):
        sys.exit('set OPENROUTER_API_KEY first (export OPENROUTER_API_KEY=...)')

    log = open(os.path.join(run, 'calls.jsonl'), 'a', encoding='utf-8')
    usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'cost': 0.0, 'calls': 0, 'words': 0}
    by_cat = {}
    mock_invalid_seen = set()

    def run_request(batch, temperature, hint=None, model=None, cat='main'):
        model = model or args.model
        user = build_user_prompt(template, src, batch, not args.no_bn_wbw, hint)
        attempt_id = uuid.uuid4().hex
        started = time.time()
        words = sum(src.n_words(*ay) for ay in batch)
        reasoning = {'long': args.long_reasoning, 'escalate': args.escalate_reasoning}.get(cat, args.reasoning)
        budget = (args.long_max_tokens if cat == 'long' else args.max_tokens) or auto_budget(words)
        attempt = {
            'attempt_id': attempt_id,
            'kind': 'annotation',
            'keys': [f'{s}:{a}' for s, a in batch],
            'model': model,
            'category': cat,
            'temperature': temperature,
            'reasoning': reasoning,
            'started_at_unix': started,
            'request': {
                'endpoint': API,
                'max_tokens': budget,
                'system_prompt': system,
                'user_prompt': user,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
            },
        }
        try:
            if args.mock_replay:
                if args.mock_flaky and temperature == 0.0 and any(a % 5 == 0 for s, a in batch):
                    raise RuntimeError('mock transient failure')
                text, u = mock_call(batch, src, args.mock_coarse)
                provider_response = {'mock': True}
                if args.mock_invalid_once and temperature == 0.0:
                    mock_key = f'{batch[0][0]}:{batch[0][1]}'
                    if mock_key not in mock_invalid_seen:
                        mock_invalid_seen.add(mock_key)
                        malformed = parse_json_object(text)
                        first = malformed[mock_key][0]
                        first['words'] = [2]
                        text = json.dumps(malformed, ensure_ascii=False)
            else:
                text, u, provider_response = call_openrouter(
                    args, system, user, temperature, model, budget, reasoning
                )
            attempt.update({
                'duration_seconds': round(time.time() - started, 2),
                'usage': u,
                'raw_model_text': text,
                'provider_response': provider_response,
                'response_captured': True,
            })
            try:
                parsed = parse_json_object(text, [f'{s}:{a}' for s, a in batch])
                attempt['parse_status'] = 'valid_json_object'
            except Exception as parse_exc:
                attempt['parse_status'] = 'invalid'
                attempt['parse_error'] = repr(parse_exc)
                raise
            attempt_id_saved, attempt_file = persist_attempt(attempt)
            rec = {
                'attempt_id': attempt_id_saved, 'attempt_file': attempt_file,
                'keys': attempt['keys'], 'model': model, 'temperature': temperature,
                'category': cat, 'hint': hint, 'seconds': attempt['duration_seconds'],
                'usage': u, 'reply_available_in_attempt_file': True,
            }
            append_call_log(rec)
        except Exception as exc:
            attempt.setdefault('duration_seconds', round(time.time() - started, 2))
            attempt['error'] = str(exc)
            attempt.setdefault('response_captured', False)
            attempt_id_saved, attempt_file = persist_attempt(attempt)
            append_call_log({
                'attempt_id': attempt_id_saved, 'attempt_file': attempt_file,
                'keys': attempt['keys'], 'model': model, 'temperature': temperature,
                'category': cat, 'seconds': attempt['duration_seconds'], 'error': str(exc),
            })
            setattr(exc, 'attempt_id', attempt_id_saved)
            setattr(exc, 'attempt_file', attempt_file)
            raise

        cat_stats = by_cat.setdefault(cat, {'calls': 0, 'cost': 0.0, 'in': 0, 'out': 0, 'reason': 0})
        cat_stats['calls'] += 1
        cat_stats['cost'] += u.get('cost') or 0
        cat_stats['in'] += u.get('prompt_tokens', 0)
        cat_stats['out'] += u.get('completion_tokens', 0)
        cat_stats['reason'] += (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0
        usage['prompt_tokens'] += u.get('prompt_tokens', 0)
        usage['completion_tokens'] += u.get('completion_tokens', 0)
        usage['cost'] += u.get('cost') or 0
        usage['calls'] += 1
        return parsed, attempt_id_saved, attempt_file

    def repair_missing_bn(s, a, chunks, model, cat):
        """Fill only blank Bangla fragments; the model is forbidden to alter chunk spans."""
        from ayahlib import expand_words, register_line
        key = f'{s}:{a}'
        missing = []
        src_words = src.words(s, a)
        def valid_bn(value):
            if not isinstance(value, str) or not value.strip():
                return False
            has_bn = any('\u0980' <= ch <= '\u09FF' for ch in value)
            has_ar = any(('\u0600' <= ch <= '\u06FF' or '\u0750' <= ch <= '\u077F'
                          or '\u08A0' <= ch <= '\u08FF' or '\uFB50' <= ch <= '\uFDFF'
                          or '\uFE70' <= ch <= '\uFEFF') for ch in value)
            return has_bn and not has_ar

        for idx, chunk in enumerate(chunks, 1):
            if not isinstance(chunk, dict) or valid_bn(chunk.get('bn')):
                continue
            try:
                positions = expand_words(chunk.get('words'))
            except Exception:
                # Legacy `ar`-based replies are handled by normal validation/retry.
                continue
            span_lines = [f'{w}. {ar} — Bangla gloss: {gb}' for w, ar, ge, gb in src_words
                          if w in positions]
            missing.append((idx, positions, chunk.get('en', ''), span_lines))
        if not missing or args.mock_replay:
            return

        ayah_text = '\n'.join(f'{w}. {ar} — {ge} — {gb}' for w, ar, ge, gb in src_words)
        register = register_line(src.tr_bn[f'{s}:{a}']) or 'Follow the natural register of the supplied Bangla reference.'
        requested = []
        for idx, positions, en, span_lines in missing:
            requested.append(
                f'chunk {idx}, source positions {positions[0]}-{positions[-1]} (inclusive)\n'
                f'English fragment: {en}\n' + '\n'.join(span_lines)
            )
        user = (
            f'Fill ONLY the missing Bangla translation fragments for Quran ayah {key}.\n'
            'Chunk boundaries and English fragments are already fixed. Do not segment, merge, '
            'split, or reorder anything. Return a JSON object with this exact shape: '
            f'{{"{key}": {{"<chunk-index>": "Bangla fragment"}}}}. Include every requested '
            'chunk index exactly once. Use Bangla script only, no Arabic script or romanisation. '
            'Each fragment must translate only its own numbered Arabic source span.\n\n'
            f'Complete numbered ayah words:\n{ayah_text}\n\n{register}\n\n'
            'Missing fragments to fill:\n' + '\n\n'.join(requested)
        )
        started = time.time()
        repair_id = uuid.uuid4().hex
        repair_system = ('You are a precise Quranic Bangla translation assistant. Translate only the given '
                         'source spans. Use আল্লাহ / রব / ইলাহ according to the Arabic; never use ঈশ্বর, '
                         'প্রভু, or খোদা. Return valid JSON only.')
        rec = {'attempt_id': repair_id, 'kind': 'bangla_translation_repair', 'keys': [key],
               'model': model or args.model, 'category': 'bn_repair',
               'missing_chunks': [x[0] for x in missing],
               'request': {'system_prompt': repair_system, 'user_prompt': user}}
        try:
            text, u, provider_response = call_openrouter(
                args, repair_system, user, 0.0, model or args.model,
                max(1200, min(6000, 500 * len(missing))), 'off'
            )
            parsed = parse_json_object(text)
            translations = parsed.get(key, {}) if isinstance(parsed, dict) else {}
            if not isinstance(translations, dict):
                raise ValueError('Bangla repair response must map chunk indices to strings')
            for idx, _, _, _ in missing:
                value = translations.get(str(idx), translations.get(idx))
                if isinstance(value, str) and value.strip():
                    chunks[idx - 1]['bn'] = value.strip()
            rec.update(duration_seconds=round(time.time() - started, 2), usage=u,
                       raw_model_text=text, provider_response=provider_response,
                       response_captured=True, parse_status='valid_json_object')
            attempt_id_saved, attempt_file = persist_attempt(rec)
            cat_stats = by_cat.setdefault('bn_repair', {'calls': 0, 'cost': 0.0, 'in': 0, 'out': 0, 'reason': 0})
            cat_stats['calls'] += 1
            cat_stats['cost'] += u.get('cost') or 0
            cat_stats['in'] += u.get('prompt_tokens', 0)
            cat_stats['out'] += u.get('completion_tokens', 0)
            cat_stats['reason'] += (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0
            usage['prompt_tokens'] += u.get('prompt_tokens', 0)
            usage['completion_tokens'] += u.get('completion_tokens', 0)
            usage['cost'] += u.get('cost') or 0
            usage['calls'] += 1
            append_call_log({'attempt_id': attempt_id_saved, 'attempt_file': attempt_file,
                             'keys': [key], 'model': model or args.model, 'category': 'bn_repair',
                             'missing_chunks': [x[0] for x in missing], 'usage': u})
        except Exception as exc:
            rec.update(duration_seconds=round(time.time() - started, 2), error=str(exc),
                       response_captured=bool('text' in locals()))
            if 'text' in locals():
                rec['raw_model_text'] = text
            attempt_id_saved, attempt_file = persist_attempt(rec)
            append_call_log({'attempt_id': attempt_id_saved, 'attempt_file': attempt_file,
                             'keys': [key], 'model': model or args.model, 'category': 'bn_repair',
                             'error': str(exc)})
            print(f'  {key}: Bangla-only repair failed: {exc}')

    def settle(batch, temperature, hint=None, model=None, cat='main', retry_number=0):
        failed = []
        try:
            reply, attempt_id, attempt_file = run_request(batch, temperature, hint, model, cat)
        except Exception as exc:
            attempt_id = getattr(exc, 'attempt_id', None)
            attempt_file = getattr(exc, 'attempt_file', None)
            print(f'  request {batch[0]}..{batch[-1]} failed: {exc}')
            msg = f'reply could not be used ({str(exc)[:140]})'
            if isinstance(exc, json.JSONDecodeError) or 'JSON' in str(exc):
                msg += '; return one valid JSON object with a flat list of {words,en,bn} objects per ayah'
            for ay in batch:
                key = f'{ay[0]}:{ay[1]}'
                mark_invalid(key, attempt_id, attempt_file, [msg], retry_number, cat)
                failed.append((ay, [msg]))
            return failed
        for s, a in batch:
            key = f'{s}:{a}'
            if key in reply and isinstance(reply.get(key), list):
                repair_missing_bn(s, a, reply[key], model or args.model, cat)
            errs, chunks = (normalise(reply.get(key), src.n_words(s, a),
                                      max_phrase_words=args.max_phrase_words,
                                      src_words=src.align_words(s, a))
                            if key in reply else (['missing from reply'], []))
            if errs:
                print(f'  {key}: invalid ({errs[0]}{" ..." if len(errs) > 1 else ""})')
                mark_invalid(key, attempt_id, attempt_file, errs, retry_number, cat)
                failed.append(((s, a), errs))
                continue
            resolve_invalid(key, attempt_id, attempt_file, retry_number)
            reasons, mean = assess(chunks, args.coarse_mean, args.review_chunk_words)
            source_words = src.source_trace(s, a)
            source_arabic = ' '.join(w['arabic'] for w in source_words)
            refs = src.ayah_references(s, a)
            with open(raw_path(s, a), 'w', encoding='utf-8') as fh:
                json.dump({
                    'key': key, 'model': model or args.model,
                    'final_attempt_id': attempt_id, 'final_attempt_file': attempt_file,
                    'chunks': chunks, 'mean_words_per_chunk': round(mean, 4),
                    'coarse': bool(reasons), 'reasons': reasons,
                    'refined': False, 'escalated': False,
                    'source': {
                        'surah': s, 'ayah': a, 'word_count': len(source_words),
                        'arabic_ayah': source_arabic, 'words': source_words,
                        'references': refs,
                    },
                }, fh, ensure_ascii=False, indent=2)
            usage['words'] += src.n_words(s, a)
        return failed

    failed = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for i, failures in enumerate(executor.map(lambda b: settle(b, 0.0), batches), 1):
            failed += failures
            print(f'batch {i}/{len(batches)} done ({len(failures)} failed)')
        for failures in executor.map(lambda ay: settle([ay], 0.0, model=args.long_model, cat='long'), long_items):
            failed += failures
        if long_items:
            print(f'individual long ayahs done ({len(long_items)})')
        for attempt in range(args.retries):
            if not failed:
                break
            print(f'retry {attempt + 1}: {len(failed)} ayah(s) alone at temperature 0.3')
            retry_work = failed
            retry_number = attempt + 1
            failed = [item for group in executor.map(
                lambda fe: settle([fe[0]], 0.3, fe[1],
                                  args.long_model if fe[0] in long_set else args.model,
                                  'long' if fe[0] in long_set else 'main', retry_number), retry_work) for item in group]

    def refine(ay):
        s, a = ay
        path = raw_path(s, a)
        data = load_json(path)
        old_chunks = data['chunks']
        old_reasons, _ = assess(old_chunks, args.coarse_mean, args.review_chunk_words)
        try:
            reply, attempt_id, attempt_file = run_request([ay], 0.3,
                                coarse_hint(old_chunks, old_reasons, args.review_chunk_words),
                                args.long_model if ay in long_set else args.model,
                                'long' if ay in long_set else 'main')
            errs, new_chunks = normalise(reply.get(f'{s}:{a}'), src.n_words(s, a),
                                         max_phrase_words=args.max_phrase_words,
                                         src_words=src.align_words(s, a))
        except Exception as exc:
            errs, new_chunks = [str(exc)], []
        better = False
        if not errs:
            better = granularity_score(new_chunks, args.review_chunk_words) < \
                     granularity_score(old_chunks, args.review_chunk_words)
            if better:
                reasons, mean = assess(new_chunks, args.coarse_mean, args.review_chunk_words)
                data.update(chunks=new_chunks, mean_words_per_chunk=round(mean, 4),
                            coarse=bool(reasons), reasons=reasons)
        data['refined'] = True
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return better

    if args.coarse_retries:
        pending = [ay for ay in items if os.path.exists(raw_path(*ay))
                   and load_json(raw_path(*ay)).get('coarse')
                   and not load_json(raw_path(*ay)).get('refined')]
        if pending:
            print(f'chunk review: {len(pending)} ayah(s) have large/coarse chunks; requesting one finer pass')
            with cf.ThreadPoolExecutor(max_workers=args.workers) as executor:
                gained = sum(executor.map(refine, pending))
            print(f'chunk review: {gained}/{len(pending)} improved under the size heuristic')

    def flags_for(s, a, chunks):
        gloss = {w: ge for w, ar, ge, gb in src.words(s, a)}
        return meaning_flags(gloss, chunks)

    def escalate(ay):
        s, a = ay
        path = raw_path(s, a)
        data = load_json(path)
        old_chunks = data['chunks']
        old_reasons, _ = assess(old_chunks, args.coarse_mean, args.review_chunk_words)
        old_flags = flags_for(s, a, old_chunks)
        hint = coarse_hint(old_chunks, old_reasons, args.review_chunk_words) if old_reasons else []
        if old_flags:
            hint.append('possible moved/dropped/doubled gloss meaning: ' + '; '.join(old_flags[:4]) +
                        '. Each chunk must translate only its own Arabic words.')
        try:
            reply, attempt_id, attempt_file = run_request([ay], 0.0, hint, args.escalate_model, 'escalate')
            errs, new_chunks = normalise(reply.get(f'{s}:{a}'), src.n_words(s, a),
                                         max_phrase_words=args.max_phrase_words,
                                         src_words=src.align_words(s, a))
        except Exception as exc:
            errs, new_chunks = [str(exc)], []
        better = False
        if not errs:
            new_flags = flags_for(s, a, new_chunks)
            old_score = (len(old_flags),) + granularity_score(old_chunks, args.review_chunk_words)
            new_score = (len(new_flags),) + granularity_score(new_chunks, args.review_chunk_words)
            better = new_score < old_score
            if better:
                reasons, mean = assess(new_chunks, args.coarse_mean, args.review_chunk_words)
                data.update(chunks=new_chunks, mean_words_per_chunk=round(mean, 4),
                            coarse=bool(reasons), reasons=reasons, model=args.escalate_model)
        data['escalated'] = True
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return better

    if args.escalate_model:
        pending = []
        for ay in items:
            path = raw_path(*ay)
            if os.path.exists(path):
                data = load_json(path)
                if data.get('coarse') or flags_for(ay[0], ay[1], data['chunks']):
                    pending.append(ay)
        if pending:
            print(f'escalation: {len(pending)} ayah(s) remain flagged; trying {args.escalate_model}')
            with cf.ThreadPoolExecutor(max_workers=args.workers) as executor:
                improved = sum(executor.map(escalate, pending))
            print(f'escalation: {improved}/{len(pending)} improved under the automatic checks')

    left = {}
    for s, a in items:
        path = raw_path(s, a)
        if os.path.exists(path):
            data = load_json(path)
            why = list(data.get('reasons') or []) + flags_for(s, a, data['chunks'])
            if why:
                left[f'{s}:{a}'] = list(dict.fromkeys(why))
    with open(os.path.join(run, 'flags.json'), 'w', encoding='utf-8') as fh:
        json.dump(left, fh, ensure_ascii=False, indent=2)
    if left:
        print(f'{len(left)} ayah(s) flagged for human review (runs/{args.tag}/flags.json)')

    still = [f'{s}:{a}' for s, a in items if os.path.exists(raw_path(s, a))
             and load_json(raw_path(s, a)).get('coarse')]
    with open(os.path.join(run, 'coarse.json'), 'w', encoding='utf-8') as fh:
        json.dump({key: load_json(raw_path(*map(int, key.split(':')))).get('reasons') for key in still},
                  fh, ensure_ascii=False, indent=2)
    if still:
        print(f'{len(still)} ayah(s) still have chunk-size review flags (runs/{args.tag}/coarse.json)')

    for key, events in list(pending_retry_events.items()):
        for event in events:
            append_retry_event({
                'event_id': uuid.uuid4().hex,
                'event': 'invalid_response_unresolved',
                'ayah': key,
                'original_event_id': event['event_id'],
                'original_attempt_id': event['attempt_id'],
                'status': 'unresolved_after_configured_retries',
                'validation_errors': event['validation_errors'],
                'raw_original_response_available': bool(event.get('attempt_file')),
            })
    log.close()
    done = [(s, a) for s, a in items if os.path.exists(raw_path(s, a))]
    failed_keys = {f'{s}:{a}': reasons for (s, a), reasons in failed}
    with open(os.path.join(run, 'failed.json'), 'w', encoding='utf-8') as fh:
        json.dump(failed_keys, fh, ensure_ascii=False, indent=2)
    print(f'\nvalidated {len(done)}/{len(items)} ayahs; failed {len(failed)} (runs/{args.tag}/failed.json)')
    if usage['calls']:
        print(f'this run: {usage["calls"]} calls, {usage["prompt_tokens"]:,} input / '
              f'{usage["completion_tokens"]:,} output tokens, reported cost ${usage["cost"]:.4f}')
        for category, stat in sorted(by_cat.items()):
            reasoning_share = stat['reason'] / stat['out'] if stat['out'] else 0
            print(f'  {category:9s} {stat["calls"]:4d} calls {stat["in"]:>9,} in {stat["out"]:>8,} out '
                  f'(reasoning {stat["reason"]:,} = {reasoning_share:.0%}) ${stat["cost"]:.4f}')
        # Rough whole-Quran projection from the observed API cost per source word.
        long_keys = [key for key in src.maxkey if args.long_model and src.n_words(*key) > args.long_words]
        long_words = sum(src.n_words(*key) for key in long_keys)
        regular_words = FULL_QURAN_WORDS - long_words
        estimate_parts = []
        if by_cat.get('main') and regular_words:
            words_run = sum(src.n_words(*ay) for ay in done if ay not in long_set)
            if words_run:
                estimate_parts.append(('regular ayahs', by_cat['main']['cost'] / words_run * regular_words))
        if by_cat.get('long') and long_words:
            words_run = sum(src.n_words(*ay) for ay in done if ay in long_set)
            if words_run:
                estimate_parts.append(('long ayahs', by_cat['long']['cost'] / words_run * long_words))
        if estimate_parts:
            print('rough whole-Quran estimate from this run:')
            for name, cost in estimate_parts:
                print(f'  {name:20s} ~${cost:,.2f}')
            print(f'  {"total":20s} ~${sum(v for _, v in estimate_parts):,.2f}')

    if args.no_merge or not done:
        return
    by_surah = {}
    for s, a in done:
        data = load_json(raw_path(s, a))
        by_surah.setdefault(s, {})[f'{s}:{a}'] = data['chunks']
    for s, data in sorted(by_surah.items()):
        merge_file = os.path.join(run, f'merge-{s:03d}.json')
        with open(merge_file, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)
        models = sorted({load_json(raw_path(s, int(key.split(':')[1])))['model'] for key in data})
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools/collect.py'), '--surah', str(s),
                        '--file', merge_file, '--out-dir', out_dir, '--model', ' + '.join(models)], check=True)


if __name__ == '__main__':
    main()
