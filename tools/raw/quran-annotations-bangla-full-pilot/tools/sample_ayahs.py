#!/usr/bin/env python3
"""tools/sample_ayahs.py — stratified ayah sample by length, from chunker-covered ayahs only.

Purpose: measure at which ayah length a model starts breaking the chunker fence, so routing thresholds
(--long-words) are chosen from data instead of guessed.

  python3 tools/sample_ayahs.py --out band_sample.txt
  python3 tools/run_llm.py --pilot band_sample.txt --tag bands_haiku --long-model '' --escalate-model '' --coarse-retries 0
  python3 tools/chunker_report.py --annotations-dir runs/bands_haiku/annotations     # see the "By ayah length" table
"""
import argparse, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import Src  # noqa: E402
from chunker_report import load_chunks  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--per-band', default='11-20:10,21-30:16,31-40:16,41-60:10,61-80:6',
                help='lo-hi:count, comma separated (Arabic words per ayah)')
ap.add_argument('--seed', type=int, default=1)
ap.add_argument('--exclude', help='spec file whose ayahs/surahs are left out (e.g. pilot.txt)')
ap.add_argument('--out', required=True)
args = ap.parse_args()

src = Src()
toks, _ = load_chunks()
skip = set()
if args.exclude:
    from run_llm import parse_spec
    skip = set(parse_spec(open(args.exclude, encoding='utf-8').read().splitlines(), src))
rng = random.Random(args.seed)
out = []
for part in args.per_band.split(','):
    rng_s, cnt = part.split(':')
    lo, hi = map(int, rng_s.split('-'))
    pool = sorted(k for k in toks if lo <= src.n_words(*k) <= hi and k in src.maxkey and k not in skip)
    pick = sorted(rng.sample(pool, min(int(cnt), len(pool))))
    print(f'{lo}-{hi} words: {len(pick)} of {len(pool)} chunker-covered ayahs')
    out += [f'{s}:{a}   # {src.n_words(s, a)} words' for s, a in pick]
open(args.out, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(f'wrote {len(out)} ayahs -> {args.out}')
