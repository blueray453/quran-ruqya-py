#!/usr/bin/env python3
"""tools/review_flags.py — heuristic review list for LLM annotations (never blocks anything).

  python3 tools/review_flags.py --annotations-dir runs/pilot1/annotations --out runs/pilot1/review_flags.md

Per surah: granularity numbers (compare with the Al-Mulk prototype: 1.56 words/phrase,
3.87 words/clause, 2.5 phrases/clause, ~9% one-phrase clauses, ~65% of clause ends also chunker ends).
Per ayah, candidates a human should look at first (a meaning said twice with different words, e.g. 2:255 words
45-47, is not detectable this way - it needs a reviewer):
  register  Bangla address register differs from the Bangla reference translation (আপনি/…ুন vs তুমি/বল)
  dropped? / moved/doubled?  a phrase whose English carries none of its words' meaning, or contains the meaning of
            a neighbouring phrase (checked against the English word-by-word glosses; about half are real)
These are heuristics: expect some false alarms; they exist to order the review queue.
"""
import argparse, glob, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, Src, load_json, meaning_flags, RESPECTFUL, PLAIN  # noqa: E402

def load_ends():
    ends = {}
    with open(os.path.join(ROOT, 'sources/chunker/quranic-treebank-0.4-chunks.tsv'), encoding='utf-8') as f:
        next(f)
        for ln in f:
            c = ln.rstrip('\n').split('\t')
            if len(c) >= 9 and c[8] == '1':
                ends.setdefault((int(c[0]), int(c[1])), set()).add(int(c[2]))
    return ends


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--annotations-dir', default=os.path.join(ROOT, 'annotations'))
    ap.add_argument('--out')
    args = ap.parse_args()
    src, ends = Src(), load_ends()
    summary, flags = [], []
    for path in sorted(glob.glob(os.path.join(args.annotations_dir, 'surah-*.json'))):
        s = int(os.path.basename(path)[6:9])
        en = load_json(path)['ayahs']
        bnp = os.path.join(args.annotations_dir, 'bn', os.path.basename(path))
        bn = load_json(bnp)['ayahs'] if os.path.exists(bnp) else {}
        W = P = C = one = agree = n_cl = 0
        for a, v in sorted(en.items(), key=lambda kv: int(kv[0])):
            key = f'{s}:{a}'
            cls = v['clauses']
            ph = [p for c in cls for p in c['phrases']]
            W += sum(len(p['words']) for p in ph); P += len(ph); C += len(cls)
            one += sum(1 for c in cls if len(c['phrases']) == 1)
            ce = ends.get((s, int(a)), set())
            n_cl += len(cls); agree += sum(1 for c in cls if c['words'][-1] in ce)
            why = []
            gloss = {w: ge for w, ar, ge, gb in src.words(s, int(a))}
            why += meaning_flags(gloss, [[{'words': p['words'], 'en': p['en']} for p in c['phrases']] for c in cls])
            if a in bn:                                             # Bangla register
                ref = src.tr_bn.get(key, '')
                mod = ' '.join(p['bn'] for c in bn[a]['clauses'] for p in c['phrases'])
                r_resp, r_plain = bool(RESPECTFUL.search(ref)), bool(PLAIN.search(ref))
                m_resp, m_plain = bool(RESPECTFUL.search(mod)), bool(PLAIN.search(mod))
                if r_resp and not r_plain and m_plain:
                    why.append('register: reference is respectful (আপনি/…ুন) but fragments use তুমি/বল forms')
                elif r_plain and not r_resp and m_resp:
                    why.append('register: reference uses তুমি/বল but fragments are respectful (আপনি/…ুন)')
            if why:
                flags.append((key, why))
        summary.append(f'| {s} | {len(en)} | {W / P:.2f} | {W / C:.2f} | {P / C:.2f} | {one / C:.0%} | {agree / n_cl:.0%} |')
    out = ['# Review flags (heuristics)', '',
           '| surah | ayahs | words/phrase | words/clause | phrases/clause | one-phrase clauses | clause ends also chunker ends |',
           '| --- | --- | --- | --- | --- | --- | --- |',
           '| *Mulk prototype* | 30 | 1.56 | 3.87 | 2.48 | 9% | 65% |'] + summary + ['']
    out += [f'## {len(flags)} ayah(s) to look at first', ''] + [f'- **{k}** — ' + ' · '.join(w) for k, w in flags]
    text = '\n'.join(out)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        open(args.out, 'w', encoding='utf-8').write(text + '\n')


if __name__ == '__main__':
    main()
