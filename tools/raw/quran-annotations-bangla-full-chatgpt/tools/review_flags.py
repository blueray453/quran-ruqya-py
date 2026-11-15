#!/usr/bin/env python3
"""Create a heuristic review queue for flat Arabic chunk annotations.

Flags possible dropped/moved/doubled English gloss meaning and Bangla register mismatches.
Chunk size distributions are descriptive only; they are not rules to force splitting.
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, Src, load_json, meaning_flags, RESPECTFUL, PLAIN  # noqa: E402


def chunks_of(entry):
    if 'chunks' in entry:
        return entry['chunks']
    return [p for clause in entry.get('clauses', []) for p in clause.get('phrases', [])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--annotations-dir', default=os.path.join(ROOT, 'annotations'))
    parser.add_argument('--out')
    args = parser.parse_args()
    src = Src()
    summary, flags = [], []

    for path in sorted(glob.glob(os.path.join(args.annotations_dir, 'surah-*.json'))):
        surah = int(os.path.basename(path)[6:9])
        en = load_json(path)['ayahs']
        bn_path = os.path.join(args.annotations_dir, 'bn', os.path.basename(path))
        bn = load_json(bn_path)['ayahs'] if os.path.exists(bn_path) else {}
        total_words = total_chunks = 0
        size_counts = {}
        for ayah, entry in sorted(en.items(), key=lambda kv: int(kv[0])):
            key = f'{surah}:{ayah}'
            chunks = chunks_of(entry)
            total_words += sum(len(c['words']) for c in chunks)
            total_chunks += len(chunks)
            for chunk in chunks:
                size_counts[len(chunk['words'])] = size_counts.get(len(chunk['words']), 0) + 1
            gloss = {w: ge for w, ar, ge, gb in src.words(surah, int(ayah))}
            reasons = meaning_flags(gloss, chunks)
            if ayah in bn:
                ref = src.tr_bn.get(key, '')
                bn_text = ' '.join(chunk['bn'] for chunk in chunks_of(bn[ayah]))
                ref_respectful, ref_plain = bool(RESPECTFUL.search(ref)), bool(PLAIN.search(ref))
                model_respectful, model_plain = bool(RESPECTFUL.search(bn_text)), bool(PLAIN.search(bn_text))
                if ref_respectful and not ref_plain and model_plain:
                    reasons.append('register: reference is respectful (আপনি/…ুন) but fragments use তুমি/বল forms')
                elif ref_plain and not ref_respectful and model_respectful:
                    reasons.append('register: reference uses তুমি/বল but fragments are respectful (আপনি/…ুন)')
            if reasons:
                flags.append((key, reasons))
        mean = total_words / total_chunks if total_chunks else 0
        one_share = size_counts.get(1, 0) / total_chunks if total_chunks else 0
        two_share = size_counts.get(2, 0) / total_chunks if total_chunks else 0
        over_four = sum(n for size, n in size_counts.items() if size > 4) / total_chunks if total_chunks else 0
        summary.append(f'| {surah} | {len(en)} | {mean:.2f} | {one_share:.0%} | {two_share:.0%} | {over_four:.0%} |')

    lines = ['# Chunk review flags (heuristics)', '',
             'Chunk-size numbers are descriptive, not quotas. A large chunk is a review candidate, '
             'not an automatic instruction to split.', '',
             '| surah | ayahs | words/chunk | one-word chunks | two-word chunks | >4-word chunks |',
             '| --- | ---: | ---: | ---: | ---: | ---: |'] + summary
    lines += ['', f'## {len(flags)} ayah(s) with possible meaning/register issues', '']
    lines += [f'- **{key}** — ' + ' · '.join(reasons) for key, reasons in flags]
    report = '\n'.join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(report + '\n')


if __name__ == '__main__':
    main()
