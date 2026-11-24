#!/usr/bin/env python3
"""Stage 6: repeated Arabic words and phrases and their memorization order (the original phrase analysis),
computed from the WORD LAYER only (word keys give the verse, text_normalized / text_exact the matching spelling,
text_indopak the displayed text). Reproduces quran-phrases.csv and the greedy orders of the original project.

Writes output/phrases/                                    (matching on base letters; exact-diacritics/ matches on the diacritized spelling)
  quran-phrases.csv, quran-phrases-annotation.json        every repeated word / phrase with counts and exact locations
  quran-coverage-by-surah.csv                             coverage per surah
  summary.json                                            headline numbers
Writes output/memorization-order/                         (and exact-diacritics/)
  quran-greedy-order-words-and-phrases.csv                memorization order, words + phrases   (original)
  quran-greedy-order-phrases-only.csv                     phrases of 2+ words only              (original)
  quran-greedy-order-words-only.csv                       single words only                     (new)
  quran-greedy-order-phrases-3plus.csv                    phrases of 3+ words only              (new)

Definitions: unit = n >= 1 consecutive words inside ONE verse (never across a verse boundary) occurring at least twice;
total = every occurrence (overlaps included); stand-alone = occurrences NOT inside a longer repeated unit;
coverage = share of word positions inside at least one unit; memorization order = lazy greedy set cover, efficiency =
new words covered / words in the unit.
Usage: python3 pipeline/06_phrases.py [--out-dir output]
"""
import argparse
import collections
import csv
import heapq
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import grammar_data as G
import study_data as D

PAUSE = set('\u0615\u06d6\u06d7\u06d8\u06d9\u06da\u06db')
ZW = ' \u200b\u200c\u200d\u200e\u200f\ufeff\u2002\u2003\u00a0'


def clean_end(w):
    w = w.strip(ZW)
    while w and (w[-1] in PAUSE or w[-1] in ZW):
        w = w[:-1]
    return w


def analyse(words, field, T_ph, T_mem, sub, nfiles):
    """Original analysis for one matching field. words = word layer 'words' dict (already in Quran order)."""
    verses, cur = [], None
    for k, w in words.items():
        a = D.ayah_key(k)
        if a != cur:
            verses.append({'key': a, 's': D.surah(k), 'locs': [], 'norm': [], 'text': []})
            cur = a
        verses[-1]['locs'].append(k)
        verses[-1]['norm'].append(w[field])
        verses[-1]['text'].append(w['text_indopak'])
    assert len(verses) == 6236
    TOTAL = sum(len(v['norm']) for v in verses)
    to_base = {w[field]: w['text_normalized'] for w in words.values()}
    offs, o = [], 0
    for v in verses:
        offs.append(o)
        o += len(v['norm'])

    rep, n = {}, 1
    while True:
        d = collections.defaultdict(list)
        for vi, v in enumerate(verses):
            ws = v['norm']
            for i in range(len(ws) - n + 1):
                d[tuple(ws[i:i + n])].append((vi, i))
        r = {g: p for g, p in d.items() if len(p) >= 2}
        if not r:
            break
        rep[n] = r
        n += 1
    rep_pos = {n: {p for ps in r.values() for p in ps} for n, r in rep.items()}
    rows = []
    for n, r in rep.items():
        nxt = rep_pos.get(n + 1, set())
        for g, ps in r.items():
            rows.append((g, n, ps, [(vi, i) not in nxt and (vi, i - 1) not in nxt for vi, i in ps]))
    rows.sort(key=lambda x: (-len(x[2]), -x[1], x[0]))

    def vlist(ps, flags=None):
        seen, s = [], set()
        for j, (vi, i) in enumerate(ps):
            if flags is not None and not flags[j]:
                continue
            if vi not in s:
                s.add(vi)
                seen.append(verses[vi]['key'])
        return seen

    ann, csvrows = [], []
    for idx, (g, n, ps, alone) in enumerate(rows, 1):
        vi0, i0 = ps[0]
        vt = [x.strip(ZW) for x in verses[vi0]['text'][i0:i0 + n]]
        vt[-1] = clean_end(vt[-1])
        ph, tot, sa = ' '.join(g), len(ps), sum(alone)
        letters = ' '.join(to_base[x] for x in g)
        rec = {'id': f'U{idx:05d}', 'type': 'word' if n == 1 else 'phrase', 'phrase_normalized': ph, 'phrase_nastaleeq': ' '.join(vt),
               'word_count': n, 'char_count': len(letters), 'letter_count': len(letters.replace(' ', '')), 'total_count': tot,
               'stand_alone_count': sa, 'inside_longer_count': tot - sa, 'verses_total': vlist(ps), 'verses_stand_alone': vlist(ps, alone),
               'occurrences': [{'start': verses[vi]['locs'][i], 'end': verses[vi]['locs'][i + n - 1], 'stand_alone': a}
                               for (vi, i), a in zip(ps, alone)]}
        ann.append(rec)
        csvrows.append([rec['id'], rec['type'], n, rec['char_count'], rec['letter_count'], tot, sa, ph, rec['phrase_nastaleeq'],
                        ' | '.join(rec['verses_total']), ' | '.join(rec['verses_stand_alone'])])
    path = os.path.join(T_ph.dir, sub, 'quran-phrases-annotation.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'source_layer': G.WORD_FILE, 'match_field': field,
                   'notes': 'Units are repeated single words (word_count 1) and repeated phrases (>=2 consecutive words), always inside one verse, '
                            'occurring >=2 times. phrase_normalized holds the matching form ("%s"). Locations are surah:ayah:word. '
                            'stand_alone = occurrence not part of a longer repeated unit. Words occurring once in the Quran are not included.' % field,
                   'units': ann}, f, ensure_ascii=False, separators=(',', ':'))
    T_ph.write(sub + 'quran-phrases.csv', ['id', 'type', 'word_count', 'char_count_with_spaces', 'letter_count', 'total_count', 'stand_alone_count',
                                           'phrase_normalized', 'phrase_nastaleeq', 'verses_total', 'verses_stand_alone'], csvrows)
    for r in ann:
        assert r['total_count'] == len(r['occurrences']) >= 2 and r['stand_alone_count'] + r['inside_longer_count'] == r['total_count']
        for oc in r['occurrences'][:3]:
            s0, e0 = oc['start'].rsplit(':', 1), oc['end'].rsplit(':', 1)
            assert s0[0] == e0[0]
            assert ' '.join(words[f'{s0[0]}:{kk}'][field] for kk in range(int(s0[1]), int(e0[1]) + 1)) == r['phrase_normalized']

    def cov_for(filt):
        c = bytearray(TOTAL)
        for r, (g, n, ps, al) in zip(ann, rows):
            if filt(r):
                for vi, i in ps:
                    b = offs[vi] + i
                    c[b:b + n] = b'\x01' * n
        return sum(c), c
    allc, call = cov_for(lambda r: True)
    phc, cph = cov_for(lambda r: r['word_count'] >= 2)
    ps_tot, pa, pp, va = collections.Counter(), collections.Counter(), collections.Counter(), []
    for vi, v in enumerate(verses):
        L = len(v['norm'])
        a_, p_ = sum(call[offs[vi]:offs[vi] + L]), sum(cph[offs[vi]:offs[vi] + L])
        ps_tot[v['s']] += L
        pa[v['s']] += a_
        pp[v['s']] += p_
        va.append(a_ / L)
    T_ph.write(sub + 'quran-coverage-by-surah.csv', ['surah', 'words', 'covered_words_and_phrases', 'coverage_pct_words_and_phrases', 'covered_phrases_only',
                                                      'coverage_pct_phrases_only'],
               [[s, ps_tot[s], pa[s], round(100 * pa[s] / ps_tot[s], 2), pp[s], round(100 * pp[s] / ps_tot[s], 2)] for s in sorted(ps_tot)])

    def greedy(filt, fname):
        idxs = [j for j, r in enumerate(ann) if filt(r)]
        cand = {j: (ann[j]['word_count'], sorted({offs[vi] + i + k for vi, i in rows[j][2] for k in range(ann[j]['word_count'])})) for j in idxs}
        cov = bytearray(TOTAL)
        gain = lambda j: sum(1 for p in cand[j][1] if not cov[p])
        heap = [(-gain(j) / cand[j][0], j) for j in idxs]
        heapq.heapify(heap)
        sel, cum, cost = [], 0, 0
        while heap:
            _, j = heapq.heappop(heap)
            gn = gain(j)
            if gn == 0:
                continue
            eff = gn / cand[j][0]
            if heap and eff < -heap[0][0] - 1e-12:
                heapq.heappush(heap, (-eff, j))
                continue
            for p in cand[j][1]:
                cov[p] = 1
            cum += gn
            cost += cand[j][0]
            sel.append((j, gn, cum, cost))
        T_mem.write(sub + fname, ['rank', 'id', 'type', 'text_nastaleeq', 'words_in_unit', 'total_count', 'new_words_covered', 'cumulative_words_covered',
                                  'cumulative_pct_of_quran', 'cumulative_words_to_learn'],
                    [[rk, ann[j]['id'], ann[j]['type'], ann[j]['phrase_nastaleeq'], ann[j]['word_count'], ann[j]['total_count'], gn, cm,
                      round(100 * cm / TOTAL, 2), cs] for rk, (j, gn, cm, cs) in enumerate(sel, 1)])
        return sel
    variants = [('quran-greedy-order-words-and-phrases.csv', lambda r: True), ('quran-greedy-order-phrases-only.csv', lambda r: r['type'] == 'phrase'),
                ('quran-greedy-order-words-only.csv', lambda r: r['type'] == 'word'), ('quran-greedy-order-phrases-3plus.csv', lambda r: r['word_count'] >= 3)]
    sels = {fn: greedy(f, fn) for fn, f in variants}
    assert sels['quran-greedy-order-words-and-phrases.csv'][-1][2] == allc and sels['quran-greedy-order-phrases-only.csv'][-1][2] == phc
    rep_tokens = sum(len(p) for p in rep[1].values())
    phr = [r for r in ann if r['type'] == 'phrase']

    def checkpoints(sel, Ns):
        return [{'units': N, 'words_to_learn': sel[N - 1][3], 'covered': sel[N - 1][2], 'pct': round(100 * sel[N - 1][2] / TOTAL, 2)} for N in Ns + [len(sel)] if N <= len(sel)]
    summary = {'match_field': field, 'tokens': TOTAL, 'distinct_types': len(rep[1]) + (TOTAL - rep_tokens), 'once_only_types': TOTAL - rep_tokens,
               'repeated_word_types': len(rep[1]), 'repeated_phrase_types': len(phr), 'longest_unit_words': max(rep),
               'phrases_never_stand_alone': sum(1 for r in phr if r['stand_alone_count'] == 0),
               'covered_words_and_phrases': allc, 'coverage_words_and_phrases_pct': round(100 * allc / TOTAL, 2), 'covered_phrases_only': phc,
               'coverage_phrases_only_pct': round(100 * phc / TOTAL, 2), 'uncovered_tokens': TOTAL - allc,
               'verses_fully_covered': sum(x == 1 for x in va), 'verses_ge_90': sum(x >= .9 for x in va), 'verses_ge_75': sum(x >= .75 for x in va),
               'verses_ge_50': sum(x >= .5 for x in va),
               'memorization_order': {fn: {'units_selected': len(sel), 'checkpoints': checkpoints(sel, [10, 100, 1000, 2500, 5000])} for fn, sel in sels.items()}}
    with open(os.path.join(T_ph.dir, sub, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print('  [%s] tokens %d | repeated words %d | repeated phrases %d | longest %d | coverage %.2f%% (phrases only %.2f%%)' % (
        field, TOTAL, len(rep[1]), len(phr), max(rep), 100 * allc / TOTAL, 100 * phc / TOTAL))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='output')
    a = ap.parse_args()
    out_dir = os.path.abspath(a.out_dir)
    words = G.words(out_dir)
    T_ph, T_mem = D.Table('phrases', '06_phrases', out_dir), D.Table('memorization-order', '06_phrases', out_dir)
    s1 = analyse(words, 'text_normalized', T_ph, T_mem, '', 0)
    s2 = analyse(words, 'text_exact', T_ph, T_mem, 'exact-diacritics/', 0)
    T_ph.finish({'summary': {'normalized': s1, 'exact': s2}})
    T_mem.finish()


if __name__ == '__main__':
    main()
