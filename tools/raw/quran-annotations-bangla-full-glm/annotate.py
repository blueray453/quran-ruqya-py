#!/usr/bin/env python3
"""Annotate ayahs, one request per ayah. Simple on purpose.

    python3 tools/annotate.py --tag haiku_smoke --pilot runs/haiku_smoke/pilot.txt
    python3 tools/annotate.py --tag haiku_smoke --pilot runs/haiku_smoke/pilot.txt   # rerun = resume

For each ayah that has no runs/<tag>/raw/SSS-AAA.json yet:
  call model -> parse JSON -> validate (tiling, Bangla, terminology) -> write raw file.

On the FIRST error it stops, writes runs/<tag>/STOPPED.md (what failed, the exact bad
line, the model's reply, and the files to look at) and exits 1. Finished ayahs are
never redone, so after you fix the cause just run the same command again.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ayahlib  # noqa: E402
from ayahlib import ROOT, Src, load_json, normalise, parse_json_object  # noqa: E402
import run_llm  # noqa: E402  (reuses the API call, prompt builder and spec parser)


def describe(exc, text):
    """Plain-English reason + the exact offending line when the reply is broken JSON."""
    if isinstance(exc, json.JSONDecodeError) and text:
        # parse_json_object works on the first '{'; report against the cleaned text
        lines = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip()).splitlines()
        i = exc.lineno - 1
        bad = lines[i] if 0 <= i < len(lines) else ''
        caret = ' ' * max(exc.colno - 1, 0) + '^'
        return (f'Model reply is not valid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}.\n'
                f'    {bad}\n    {caret}')
    return str(exc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--pilot', help='file with lines like "67", "2:255", "2:282-286"')
    ap.add_argument('--surah', type=int, action='append')
    ap.add_argument('--ayahs', help='e.g. "2:255,2:282-284"')
    ap.add_argument('--model', default=os.environ.get('MODEL', 'anthropic/claude-haiku-5.5'))
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--temperature', type=float, default=0.0)
    args = ap.parse_args()
    # fields call_openrouter() expects
    args.no_cache, args.max_tokens = False, 0

    if not os.environ.get('OPENROUTER_API_KEY'):
        sys.exit('set OPENROUTER_API_KEY first')

    src = Src()
    spec = []
    if args.pilot:
        spec += open(args.pilot, encoding='utf-8').read().splitlines()
    spec += [str(s) for s in (args.surah or [])]
    if args.ayahs:
        spec += args.ayahs.split(',')
    items = run_llm.parse_spec(spec, src)
    if not items:
        sys.exit('nothing to do: give --pilot / --surah / --ayahs')

    run = os.path.join(ROOT, 'runs', args.tag)
    raw_dir = os.path.join(run, 'raw')
    fail_dir = os.path.join(run, 'failures')
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(fail_dir, exist_ok=True)
    stopped_md = os.path.join(run, 'STOPPED.md')
    if os.path.exists(stopped_md):
        os.remove(stopped_md)  # a new run starts clean; it is rewritten if we stop again

    def raw_path(s, a):
        return os.path.join(raw_dir, f'{s:03d}-{a:03d}.json')

    todo = [ay for ay in items if not os.path.exists(raw_path(*ay))]
    print(f'{len(items)} ayahs selected, {len(items) - len(todo)} already done, {len(todo)} to run '
          f'(model {args.model})')

    system = open(os.path.join(ROOT, 'CONVENTIONS.md'), encoding='utf-8').read()
    template = run_llm.load_template()
    stop = threading.Event()
    lock = threading.Lock()
    errors = []        # (key, reason, failure_file)
    totals = {'cost': 0.0, 'calls': 0, 'done': 0}

    def annotate(ay):
        if stop.is_set():
            return
        s, a = ay
        key = f'{s}:{a}'
        n = src.n_words(s, a)
        prompt = run_llm.build_user_prompt(template, src, [ay])
        text, usage, reason = None, {}, None
        try:
            text, usage, _ = run_llm.call_openrouter(
                args, system, prompt, args.temperature, args.model,
                run_llm.auto_budget(n), 'off')
            reply = parse_json_object(text, [key])
            errs, chunks = normalise(reply.get(key), n, src_words=src.align_words(s, a))
            if errs:
                reason = 'Validation failed:\n  - ' + '\n  - '.join(errs)
        except Exception as exc:  # network, empty reply, cut-off, bad JSON
            reason = describe(exc, text)
        with lock:
            totals['calls'] += 1
            totals['cost'] += usage.get('cost') or 0
        if reason:
            stop.set()
            path = os.path.join(fail_dir, f'{s:03d}-{a:03d}-{int(time.time())}.json')
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump({'ayah': key, 'model': args.model, 'reason': reason,
                           'system_prompt_file': 'CONVENTIONS.md', 'user_prompt': prompt,
                           'raw_model_text': text, 'usage': usage}, fh, ensure_ascii=False, indent=2)
            with lock:
                errors.append((key, reason, os.path.relpath(path, ROOT)))
            print(f'  {key}: FAILED')
            return
        source_words = src.source_trace(s, a)
        tmp = raw_path(s, a) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump({'key': key, 'model': args.model, 'chunks': chunks, 'raw_model_text': text,
                       'source': {'surah': s, 'ayah': a, 'word_count': len(source_words),
                                  'arabic_ayah': ' '.join(w['arabic'] for w in source_words),
                                  'words': source_words, 'references': src.ayah_references(s, a)}},
                      fh, ensure_ascii=False, indent=2)
        os.replace(tmp, raw_path(s, a))  # a raw file exists only if the ayah fully validated
        with lock:
            totals['done'] += 1
            print(f'  {key}: ok ({totals["done"]}/{len(todo)})')

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(annotate, todo))

    # merge everything finished so far (also after a stop, so partial work is usable)
    out_dir = os.path.join(run, 'annotations')
    by_surah = {}
    for s, a in items:
        if os.path.exists(raw_path(s, a)):
            by_surah.setdefault(s, {})[f'{s}:{a}'] = load_json(raw_path(s, a))['chunks']
    for s, data in sorted(by_surah.items()):
        mf = os.path.join(run, f'merge-{s:03d}.json')
        with open(mf, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools/collect.py'), '--surah', str(s),
                        '--file', mf, '--out-dir', out_dir, '--model', args.model],
                       check=True, stdout=subprocess.DEVNULL)

    print(f'\nthis run: {totals["done"]} ayahs done, {totals["calls"]} calls, ${totals["cost"]:.4f}')
    if errors:
        done_total = sum(os.path.exists(raw_path(*ay)) for ay in items)
        with open(stopped_md, 'w', encoding='utf-8') as fh:
            fh.write(f'# STOPPED: {args.tag}\n\n'
                     f'Finished {done_total}/{len(items)} ayahs. Nothing after the failure was started.\n\n')
            for key, reason, path in errors:
                fh.write(f'## {key}\n\n{reason}\n\nFull request + model reply: `{path}`\n\n')
            fh.write('## To continue\n\nFix the cause, then run the exact same command again. '
                     'Finished ayahs are skipped; it resumes at the failed ayah.\n')
        print(f'\nSTOPPED. {len(errors)} error(s). Details: runs/{args.tag}/STOPPED.md')
        for key, reason, path in errors:
            print(f'\n[{key}] {reason}\n  file: {path}')
        print('\nRe-run the same command to resume.')
        sys.exit(1)
    print(f'ALL DONE: {len(items)}/{len(items)} ayahs. Annotations: runs/{args.tag}/annotations/')


if __name__ == '__main__':
    main()
