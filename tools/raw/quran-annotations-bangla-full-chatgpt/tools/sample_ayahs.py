#!/usr/bin/env python3
"""Create a reproducible stratified ayah sample by Arabic word length.

Use this to benchmark model choice and batching across short, medium, and long ayahs.
Chunker coverage is not required; treebank alignment is a diagnostic, not a sampling filter.

Example:
  python3 tools/sample_ayahs.py --out band_sample.txt
  python3 tools/run_llm.py --pilot band_sample.txt --tag band_haiku
"""
import argparse
import random
import sys

sys.path.insert(0, 'tools')
from ayahlib import Src  # noqa: E402


def parse_bands(spec):
    out = []
    for part in spec.split(','):
        interval, count = part.split(':', 1)
        lo, hi = map(int, interval.split('-', 1))
        if lo < 1 or hi < lo or int(count) < 1:
            raise argparse.ArgumentTypeError(f'invalid band {part!r}')
        out.append((lo, hi, int(count)))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--per-band', default='1-10:8,11-20:10,21-30:10,31-40:10,41-60:10,61-80:6,81-130:4',
                        help='lo-hi:count, comma separated (Arabic words per ayah)')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--exclude', help='spec file whose ayahs/surahs are omitted')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    src = Src()
    skip = set()
    if args.exclude:
        from run_llm import parse_spec
        with open(args.exclude, encoding='utf-8') as fh:
            skip = set(parse_spec(fh.read().splitlines(), src))
    rng = random.Random(args.seed)
    all_ayahs = list(src.maxkey)
    output = []
    for lo, hi, count in parse_bands(args.per_band):
        pool = sorted(key for key in all_ayahs if lo <= src.n_words(*key) <= hi and key not in skip)
        chosen = sorted(rng.sample(pool, min(count, len(pool))))
        print(f'{lo}-{hi} words: selected {len(chosen)} of {len(pool)} available ayahs')
        output += [f'{surah}:{ayah}   # {src.n_words(surah, ayah)} words' for surah, ayah in chosen]
    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(output) + '\n')
    print(f'wrote {len(output)} ayahs -> {args.out}')


if __name__ == '__main__':
    main()
