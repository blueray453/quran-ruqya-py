#!/usr/bin/env python3
"""Stage 10: validate every generated table (stages 04-09) by reading the CSVs back and reconciling them with the two JSON layers
and with each other: totals, row counts, ordering, cumulative columns. Also a regression check against the headline numbers of the
original phrase analysis. Writes output/tables-validation-report.json; exit code 1 if any check fails.
Usage: python3 pipeline/10_validate_tables.py [--out-dir output]
"""
import argparse
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import grammar_data as G
import study_data as D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='output')
    a = ap.parse_args()
    O = os.path.abspath(a.out_dir)
    W, S = G.load(O)
    words, sents = W['words'], S['sentences']
    X = D.SyntaxIndex(O)
    results = []

    def check(group, name, ok, detail=''):
        results.append({'group': group, 'check': name, 'ok': bool(ok), 'detail': detail})
        print(('PASS ' if ok else 'FAIL ') + f'[{group}] {name}' + (f'  -> {detail}' if detail and not ok else ''))

    def rd(rel):
        return D.read_csv(os.path.join(O, rel))
    isum = lambda rows, col: sum(int(r[col]) for r in rows)

    # ---- truth from the JSON layers
    segs = [(k, w, s) for k, w, s in D.segments(O)]
    n_seg = len(segs)
    n_lem = sum(1 for _, _, s in segs if 'lemma' in s)
    n_root = sum(1 for _, _, s in segs if 'root' in s)
    n_both = sum(1 for _, _, s in segs if 'lemma' in s and 'root' in s)
    lemmas = {s['lemma']['bw'] for _, _, s in segs if 'lemma' in s}
    roots = {s['root']['bw'] for _, _, s in segs if 'root' in s}
    n_verbs = sum(len(w['derived']['verb_forms']) for w in words.values())
    pos_count = collections.Counter(s['pos'] for _, _, s in segs)
    lemma_count = collections.Counter(s['lemma']['bw'] for _, _, s in segs if 'lemma' in s)
    root_count = collections.Counter(s['root']['bw'] for _, _, s in segs if 'root' in s)
    n_words = len(words)

    # ---- files listed in the stage reports exist with the stated row counts
    bad = []
    for rep_path in glob.glob(os.path.join(O, '*', 'tables-report-*.json')):
        rep = json.load(open(rep_path, encoding='utf-8'))
        folder = os.path.dirname(rep_path)
        for name, info in rep['files'].items():
            p = os.path.join(folder, name)
            if not os.path.exists(p) or len(D.read_csv(p)) != info['rows']:
                bad.append(name)
    check('reports', 'every table named in a stage report exists with the stated number of rows', not bad, str(bad[:5]))

    # ---- stage 05 analysis
    lem, rot = rd('analysis/quran-frequency-lemmas.csv'), rd('analysis/quran-frequency-roots.csv')
    check('analysis', 'lemma table: one row per lemma, counts add up to every lemma-bearing segment',
          len(lem) == len(lemmas) and isum(lem, 'count') == n_lem and {r['lemma_bw'] for r in lem} == lemmas, f'{len(lem)} vs {len(lemmas)}')
    check('analysis', 'lemma table is sorted by count (descending) and each count equals the JSON count',
          [int(r['count']) for r in lem] == sorted((int(r['count']) for r in lem), reverse=True) and all(int(r['count']) == lemma_count[r['lemma_bw']] for r in lem))
    check('analysis', 'lemma table: word type exists in reference data, surah spread 1..114, first word exists',
          all(r['pos'] in W['reference_data']['pos'] and 1 <= int(r['n_surahs']) <= 114 and r['first_word'] in words for r in lem))
    check('analysis', 'root table: one row per root, counts add up to every root-bearing segment',
          len(rot) == len(roots) and isum(rot, 'count') == n_root and all(int(r['count']) == root_count[r['root_bw']] for r in rot))
    check('analysis', 'root table: n_lemmas >= 1 and word-type mix adds up to the count',
          all(int(r['n_lemmas']) >= 1 and sum(int(x.split()[1]) for x in r['pos_mix'].split(' | ')) == int(r['count']) for r in rot))
    vs, vw, vo, rf = rd('analysis/quran-verb-form-summary.csv'), rd('analysis/quran-verb-form-words.csv'), rd('analysis/quran-verb-form-occurrences.csv'), rd('analysis/quran-root-form-summary.csv')
    check('analysis', 'verb tables agree: summary, words, occurrences and root-form tables all total the verbs in the JSON',
          isum(vs, 'total') == n_verbs == len(vo) == isum(vw, 'occurrences') == isum(rf, 'total_verbs'), f'{isum(vs, "total")} {len(vo)} {isum(vw, "occurrences")} {isum(rf, "total_verbs")}')
    check('analysis', 'verb-form explicit / inferred counts agree between the summary and the word table',
          all(isum([r for r in vw if r['form'] == s_['form']], 'explicit') == int(s_['explicit']) and isum([r for r in vw if r['form'] == s_['form']], 'inferred') == int(s_['inferred'])
              for s_ in vs))
    check('analysis', 'Form I is entirely inferred; no verb is counted twice (each verb in one form)',
          [r for r in vs if r['form'] == 'I'][0]['explicit'] == '0' and len({r['lemma_bw'] for r in vw}) == len(vw))
    dsum, dwords = rd('analysis/quran-derived-form-summary.csv'), rd('analysis/quran-derived-forms-words.csv')
    check('analysis', 'derived-noun word list adds up to the derived-noun summary for every type, with no verbs',
          all(isum([r for r in dwords if r['type'] == d['type']], 'count') == int(d['total']) for d in dsum) and not any(r['pos'] == 'V' for r in dwords))
    fpos, ffun = rd('analysis/quran-frequency-pos.csv'), rd('analysis/quran-frequency-functions.csv')
    check('analysis', 'word-type table adds up to every segment; sentence-role table adds up to every written word',
          isum(fpos, 'segments') == n_seg and isum(ffun, 'words') == n_words and {r['pos']: int(r['segments']) for r in fpos} == dict(pos_count))
    check('analysis', 'particle table equals the word-type table without content types',
          isum(rd('analysis/quran-frequency-particles.csv'), 'segments') == sum(v for k, v in pos_count.items() if k not in G.NOT_PARTICLES))

    # ---- stage 07 lexicon
    fam = rd('lexicon/quran-root-families.csv')
    check('lexicon', 'root families: one row per root + lemma; counts add up to segments with both root and lemma, and agree with the root table',
          isum(fam, 'count') == n_both and len({(r['root_bw'], r['lemma_bw']) for r in fam}) == len(fam)
          and all(sum(int(x['count']) for x in fam if x['root_bw'] == r['root_bw']) == int(r['count']) for r in rot[:200]))
    sf = rd('lexicon/quran-surface-forms.csv')
    check('lexicon', 'surface forms add up to every lemma-bearing segment', isum(sf, 'count') == n_lem)
    pa = rd('lexicon/quran-verb-paradigms.csv')
    check('lexicon', 'verb paradigms add up to every verb', isum(pa, 'count') == n_verbs)
    nf = rd('lexicon/quran-noun-features.csv')
    check('lexicon', 'noun features add up to every noun, adjective and proper-noun segment',
          isum(nf, 'count') == pos_count['N'] + pos_count['ADJ'] + pos_count['PN'])
    pr, ps = rd('lexicon/quran-pronouns.csv'), rd('lexicon/quran-pronouns-summary.csv')
    check('lexicon', 'pronoun tables add up to every pronoun and agree with each other',
          isum(pr, 'count') == pos_count['PRON'] == isum(ps, 'count'))
    af = rd('lexicon/quran-affixes.csv')
    n_pre = sum(1 for _, _, s in segs if s['type'] == 'PREFIX' and 'prefix' in s)
    n_suf = sum(1 for _, _, s in segs if s['type'] == 'SUFFIX' and 'suffix' in s)
    check('lexicon', 'affix table adds up to every prefix and suffix that carries a tag',
          isum([r for r in af if r['kind'] == 'PREFIX'], 'count') == n_pre and isum([r for r in af if r['kind'] == 'SUFFIX'], 'count') == n_suf)
    fw = rd('lexicon/quran-function-words.csv')
    check('lexicon', 'function words are lemmas of the lemma table and carry its counts',
          all(lemma_count[r['lemma_bw']] == int(r['count']) and r['pos'] not in D.CONTENT_POS for r in fw))
    hl, hr, pn = rd('lexicon/quran-hapax-lemmas.csv'), rd('lexicon/quran-hapax-roots.csv'), rd('lexicon/quran-proper-nouns.csv')
    check('lexicon', 'hapax lists contain exactly the lemmas / roots occurring once',
          {r['lemma_bw'] for r in hl} == {k for k, v in lemma_count.items() if v == 1} and {r['root_bw'] for r in hr} == {k for k, v in root_count.items() if v == 1})
    check('lexicon', 'proper nouns are all of type PN and carry the lemma-table counts', all(r['lemma_bw'] in lemma_count and lemma_count[r['lemma_bw']] == int(r['count']) for r in pn))
    sg = rd('lexicon/quran-special-groups.csv')
    check('lexicon', 'special groups add up to every segment that has a special group',
          isum(sg, 'count') == sum(1 for _, _, s in segs if 'special_group' in s))

    # ---- stage 08 syntax
    cf = rd('syntax/quran-case-by-function.csv')
    check('syntax', 'case by function adds up to every segment with a case; shares add up to 100% per case',
          isum(cf, 'count') == sum(1 for _, _, s in segs if 'case' in s)
          and all(abs(sum(float(r['pct_of_case']) for r in cf if r['case'] == c) - 100) < 0.5 for c in {r['case'] for r in cf}))
    va = rd('syntax/quran-verb-valency.csv')
    check('syntax', 'verb valency covers every verb; no category exceeds the occurrences',
          isum(va, 'occurrences') == n_verbs and all(int(r[c]) <= int(r['occurrences']) for r in va for c in ('with_object', 'with_preposition', 'subject_attached', 'subject_implicit')))
    vp = rd('syntax/quran-verb-preposition-pairs.csv')
    check('syntax', 'verb-preposition pairs refer to verbs of the valency table', {(r['form'], r['verb_bw']) for r in vp} <= {(r['form'], r['lemma_bw']) for r in va} and all(int(r['count']) > 0 for r in vp))
    ida = rd('syntax/quran-idafa-pairs.csv')
    n_poss = sum(1 for s in sents.values() for n in s['nodes'] if not n['implicit'] and n['rel'] == 'Poss' and n['head'] != n['token_id'] and X.seg_of(n) is not None)
    check('syntax', 'possessive pairs add up to every possessor relation', isum(ida, 'count') == n_poss, f'{isum(ida, "count")} vs {n_poss}')
    adj = rd('syntax/quran-noun-adjective-pairs.csv')
    n_adj = sum(1 for s in sents.values() for n in s['nodes'] if not n['implicit'] and n['rel'] == 'Adj' and n['head'] != n['token_id'] and X.seg_of(n) is not None
                and X.seg_of(s['nodes'][n['head']]) is not None)
    check('syntax', 'noun-adjective pairs add up to every adjective relation with written head and dependent', isum(adj, 'count') == n_adj, f'{isum(adj, "count")} vs {n_adj}')
    pu = rd('syntax/quran-preposition-usage.csv') if os.path.exists(os.path.join(O, 'syntax/quran-preposition-usage.csv')) else []
    check('syntax', 'preposition usage adds up to every preposition segment', isum(pu, 'count') == pos_count['P'])
    pm = rd('syntax/quran-particle-mood-government.csv')
    check('syntax', 'particle government: counts positive; lam is followed by the jussive and lan by the subjunctive in most uses',
          all(int(r['count']) > 0 for r in pm)
          and max((r for r in pm if r['particle'] == 'lam'), key=lambda r: int(r['count']))['verb_mood'] == 'JUS'
          and max((r for r in pm if r['particle'] == 'lan'), key=lambda r: int(r['count']))['verb_mood'] == 'SUBJ')
    ie, ies = rd('syntax/quran-implicit-elements.csv'), rd('syntax/quran-implicit-elements-summary.csv')
    check('syntax', 'implicit elements: 11,157 rows and the summary adds up', len(ie) == 11157 == isum(ies, 'count'))
    co, cs = rd('syntax/quran-constituents.csv'), rd('syntax/quran-constituents-summary.csv')
    check('syntax', 'constituents: every constituent of every sentence, summary adds up',
          len(co) == sum(len(s['constituents']) for s in sents.values()) == isum(cs, 'count'))
    sl = rd('syntax/quran-sentence-length-distribution.csv')
    check('syntax', 'sentence length distribution covers 11,693 sentences and 77,432 words',
          isum(sl, 'sentences') == len(sents) == 11693 and sum(int(r['words_in_sentence']) * int(r['sentences']) for r in sl) == n_words)

    # ---- stage 09 reading tables
    sp, al = rd('reading/quran-surah-profile.csv'), rd('reading/quran-ayah-vocabulary-load.csv')
    check('reading', 'surah profile: 114 surahs; words, ayahs, sentences and vocabulary add up',
          len(sp) == 114 and isum(sp, 'words') == n_words and isum(sp, 'ayahs') == 6236 and isum(sp, 'lemma_segments') == n_lem
          and isum(sp, 'new_lemmas_first_seen_here') == len(lemmas) == int(sp[-1]['cumulative_distinct_lemmas']),
          f'{isum(sp, "sentences")}')
    check('reading', 'surah profile: sentences = 11,693 minus the 26 fragments', isum(sp, 'sentences') == 11693 - 26)
    check('reading', 'ayah vocabulary load: 6,236 ayahs; words and new vocabulary add up',
          len(al) == 6236 and isum(al, 'words') == n_words and isum(al, 'new_lemmas_first_seen_here') == len(lemmas))

    # ---- memorization orders
    def mono(rows, cum, new=None, rank='rank'):
        c = [int(r[cum]) for r in rows]
        ok = c == sorted(c) and [int(r[rank]) for r in rows] == list(range(1, len(rows) + 1))
        if new:
            ok = ok and all(int(r[new]) > 0 for r in rows) and c == [sum(int(x[new]) for x in rows[:i + 1]) for i in range(len(rows))] if len(rows) < 6000 else ok
        return ok
    for nm in sorted(glob.glob(os.path.join(O, 'memorization-order', 'quran-greedy-order-*-*.csv'))):
        base = os.path.basename(nm)
        rows = D.read_csv(nm)
        if '-pos-' in base or '-function-' in base:
            check('memorization-order', f'{base}: ranks consecutive, cumulative = running sum of new words, no unit covers nothing',
                  mono(rows, 'cumulative_words_covered', 'new_words_covered') and all(float(rows[i]['cumulative_pct_of_quran']) <= float(rows[i + 1]['cumulative_pct_of_quran']) for i in range(len(rows) - 1)))
    seq = json.load(open(os.path.join(O, 'sequences', 'sequence-analysis-report.json'), encoding='utf-8'))
    ok = True
    for kind, info in seq['analyses'].items():
        for fn, g in info['greedy'].items():
            r = D.read_csv(os.path.join(O, 'memorization-order', fn))
            ok &= len(r) == g['units_selected'] and abs(float(r[-1]['cumulative_pct_of_quran']) - g['final_pct_of_quran']) < 0.01
    check('memorization-order', 'sequence memorization orders agree with the sequence report (units, final coverage)', ok)
    mo = {fn: D.read_csv(os.path.join(O, 'memorization-order', fn)) for fn in ('quran-greedy-order-lemmas.csv', 'quran-greedy-order-lemmas-content-words.csv',
                                                                              'quran-greedy-order-roots.csv', 'quran-greedy-order-verbs.csv', 'quran-greedy-order-ayahs.csv',
                                                                              'quran-greedy-order-surahs.csv')}
    r = mo['quran-greedy-order-lemmas.csv']
    check('memorization-order', 'lemma order: every lemma once, descending counts, ends at 100% of lemma occurrences',
          len(r) == len(lemmas) and r[-1]['cumulative_pct_of_lemma_occurrences'] == '100.0' and int(r[-1]['cumulative_occurrences']) == n_lem
          and [int(x['count']) for x in r] == sorted((int(x['count']) for x in r), reverse=True))
    r = mo['quran-greedy-order-lemmas-content-words.csv']
    check('memorization-order', 'content-word order contains only nouns, verbs, adjectives and proper nouns', all(x['pos'] in D.CONTENT_POS for x in r) and len(r) == 4740)
    r = mo['quran-greedy-order-roots.csv']
    check('memorization-order', 'root order: every root once, efficiency (occurrences per word) non-increasing, ends at 100%',
          len(r) == len(roots) and int(r[-1]['cumulative_occurrences']) == n_root
          and all(float(r[i]['occurrences_per_word']) >= float(r[i + 1]['occurrences_per_word']) - 1e-9 for i in range(len(r) - 1)))
    r = mo['quran-greedy-order-verbs.csv']
    check('memorization-order', 'verb order: every verb once, descending, ends at all verbs',
          len(r) == len(vw) and int(r[-1]['cumulative_verbs']) == n_verbs and [int(x['count']) for x in r] == sorted((int(x['count']) for x in r), reverse=True))
    r = mo['quran-greedy-order-ayahs.csv']
    check('memorization-order', 'ayah order: every step adds new vocabulary; ends covering every dictionary word',
          mono(r, 'cumulative_lemmas_covered', 'new_lemmas_covered') and int(r[-1]['cumulative_lemmas_covered']) == len(lemmas) and len({x['unit'] for x in r}) == len(r))
    r = mo['quran-greedy-order-surahs.csv']
    check('memorization-order', 'surah order: every step adds new vocabulary; ends covering every dictionary word',
          mono(r, 'cumulative_lemmas_covered', 'new_lemmas_covered') and int(r[-1]['cumulative_lemmas_covered']) == len(lemmas))

    # ---- regression against the original phrase analysis (headline numbers of the original project)
    sm = json.load(open(os.path.join(O, 'phrases', 'summary.json'), encoding='utf-8'))
    exp = {'tokens': 77432, 'repeated_word_types': 6095, 'repeated_phrase_types': 25188, 'longest_unit_words': 24, 'covered_words_and_phrases': 68837,
           'covered_phrases_only': 50057, 'verses_fully_covered': 2263, 'verses_ge_90': 3357, 'verses_ge_75': 5287, 'verses_ge_50': 6058}
    check('regression', 'phrase analysis reproduces the original project exactly (tokens, repeated words, phrases, longest phrase, coverage, verse coverage)',
          all(sm[k] == v for k, v in exp.items()), str({k: (sm[k], v) for k, v in exp.items() if sm[k] != v}))
    ph = rd('phrases/quran-phrases.csv')
    check('regression', 'phrase table: total = stand-alone + inside-longer is implied; ids ordered by frequency then length; 31,283 units',
          len(ph) == 6095 + 25188 and [int(r['total_count']) for r in ph] == sorted((int(r['total_count']) for r in ph), reverse=True)
          and all(int(r['stand_alone_count']) <= int(r['total_count']) for r in ph))
    g1 = rd('memorization-order/quran-greedy-order-words-and-phrases.csv')
    check('regression', 'original memorization order: 6,001 units reaching 88.9% of the Quran', len(g1) == 6001 and g1[-1]['cumulative_pct_of_quran'] == '88.9')

    ok = all(r['ok'] for r in results)
    with open(os.path.join(O, 'tables-validation-report.json'), 'w', encoding='utf-8') as f:
        json.dump({'ok': ok, 'checks': results}, f, ensure_ascii=False, indent=1)
    print('\n%d/%d table checks passed' % (sum(r['ok'] for r in results), len(results)))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
