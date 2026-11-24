#!/usr/bin/env python3
"""Stage 9: reading tables and memorization orders for vocabulary, from the two JSON layers ONLY.

Writes output/reading/
  quran-surah-profile.csv            per surah: size, verbs, vocabulary, new vocabulary, coverage by the most frequent words
  quran-ayah-vocabulary-load.csv     per ayah: vocabulary load (coverage by frequent words, rare and once-only words, new words)
Writes output/memorization-order/   (greedy orders; see docs)
  quran-greedy-order-lemmas.csv                  dictionary words by frequency (cost 1 each)
  quran-greedy-order-lemmas-content-words.csv    the same without particles (nouns, verbs, adjectives, proper nouns)
  quran-greedy-order-roots.csv                   roots by occurrences per word to learn (cost = number of words of the root)
  quran-greedy-order-verbs.csv                   verbs (dictionary word + form) by frequency
  quran-greedy-order-ayahs.csv                   ayahs to read first: most new dictionary words per word read
  quran-greedy-order-surahs.csv                  the same at surah level
Usage: python3 pipeline/09_reading_tables.py [--out-dir output]
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import grammar_data as G
import study_data as D

TOPS = (100, 300, 500, 1000)
RARE = 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='output')
    a = ap.parse_args()
    out_dir = os.path.abspath(a.out_dir)
    W, S = G.load(out_dir)
    words, sents = W['words'], S['sentences']
    pos_en = {k: v['en'] for k, v in W['reference_data']['pos'].items()}
    TR, TM = D.Table('reading', '09_reading_tables', out_dir), D.Table('memorization-order', '09_reading_tables', out_dir)

    # ---- lemma statistics
    L, R, lemma_ar, root_ar, lroot = {}, {}, {}, {}, {}
    for k, w, s in D.segments(out_dir):
        if 'lemma' in s:
            lb = s['lemma']['bw']
            lemma_ar[lb] = s['lemma']['ar']
            L.setdefault(lb, D.Stats()).add(k, w, s)
        if 'root' in s:
            rb = s['root']['bw']
            root_ar[rb] = s['root']['ar']
            R.setdefault(rb, D.Stats()).add(k, w, s)
            if 'lemma' in s:
                R[rb].extra[s['lemma']['bw']] += 1
                lroot.setdefault(lb, collections.Counter())[rb] += 1
    order = sorted(L, key=lambda x: (-L[x].count, x))
    rank = {lb: i + 1 for i, lb in enumerate(order)}
    lid = {lb: i for i, lb in enumerate(order)}
    total_lemma_occ = sum(st.count for st in L.values())
    only_one_surah = {lb for lb, st in L.items() if len(st.surahs) == 1}

    # ---- per-ayah and per-surah accumulation (in Quran order)
    ay = collections.OrderedDict()
    seen = set()
    for k, w in words.items():
        e = ay.setdefault(D.ayah_key(k), {'words': [], 'segs': [], 'verbs': 0, 'new': 0, 'ids': set()})
        e['words'].append(w['text_indopak'])
        e['verbs'] += bool(w['derived']['verb_forms'])
        for s in w['segments']:
            if 'lemma' in s:
                lb = s['lemma']['bw']
                e['segs'].append(lb)
                e['ids'].add(lid[lb])
                if lb not in seen:
                    seen.add(lb)
                    e['new'] += 1
    T_ay = []
    for key, e in ay.items():
        n = len(e['segs'])
        pct = lambda N: round(100 * sum(1 for lb in e['segs'] if rank[lb] <= N) / n, 1) if n else ''
        T_ay.append([key, int(key.split(':')[0]), int(key.split(':')[1]), len(e['words']), n, len(e['ids']), pct(100), pct(500), pct(1000),
                     sum(1 for lb in e['segs'] if L[lb].count <= RARE), sum(1 for lb in e['segs'] if L[lb].count == 1), e['new'], e['verbs'], ' '.join(e['words'])])
    TR.write('quran-ayah-vocabulary-load.csv', ['ayah', 'surah', 'ayah_number', 'words', 'lemma_segments', 'distinct_lemmas', 'pct_top100_lemmas', 'pct_top500_lemmas',
                                                 'pct_top1000_lemmas', 'rare_segments_%d_or_fewer_uses' % RARE, 'once_only_segments', 'new_lemmas_first_seen_here', 'verbs',
                                                 'text_indopak'], T_ay)

    surahs = collections.OrderedDict()
    for key, e in ay.items():
        s_ = int(key.split(':')[0])
        t = surahs.setdefault(s_, {'ayahs': 0, 'words': 0, 'segs': [], 'verbs': 0, 'new': 0, 'nouns': 0, 'part': 0, 'sentences': 0})
        t['ayahs'] += 1
        t['words'] += len(e['words'])
        t['segs'] += e['segs']
        t['verbs'] += e['verbs']
        t['new'] += e['new']
    for k, w, s in D.segments(out_dir):
        t = surahs[D.surah(k)]
        t['nouns'] += s['pos'] in ('N', 'PN', 'ADJ')
        t['part'] += s['pos'] not in G.NOT_PARTICLES
    for sid, s in sents.items():
        if s['words']:
            first, last = s['span']['first_word'], s['span']['last_word']
            assert D.surah(first) == D.surah(last), sid
            surahs[D.surah(first)]['sentences'] += 1
    rows, cum = [], 0
    hapax_here = collections.Counter(D.surah(st.first) for st in L.values() if st.count == 1)
    only_here = collections.Counter(D.surah(L[lb].first) for lb in only_one_surah)
    for s_, t in surahs.items():
        cum += t['new']
        n = len(t['segs'])
        pc = lambda N: round(100 * sum(1 for lb in t['segs'] if rank[lb] <= N) / n, 1)
        rows.append([s_, t['ayahs'], t['words'], t['sentences'], round(t['words'] / t['sentences'], 2) if t['sentences'] else '', t['verbs'], t['nouns'], t['part'], n,
                     len(set(t['segs'])), t['new'], cum, only_here[s_], hapax_here[s_]] + [pc(N) for N in TOPS])
    TR.write('quran-surah-profile.csv', ['surah', 'ayahs', 'words', 'sentences', 'avg_words_per_sentence', 'verbs', 'noun_segments', 'particle_segments', 'lemma_segments',
                                         'distinct_lemmas', 'new_lemmas_first_seen_here', 'cumulative_distinct_lemmas', 'lemmas_found_only_in_this_surah',
                                         'once_only_lemmas_here'] + ['pct_top%d_lemmas' % N for N in TOPS], rows)

    # ---- memorization orders
    def lemma_order(name, filt):
        cum = 0
        rws = []
        for i, lb in enumerate([x for x in order if filt(x)], 1):
            st = L[lb]
            cum += st.count
            rws.append([i, lb, lemma_ar[lb], D.most_common(st.pos), pos_en.get(D.most_common(st.pos)), D.first_gloss(st.gloss), st.count, cum,
                        round(100 * cum / total_lemma_occ, 2), i])
        TM.write(name, ['rank', 'lemma_bw', 'lemma_ar', 'pos', 'pos_en', 'top_gloss', 'count', 'cumulative_occurrences', 'cumulative_pct_of_lemma_occurrences',
                        'cumulative_words_to_learn'], rws)
    lemma_order('quran-greedy-order-lemmas.csv', lambda lb: True)
    lemma_order('quran-greedy-order-lemmas-content-words.csv', lambda lb: D.most_common(L[lb].pos) in D.CONTENT_POS)
    ro = sorted(R, key=lambda r: (-R[r].count / len(R[r].extra), -R[r].count, r))
    tot_root = sum(R[r].count for r in R)
    cum = cost = 0
    rws = []
    for i, r in enumerate(ro, 1):
        st = R[r]
        cum += st.count
        cost += len(st.extra)
        rws.append([i, r, root_ar[r], st.count, len(st.extra), round(st.count / len(st.extra), 2), cum, round(100 * cum / tot_root, 2), cost, lemma_ar.get(D.most_common(st.extra)),
                    D.first_gloss(st.gloss)])
    TM.write('quran-greedy-order-roots.csv', ['rank', 'root_bw', 'root_ar', 'count', 'words_to_learn_for_this_root', 'occurrences_per_word', 'cumulative_occurrences',
                                              'cumulative_pct_of_root_occurrences', 'cumulative_words_to_learn', 'top_lemma_ar', 'top_gloss'], rws)
    vt = collections.OrderedDict()
    nverbs = 0
    for k, w in words.items():
        for vf in w['derived']['verb_forms']:
            s = next(g for g in w['segments'] if g['location'] == vf['segment'])
            st = vt.setdefault((s.get('lemma', {}).get('bw'), vf['value']), D.Stats())
            st.add(k, w, s)
            nverbs += 1
    total_words = len(words)
    cum = 0
    rws = []
    for i, ((lb, f), st) in enumerate(sorted(vt.items(), key=lambda kv: (-kv[1].count, kv[0][1], kv[0][0] or '')), 1):
        cum += st.count
        rws.append([i, f, lb, lemma_ar.get(lb), root_ar.get(D.most_common(lroot.get(lb, {}))), D.first_gloss(st.gloss), st.count, cum, round(100 * cum / nverbs, 2),
                    round(100 * cum / total_words, 2), i])
    TM.write('quran-greedy-order-verbs.csv', ['rank', 'form', 'lemma_bw', 'lemma_ar', 'root_ar', 'top_gloss', 'count', 'cumulative_verbs', 'cumulative_pct_of_verbs',
                                              'cumulative_pct_of_quran_words', 'cumulative_words_to_learn'], rws)

    def unit_order(name, units, labels, extra_cols, extra_vals):
        ids = [[i for i in u] for u in units]
        sel = D.greedy_cover([(c, i) for c, i in zip(costs[name], ids)], len(order))
        rws = [[rk, labels[j], costs[name][j], gn, cm, round(100 * cm / len(order), 2), cs] + extra_vals(j) for rk, (j, gn, cm, cs) in enumerate(sel, 1)]
        TM.write(name, ['rank', 'unit', 'words_in_unit', 'new_lemmas_covered', 'cumulative_lemmas_covered', 'cumulative_pct_of_lemma_types', 'cumulative_words_to_read'] + extra_cols, rws)
    costs = {}
    akeys = list(ay)
    costs['quran-greedy-order-ayahs.csv'] = [len(ay[x]['words']) for x in akeys]
    unit_order('quran-greedy-order-ayahs.csv', [sorted(ay[x]['ids']) for x in akeys], akeys, ['text_indopak'], lambda j: [' '.join(ay[akeys[j]]['words'])])
    skeys = list(surahs)
    sids = collections.defaultdict(set)
    for x in akeys:
        sids[int(x.split(':')[0])] |= ay[x]['ids']
    costs['quran-greedy-order-surahs.csv'] = [surahs[x]['words'] for x in skeys]
    unit_order('quran-greedy-order-surahs.csv', [sorted(sids[x]) for x in skeys], skeys, ['ayahs'], lambda j: [surahs[skeys[j]]['ayahs']])
    TM.finish()
    TR.finish({'notes': {'top_ranks': list(TOPS), 'rare_threshold_uses': RARE, 'lemma_segments_total': total_lemma_occ, 'lemma_types': len(order)}})


if __name__ == '__main__':
    main()
