#!/usr/bin/env python3
"""Compare two or more run directories produced by run_llm.py.

Usage:
  python3 tools/compare_runs.py runs/BASELINE runs/CANDIDATE [runs/THIRD ...]

Reads only the standard run artifacts (calls.jsonl, retry_events.jsonl,
failed.json, flags.json, coarse.json, raw/*.json, attempts/*.json). Missing
files are counted as zero/absent, so partial or aborted runs compare safely.
Metrics are grouped into shape/structure (what qa.py checks) and outcome.
"""
import glob
import json
import os
import sys
from collections import Counter


def load_json(path, default):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return default


def temperature_of(rec):
    if 'temperature' in rec:
        return rec['temperature']
    return (rec.get('sampling') or {}).get('temperature')


def classify(errors):
    text = ' '.join(errors).lower()
    if 'expecting value' in text or 'parse' in text or 'json' in text and 'object' in text:
        return 'parse/json'
    if 'gap/overlap' in text or 'expected' in text:
        return 'boundary'
    if 'missing from reply' in text:
        return 'missing'
    return 'other'


def load_run(path):
    m = {'dir': path}

    calls = []
    with open(os.path.join(path, 'calls.jsonl'), encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                calls.append(json.loads(line))
    m['calls'] = len(calls)
    m['calls_by_cat'] = Counter(r.get('category') or '?' for r in calls)
    m['retried_calls'] = sum(1 for r in calls if r.get('hint'))
    m['temps'] = Counter(str(temperature_of(r)) for r in calls)
    m['models'] = Counter(r.get('model') or '?' for r in calls)

    first_pass, resolved, unresolved = [], 0, 0
    for line in open(os.path.join(path, 'retry_events.jsonl'), encoding='utf-8'):
        ev = json.loads(line)
        kind = ev.get('event')
        if kind == 'invalid_model_response':
            if ev.get('attempt_number') in (0, None):
                first_pass.append((ev.get('ayah'), classify(ev.get('validation_errors') or [])))
        elif kind == 'invalid_response_resolved_by_retry':
            resolved += 1
        elif kind == 'invalid_response_unresolved':
            unresolved += 1
    m['first_pass_invalid'] = first_pass
    m['first_pass_by_type'] = Counter(t for _, t in first_pass)
    m['resolved_by_retry'] = resolved
    m['unresolved'] = unresolved

    m['failed'] = load_json(os.path.join(path, 'failed.json'), {})
    m['review_flags'] = load_json(os.path.join(path, 'flags.json'), {})
    m['coarse_flags'] = load_json(os.path.join(path, 'coarse.json'), {})

    means, sizes = [], []
    for fp in glob.glob(os.path.join(path, 'raw', '*.json')):
        d = load_json(fp, {})
        if 'mean_words_per_chunk' in d and d.get('chunks'):
            means.append(d['mean_words_per_chunk'])
            sizes += [len(c.get('words') or []) for c in d['chunks']]
    m['ayahs'] = len(means)
    m['mean_wpc'] = sum(means) / len(means) if means else 0.0
    m['max_chunk'] = max(sizes) if sizes else 0
    n = len(sizes) or 1
    m['one_word_pct'] = 100.0 * sum(1 for s in sizes if s == 1) / n
    m['over4_pct'] = 100.0 * sum(1 for s in sizes if s > 4) / n

    cost, tok_in, tok_out, parse_bad = 0.0, 0, 0, 0
    for fp in glob.glob(os.path.join(path, 'attempts', '*.json')):
        d = load_json(fp, {})
        if d.get('parse_status') not in (None, 'valid_json_object'):
            parse_bad += 1
        u = d.get('usage') or {}
        cost += u.get('cost') or 0
        tok_in += u.get('prompt_tokens') or 0
        tok_out += u.get('completion_tokens') or 0
    m['cost'] = cost
    m['tok_in'] = tok_in
    m['tok_out'] = tok_out
    m['parse_bad'] = parse_bad
    return m


METRICS = [
    ('model(s)', lambda m: ', '.join(sorted(m['models']))),
    ('temperatures used', lambda m: ', '.join(sorted(m['temps']))),
    ('calls (retried)', lambda m: f"{m['calls']} ({m['retried_calls']})"),
    ('calls by category', lambda m: ', '.join(f'{k}:{v}' for k, v in sorted(m['calls_by_cat'].items()))),
    ('first-pass invalid ayahs',
     lambda m: f"{len(m['first_pass_invalid'])}  [" + (', '.join(f'{k}:{v}' for k, v in sorted(m['first_pass_by_type'].items())) or 'none') + ']'),
    ('resolved by retry / unresolved', lambda m: f"{m['resolved_by_retry']} / {m['unresolved']}"),
    ('parse failures (attempts)', lambda m: m['parse_bad']),
    ('final hard failures', lambda m: len(m['failed'])),
    ('review flags', lambda m: len(m['review_flags'])),
    ('coarse chunk-size flags', lambda m: len(m['coarse_flags'])),
    ('ayahs with chunks', lambda m: m['ayahs']),
    ('mean words/chunk', lambda m: round(m['mean_wpc'], 3)),
    ('largest chunk (words)', lambda m: m['max_chunk']),
    ('one-word chunks %', lambda m: round(m['one_word_pct'], 1)),
    ('chunks >4 words %', lambda m: round(m['over4_pct'], 1)),
    ('tokens in / out', lambda m: f"{m['tok_in']:,} / {m['tok_out']:,}"),
    ('reported cost $', lambda m: round(m['cost'], 4)),
]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    runs = [load_run(p) for p in sys.argv[1:]]
    header = ['metric'] + [os.path.basename(r['dir'].rstrip('/')) for r in runs]
    rows = [[label] + [str(fn(m)) for m in runs] for label, fn in METRICS]
    widths = [max(len(header[i]), *(len(row[i]) for row in rows)) for i in range(len(header))]
    print('  '.join(h.ljust(w) for h, w in zip(header, widths)))
    for row in rows:
        print('  '.join(c.ljust(w) for c, w in zip(row, widths)))
    for i in range(2, len(header)):
        diffs = [f'{row[0]}: {row[1]} -> {row[i]}' for row in rows if row[i] != row[1]]
        if diffs:
            print(f"\n# {header[i]} vs {header[1]}")
            print('\n'.join('  ' + d for d in diffs))


if __name__ == '__main__':
    main()
