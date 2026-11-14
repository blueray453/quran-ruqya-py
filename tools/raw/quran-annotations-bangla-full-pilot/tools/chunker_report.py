#!/usr/bin/env python3
"""tools/chunker_report.py — compare annotation boundaries with the treebank chunker.

The chunker file (sources/chunker/quranic-treebank-0.4-chunks.tsv) is a QA signal only; it is
never shown to the model. Fence (same as qa.py): every chunk_end token must be a CLAUSE end.
This report adds detail so you can see *why* an ayah failed and how often the two agree.

  python3 tools/chunker_report.py --annotations-dir runs/pilot1/annotations
  python3 tools/chunker_report.py --annotations-dir runs/pilot1/annotations --surah 78 --out report.md

Per chunk_end token it reports one of:
  OK            lands on a clause end
  PHRASE-END    lands on a phrase end that is not a clause end  -> clause probably too long
  INSIDE-PHRASE lands inside a phrase                           -> phrase/clause too coarse
Also: tokens-vs-words alignment check, and agreement (share of clause ends the chunker also marks).
"""
import argparse, glob, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, Src, load_json  # noqa: E402

FEWSHOT = {'67:9', '67:15', '67:23'}   # appear in CONVENTIONS.md examples


def load_chunks():
    toks, ends = {}, {}
    with open(os.path.join(ROOT, 'sources/chunker/quranic-treebank-0.4-chunks.tsv'), encoding='utf-8') as f:
        next(f)
        for ln in f:
            c = ln.rstrip('\n').split('\t')
            if len(c) < 9:
                continue
            k = (int(c[0]), int(c[1]))
            toks[k] = max(toks.get(k, 0), int(c[2]))
            if c[8] == '1':
                ends.setdefault(k, []).append(int(c[2]))
    return toks, ends


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--annotations-dir', default=os.path.join(ROOT, 'annotations'))
    ap.add_argument('--surah', type=int, action='append')
    ap.add_argument('--out', help='write the markdown report here (default: stdout only)')
    args = ap.parse_args()

    src = Src()
    toks, ends = load_chunks()
    lines, rows = [], []
    tot = dict(ayahs=0, nochunk=0, misaligned=0, bad_ayahs=0, ok=0, phrase_end=0, inside=0,
               clause_ends=0, clause_ends_agreed=0)

    for path in sorted(glob.glob(os.path.join(args.annotations_dir, 'surah-*.json'))):
        s = int(os.path.basename(path)[6:9])
        if args.surah and s not in args.surah:
            continue
        doc = load_json(path)
        sc = dict.fromkeys(tot, 0)
        for a_str, ay in sorted(doc['ayahs'].items(), key=lambda kv: int(kv[0])):
            a, key = int(a_str), f'{s}:{a_str}'
            sc['ayahs'] += 1
            if (s, a) not in toks:
                sc['nochunk'] += 1
                continue
            n = src.n_words(s, a)
            if toks[(s, a)] != n:
                sc['misaligned'] += 1
                lines.append(f'- **{key}** chunker has {toks[(s, a)]} tokens but the ayah has {n} words — skipped')
                continue
            clause_end = {max(c['words']) for c in ay['clauses']}
            phrase_end = {max(p['words']) for c in ay['clauses'] for p in c['phrases']}
            ce = set(ends.get((s, a), []))
            sc['clause_ends'] += len(clause_end)
            sc['clause_ends_agreed'] += len(clause_end & ce)
            bad = []
            for e in sorted(ce):
                if e in clause_end:
                    sc['ok'] += 1
                elif e in phrase_end:
                    sc['phrase_end'] += 1
                    bad.append((e, 'PHRASE-END'))
                else:
                    sc['inside'] += 1
                    bad.append((e, 'INSIDE-PHRASE'))
            if bad:
                sc['bad_ayahs'] += 1
                words = {w: ar for w, ar, _, _ in src.words(s, a)}
                frag = {}
                for c in ay['clauses']:
                    for p in c['phrases']:
                        frag[max(p['words'])] = (p['words'], p['en'])
                tag = ' (in few-shot examples)' if key in FEWSHOT else ''
                lines.append(f'### {key}{tag}')
                for e, kind in bad:
                    ctx = ' '.join(words[w] for w in range(max(1, e - 2), min(n, e + 2) + 1))
                    where = next((p for c in ay['clauses'] for p in c['phrases'] if e in p['words']), None)
                    lines.append(f'- chunker ends at word {e} → **{kind}** — Arabic …{ctx}…; '
                                 f'phrase {where["words"][0]}-{where["words"][-1]}: "{where["en"]}"')
                lines.append('- clauses: ' + ' | '.join(
                    f'{c["words"][0]}-{c["words"][-1]} "{" ".join(p["en"] for p in c["phrases"])}"' for c in ay['clauses']))
                lines.append('')
        for k in tot:
            tot[k] += sc[k]
        checked = sc['ayahs'] - sc['nochunk'] - sc['misaligned']
        agree = sc['clause_ends_agreed'] / sc['clause_ends'] if sc['clause_ends'] else 0
        rows.append(f'| {s} | {sc["ayahs"]} | {checked} | {sc["bad_ayahs"]} | {sc["ok"]} | {sc["phrase_end"]} | '
                    f'{sc["inside"]} | {agree:.0%} |')

    head = ['# Chunker cross-check', '',
            '| surah | ayahs | checked | ayahs failing | chunk ends OK | PHRASE-END | INSIDE-PHRASE | clause ends also in chunker |',
            '| --- | --- | --- | --- | --- | --- | --- | --- |'] + rows
    n_ends = tot['ok'] + tot['phrase_end'] + tot['inside']
    checked = tot['ayahs'] - tot['nochunk'] - tot['misaligned']
    head += ['', f'**Total:** {checked} ayahs checked ({tot["nochunk"]} without chunker coverage, {tot["misaligned"]} misaligned); '
             f'{tot["ok"]}/{n_ends} chunk ends land on clause ends; {tot["bad_ayahs"]} ayah(s) violate the fence.', '']
    report = '\n'.join(head + (['## Violations', ''] + lines if lines else []))
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        open(args.out, 'w', encoding='utf-8').write(report + '\n')
    sys.exit(1 if tot['bad_ayahs'] else 0)


if __name__ == '__main__':
    main()
