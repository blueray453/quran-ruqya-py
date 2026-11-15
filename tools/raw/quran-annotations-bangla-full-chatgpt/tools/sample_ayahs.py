#!/usr/bin/env python3
"""Create an anchor-aware, stratified sample by Arabic ayah word length.

Included anchor ayahs count toward their corresponding band quota. The sampler
then adds enough deterministic-random ayahs to reach the requested count where
possible. Bands with too few ayahs are reported honestly.
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import Src  # noqa: E402
from run_llm import parse_spec  # noqa: E402


def parse_bands(spec):
    out = []
    for part in spec.split(','):
        try:
            interval, count = part.split(':', 1)
            lo, hi = map(int, interval.split('-', 1))
            count = int(count)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f'invalid band {part!r}; expected lo-hi:count') from exc
        if lo < 1 or hi < lo or count < 1:
            raise argparse.ArgumentTypeError(f'invalid band {part!r}')
        out.append((lo, hi, count))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--per-band', default=(
        '1-10:2,11-20:2,21-30:2,31-40:2,41-50:2,51-60:2,61-70:2,'
        '71-80:2,81-90:2,91-100:2,101-110:2,111-120:2,121-130:2'),
        help='lo-hi:count, comma separated (Arabic words per ayah)')
    parser.add_argument('--include', default='',
                        help='required ayahs/ranges, e.g. "2:255,2:282,2:286,4:176,5:106-107"')
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--exclude', help='spec file whose ayahs/surahs are omitted')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    src = Src()
    skip = set()
    if args.exclude:
        with open(args.exclude, encoding='utf-8') as fh:
            skip = set(parse_spec(fh.read().splitlines(), src))

    anchors = parse_spec(args.include.split(','), src) if args.include.strip() else []
    invalid = [part.strip() for part in args.include.split(',')
               if part.strip() and not parse_spec([part.strip()], src)]
    if invalid:
        parser.error('unknown ayah/range(s) in --include: ' + ', '.join(invalid))
    if set(anchors) & skip:
        parser.error('--include ayahs cannot also be excluded')

    rng = random.Random(args.seed)
    all_ayahs = list(src.maxkey)
    selected_all = set(anchors)
    output = [f'# Stratified sample; seed={args.seed}; required anchors={len(anchors)}']

    for lo, hi, count in parse_bands(args.per_band):
        pool = sorted(key for key in all_ayahs
                      if lo <= src.n_words(*key) <= hi and key not in skip)
        band_anchors = sorted(key for key in anchors if lo <= src.n_words(*key) <= hi)
        remaining = [key for key in pool if key not in selected_all]
        need = max(0, count - len(band_anchors))
        chosen = sorted(rng.sample(remaining, min(need, len(remaining))))
        selected = sorted(set(band_anchors + chosen))

        if not pool:
            print(f'{lo}-{hi} words: 0 available (no ayahs in this band)')
        else:
            print(f'{lo}-{hi} words: selected {len(selected)}; {len(pool)} available; '
                  f'{len(band_anchors)} required anchor(s)')
        if len(band_anchors) > count:
            print(f'  note: required anchors exceed requested quota {count}; all anchors retained')

        output.append(f'\n# {lo}-{hi} words: {len(selected)} selected / {len(pool)} available')
        for surah, ayah in selected:
            marker = ' [required]' if (surah, ayah) in anchors else ''
            output.append(f'{surah}:{ayah}   # {src.n_words(surah, ayah)} words{marker}')
            selected_all.add((surah, ayah))

    outside = sorted(set(anchors) - selected_all)
    if outside:
        output.append('\n# Required anchors outside configured bands')
        for surah, ayah in outside:
            output.append(f'{surah}:{ayah}   # {src.n_words(surah, ayah)} words [required]')
            selected_all.add((surah, ayah))

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(output).strip() + '\n')

    chosen = sorted(selected_all)
    words = sum(src.n_words(*key) for key in chosen)
    print(f'wrote {len(chosen)} unique ayahs / {words} Arabic words -> {out_path}')
    print('selected ayahs:', ', '.join(f'{s}:{a}({src.n_words(s,a)}w)' for s, a in chosen))


if __name__ == '__main__':
    main()
