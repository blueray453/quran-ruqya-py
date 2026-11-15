#!/usr/bin/env python3
"""tools/conform_chunker.py — enforce the data-model invariant "every chunker boundary is a clause boundary".

OPTIONAL post-step. Where a chunker boundary (sources/chunker/...-chunks.tsv) falls on a PHRASE end inside a
clause, the clause is split there — the English file and the Bangla overlay identically. Nothing is re-translated
and no phrase changes. Chunker boundaries that fall INSIDE a phrase cannot be fixed mechanically; they are listed
for a reviewer (or a re-run of that ayah).

  python3 tools/conform_chunker.py --annotations-dir runs/pilot3/annotations            # -> runs/pilot3/annotations_conformed
  python3 tools/conform_chunker.py --annotations-dir runs/pilot3/annotations --out-dir X

Trade-off: after this step "clause ends also chunker ends" is no longer independent evidence for those ayahs.
Ayahs that were changed get `conformed: [word, ...]` (words after which a clause was split); status stays `auto`.
The planned EQTB / waqf fences stay independent.
"""
import argparse, copy, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ayahlib import ROOT, load_json  # noqa: E402
from chunker_report import load_chunks  # noqa: E402


def split_clauses(clauses, cut_ends):
    """Split clauses after every phrase whose last word is in cut_ends (and not already a clause end)."""
    out, applied = [], []
    for cl in clauses:
        cur = []
        for ph in cl['phrases']:
            cur.append(ph)
            e = ph['words'][-1]
            if e in cut_ends and ph is not cl['phrases'][-1]:
                out.append(cur)
                applied.append(e)
                cur = []
        if cur:
            out.append(cur)
    new = [{'words': [w for ph in phs for w in ph['words']], 'phrases': phs} for phs in out]
    return new, applied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--annotations-dir', required=True)
    ap.add_argument('--out-dir')
    args = ap.parse_args()
    src_dir = os.path.abspath(args.annotations_dir)
    out_dir = os.path.abspath(args.out_dir or src_dir.rstrip('/') + '_conformed')
    toks, ends = load_chunks()
    n_split = n_ayahs = 0
    unresolved = []
    for path in sorted(glob.glob(os.path.join(src_dir, 'surah-*.json'))):
        name = os.path.basename(path)
        s = int(name[6:9])
        en = load_json(path)
        bnp = os.path.join(src_dir, 'bn', name)
        bn = load_json(bnp) if os.path.exists(bnp) else None
        for a, ay in en['ayahs'].items():
            ce = set(ends.get((s, int(a)), []))
            if not ce:
                continue
            clause_end = {c['words'][-1] for c in ay['clauses']}
            phrase_end = {p['words'][-1] for c in ay['clauses'] for p in c['phrases']}
            cut = (ce - clause_end) & phrase_end
            inside = sorted(ce - clause_end - phrase_end)
            if inside:
                unresolved.append(f'{s}:{a} chunker boundary inside a phrase after word(s) {inside}')
            if not cut:
                continue
            ay['clauses'], applied = split_clauses(ay['clauses'], cut)
            ay['conformed'] = sorted(applied)
            if bn and a in bn['ayahs']:
                bn['ayahs'][a]['clauses'], applied_bn = split_clauses(bn['ayahs'][a]['clauses'], cut)
                assert applied_bn == applied, f'{s}:{a} en/bn structure differs'
                bn['ayahs'][a]['conformed'] = sorted(applied)
            n_split += len(applied)
            n_ayahs += 1
        for doc, p in ((en, os.path.join(out_dir, name)), (bn, os.path.join(out_dir, 'bn', name))):
            if doc is None:
                continue
            doc['provenance'] = dict(doc.get('provenance', {}),
                                     conformed='clauses split at chunker boundaries that are phrase ends (tools/conform_chunker.py)')
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=2)
    print(f'split {n_split} clause(s) in {n_ayahs} ayah(s) -> {out_dir}')
    if unresolved:
        print(f'{len(unresolved)} ayah(s) still need a human or a re-run:')
        for u in unresolved:
            print('  ' + u)
    print(f'next: python3 qa.py --annotations-dir {os.path.relpath(out_dir, ROOT)} --no-baseline')


if __name__ == '__main__':
    main()
