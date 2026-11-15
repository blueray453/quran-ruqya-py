#!/usr/bin/env python3
"""Post-hoc diagnostic comparison with Quranic Arabic Corpus treebank chunks.

Treebank boundaries are NEVER hard fences and are never model input. For the flat chunk
schema, this report only shows where those boundaries coincide with annotation chunk ends
or land inside a chunk. It exits successfully even when they differ.
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, Src, load_json  # noqa: E402

BANDS = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 60), (61, 80), (81, 9999)]


def load_chunks():
    tokens, ends = {}, {}
    path = os.path.join(ROOT, 'sources/chunker/quranic-treebank-0.4-chunks.tsv')
    with open(path, encoding='utf-8') as fh:
        next(fh, None)
        for line in fh:
            cols = line.rstrip('\n').split('\t')
            if len(cols) < 9:
                continue
            key = (int(cols[0]), int(cols[1]))
            tokens[key] = max(tokens.get(key, 0), int(cols[2]))
            if cols[8] == '1':
                ends.setdefault(key, []).append(int(cols[2]))
    return tokens, ends


def annotation_chunks(entry):
    if 'chunks' in entry:
        return entry['chunks']
    return [p for clause in entry.get('clauses', []) for p in clause.get('phrases', [])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--annotations-dir', default=os.path.join(ROOT, 'annotations'))
    parser.add_argument('--surah', type=int, action='append')
    parser.add_argument('--out', help='write markdown report')
    args = parser.parse_args()

    src = Src()
    tokens, tree_ends = load_chunks()
    totals = {'ayahs': 0, 'no_treebank': 0, 'misaligned': 0, 'checked': 0,
              'tree_end_count': 0, 'coincident': 0, 'inside': 0, 'outside': 0}
    bands = {band: [0, 0, 0, 0] for band in BANDS}  # ayahs, tree ends, coincident, inside
    rows, details = [], []

    for path in sorted(glob.glob(os.path.join(args.annotations_dir, 'surah-*.json'))):
        surah = int(os.path.basename(path)[6:9])
        if args.surah and surah not in args.surah:
            continue
        doc = load_json(path)
        stats = dict.fromkeys(totals, 0)
        for ayah_str, entry in sorted(doc['ayahs'].items(), key=lambda kv: int(kv[0])):
            ayah = int(ayah_str)
            key = (surah, ayah)
            stats['ayahs'] += 1
            if key not in tokens:
                stats['no_treebank'] += 1
                continue
            n_words = src.n_words(surah, ayah)
            if tokens[key] != n_words:
                stats['misaligned'] += 1
                details.append(f'- **{surah}:{ayah}** treebank has {tokens[key]} tokens but ayah has {n_words} words; skipped')
                continue
            stats['checked'] += 1
            chunks = annotation_chunks(entry)
            annotation_ends = {chunk['words'][-1] for chunk in chunks if chunk.get('words')}
            ends = set(tree_ends.get(key, []))
            exact = ends & annotation_ends
            internal = {end for end in ends if end not in annotation_ends and any(
                chunk['words'][0] <= end < chunk['words'][-1]
                for chunk in chunks if chunk.get('words'))}
            outside = ends - exact - internal
            stats['tree_end_count'] += len(ends)
            stats['coincident'] += len(exact)
            stats['inside'] += len(internal)
            stats['outside'] += len(outside)
            band = next(b for b in BANDS if b[0] <= n_words <= b[1])
            band_stats = bands[band]
            band_stats[0] += 1
            band_stats[1] += len(ends)
            band_stats[2] += len(exact)
            band_stats[3] += len(internal)
            if internal or outside:
                words = {w: ar for w, ar, _, _ in src.words(surah, ayah)}
                by_end = {chunk['words'][-1]: chunk for chunk in chunks if chunk.get('words')}
                details.append(f'### {surah}:{ayah}')
                for end in sorted(internal):
                    chunk = next(c for c in chunks if c['words'][0] <= end < c['words'][-1])
                    context = ' '.join(words[w] for w in range(max(1, end - 2), min(n_words, end + 2) + 1))
                    details.append(f'- Treebank boundary at word {end} falls inside annotation chunk '
                                   f'{chunk["words"][0]}-{chunk["words"][-1]} ({chunk.get("en", "")!r}); Arabic context: …{context}…')
                for end in sorted(outside):
                    details.append(f'- Treebank boundary at word {end} is not represented by an annotation chunk end '
                                   '(check source alignment or treebank conventions)')
                details.append('- chunks: ' + ' | '.join(
                    f'{c["words"][0]}-{c["words"][-1]} {c.get("en", "")!r}' for c in chunks))
                details.append('')
        for metric in totals:
            totals[metric] += stats[metric]
        pct = stats['coincident'] / stats['tree_end_count'] if stats['tree_end_count'] else 0
        rows.append(f'| {surah} | {stats["ayahs"]} | {stats["checked"]} | {stats["tree_end_count"]} | '
                    f'{stats["coincident"]} ({pct:.0%}) | {stats["inside"]} | {stats["outside"]} |')

    overall = totals['coincident'] / totals['tree_end_count'] if totals['tree_end_count'] else 0
    lines = [
        '# Treebank / annotation chunk diagnostic', '',
        'Treebank chunk boundaries are an independent comparison signal, not gold boundaries. '
        'Differences do not fail QA and must not be used to force annotation segmentation.', '',
        '| surah | ayahs | checked | treebank boundaries | coincident with annotation chunk end | inside annotation chunk | other/unmapped |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
    ] + rows
    lines += ['', f'**Total:** {totals["checked"]} ayahs checked; {totals["coincident"]}/{totals["tree_end_count"]} '
              f'treebank boundaries coincide with annotation chunk ends ({overall:.0%}); '
              f'{totals["inside"]} fall inside a chunk. '
              f'{totals["no_treebank"]} ayahs have no treebank coverage; {totals["misaligned"]} were token-misaligned.',
              '', '## By ayah length (Arabic words)', '',
              '| words | ayahs checked | treebank boundaries | coincident | inside chunks |',
              '| --- | ---: | ---: | ---: | ---: |']
    for (lo, hi), (ayahs, count, matched, inside) in bands.items():
        if ayahs:
            lines.append(f'| {lo}-{hi if hi < 9999 else "+"} | {ayahs} | {count} | {matched} | {inside} |')
    lines.append('')
    if details:
        lines += ['## Examples to inspect', ''] + details
    report = '\n'.join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(report + '\n')


if __name__ == '__main__':
    main()
