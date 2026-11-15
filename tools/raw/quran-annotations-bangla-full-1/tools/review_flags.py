#!/usr/bin/env python3
"""Create conservative phrase-integrity and terminology review candidates.

Chunk-size numbers are descriptive only. The old word-overlap `meaning_flags` heuristic is
intentionally retired because it mislabeled valid context-dependent fragments as missing
meaning. Structural coverage remains a hard QA rule; these linguistic flags are review hints.
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import (ROOT, Src, load_json, syntactic_review_flags, terminology_flags,
                     RESPECTFUL, PLAIN)  # noqa: E402


def chunks_of(entry):
    if 'chunks' in entry:
        return entry['chunks']
    return [p for clause in entry.get('clauses', []) for p in clause.get('phrases', [])]


def source_text(src, surah, ayah, words):
    wanted = set(words or [])
    return ' '.join(ar for w, ar, _, _ in src.words(surah, ayah) if w in wanted)


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
            a = int(ayah)
            key = f'{surah}:{ayah}'
            chunks = chunks_of(entry)
            total_words += sum(len(c['words']) for c in chunks)
            total_chunks += len(chunks)
            for chunk in chunks:
                size_counts[len(chunk['words'])] = size_counts.get(len(chunk['words']), 0) + 1

            reasons = []
            for reason in syntactic_review_flags(chunks):
                reasons.append(reason)
            for i, chunk in enumerate(chunks, 1):
                for issue in terminology_flags(chunk.get('en', ''), None):
                    reasons.append(f'chunk {i}: {issue}')
            if ayah in bn:
                bn_chunks = chunks_of(bn[ayah])
                for i, chunk in enumerate(bn_chunks, 1):
                    for issue in terminology_flags('', chunk.get('bn', '')):
                        reasons.append(f'Bangla chunk {i}: {issue}')
                ref = src.tr_bn.get(key, '') or ''
                bn_text = ' '.join(chunk.get('bn', '') for chunk in bn_chunks)
                ref_respectful, ref_plain = bool(RESPECTFUL.search(ref)), bool(PLAIN.search(ref))
                model_respectful, model_plain = bool(RESPECTFUL.search(bn_text)), bool(PLAIN.search(bn_text))
                if ref_respectful and not ref_plain and model_plain:
                    reasons.append('register: reference is respectful (আপনি/…ুন) but fragments use তুমি/বল forms')
                elif ref_plain and not ref_respectful and model_respectful:
                    reasons.append('register: reference uses তুমি/বল but fragments are respectful (আপনি/…ুন)')

            if reasons:
                chunks_by_index = []
                for i, reason in enumerate(reasons, 1):
                    chunks_by_index.append(f'  - {reason}')
                flags.append((key, chunks_by_index))

        mean = total_words / total_chunks if total_chunks else 0
        one_share = size_counts.get(1, 0) / total_chunks if total_chunks else 0
        two_share = size_counts.get(2, 0) / total_chunks if total_chunks else 0
        over_four = sum(n for size, n in size_counts.items() if size > 4) / total_chunks if total_chunks else 0
        summary.append(f'| {surah} | {len(en)} | {mean:.2f} | {one_share:.0%} | {two_share:.0%} | {over_four:.0%} |')

    lines = [
        '# Phrase integrity review candidates', '',
        'These are conservative review hints, not automatic errors. The previous word-overlap '
        'meaning heuristic has been retired because it flagged valid elliptical/context-dependent '
        'fragments as dropped meaning. Structural QA checks exact Arabic word coverage separately.', '',
        '| surah | ayahs | words/chunk | one-word chunks | two-word chunks | >4-word chunks |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ] + summary
    lines += ['', f'## {len(flags)} ayah(s) with phrase-integrity / terminology candidates', '']
    for key, reasons in flags:
        lines.append(f'- **{key}**')
        lines.extend(reasons)
    lines += ['', '## Interpretation', '',
              '- A standalone function word or a fragment ending in a dependent connector is a boundary-review candidate, not necessarily a mistake.',
              '- A chunk may be elliptical because translation fragments align to Arabic spans; it need not be a complete sentence.',
              '- Do not split or merge mechanically to achieve a target average chunk length.',
              '- English terminology must use Allah / Rabb / ilah according to the Arabic; Bangla must use আল্লাহ / রব / ইলাহ.']
    report = '\n'.join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(report + '\n')


if __name__ == '__main__':
    main()
