#!/usr/bin/env python3
"""Small query examples for the generated chunk tables (standard library only)."""
import argparse, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def stream_chunks(path, family=None, surah=None):
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            if family and row['chunk_family'] != family:
                continue
            if surah and row['surah'] != str(surah):
                continue
            yield row


def main():
    ap = argparse.ArgumentParser(description='Filter Quran chunk occurrences by family and/or Surah.')
    ap.add_argument('--family', help='Example: idafi, jarri, tawsifi, atfi, fa_il, maf_ul_bih')
    ap.add_argument('--surah', type=int)
    ap.add_argument('--limit', type=int, default=20)
    ap.add_argument('--csv-dir', type=Path, default=ROOT/'output/csv')
    args = ap.parse_args()
    path = args.csv_dir/'quran_chunk_occurrences.csv'
    count = 0
    for row in stream_chunks(path, args.family, args.surah):
        print(f"{row['chunk_id']} | {row['chunk_family']} | {row['surah']}:{row['ayahs']} | {row['span_text_indopak']} | review={row['review_required']}")
        count += 1
        if count >= args.limit:
            break
    print(f'\nDisplayed {count} row(s).')

if __name__ == '__main__':
    main()
