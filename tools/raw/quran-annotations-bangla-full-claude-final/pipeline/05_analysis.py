#!/usr/bin/env python3
"""Stage 5: core analysis tables, written from the two JSON layers ONLY.

Writes output/analysis/
  quran-verb-form-summary.csv        per form I-XII: explicit / inferred / total verbs, distinct roots and lemmas
  quran-verb-form-words.csv          per form: each verb (lemma) with root, counts and its most common glosses
  quran-root-form-summary.csv        per root: which forms it occurs in and how often
  quran-verb-form-occurrences.csv    every verb occurrence with form, basis and features
  quran-derived-form-summary.csv     counts of participles / verbal nouns (kept apart from verbs)
  quran-derived-forms-words.csv      every participle / verbal noun word, with root, counts and glosses
  quran-frequency-lemmas.csv         every dictionary word with count, word type, root, glosses, surah spread, first location
  quran-frequency-roots.csv          every root with count, number of words, word-type mix, glosses, surah spread, first location
  quran-frequency-pos.csv, quran-frequency-functions.csv, quran-frequency-particles.csv
  source-lists/*.csv                 COMPLETE lists of merged / split / fragment / crossing / re-tagged items
  tables-report.json                 row counts per file and the hashes of the two JSON inputs
Usage: python3 pipeline/05_analysis.py [--out-dir output]
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import grammar_data as G
import study_data as D

FORMS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='output')
    a = ap.parse_args()
    out_dir = os.path.abspath(a.out_dir)
    W, S = G.load(out_dir)
    words, rd = W['words'], W['reference_data']
    pos_en = {k: v['en'] for k, v in rd['pos'].items()}
    T = D.Table('analysis', '05_analysis', out_dir)

    # ---- verb forms ------------------------------------------------------------------------------------------
    rows, root_forms = G.verb_form_table(out_dir)
    T.write('quran-verb-form-summary.csv', ['form', 'description', 'pattern', 'explicit', 'inferred', 'total', 'distinct_roots', 'distinct_lemmas'],
            [[f, rd['verb_forms'][f]['description_en'], rd['verb_forms'][f]['pattern'], r['explicit'], r['inferred'], r['explicit'] + r['inferred'],
              len(r['roots']), len(r['lemmas'])] for f, r in rows.items()])
    occ, lem_rows = [], collections.OrderedDict()
    for k, w in words.items():
        for vf in w['derived']['verb_forms']:
            sg = next(s for s in w['segments'] if s['location'] == vf['segment'])
            lem, root = sg.get('lemma', {}), sg.get('root', {})
            occ.append([k, w['wbw_id'], w['text_indopak'], w['sentence_id'], vf['value'], vf['basis'], lem.get('bw'), lem.get('ar'), root.get('bw'),
                        root.get('ar'), sg.get('aspect'), sg.get('voice'), (sg.get('mood') or '').replace('MOOD:', '') or None, sg.get('person'),
                        sg.get('gender'), sg.get('number'), D.clean_gloss(sg['gloss']) if 'gloss' in sg else None])
            e = lem_rows.setdefault((vf['value'], lem.get('bw')), {'lemma': lem, 'root': root, 'explicit': 0, 'inferred': 0, 'first': k,
                                                                    'text': w['text_indopak'], 'gloss': collections.Counter(), 'surahs': set()})
            e[vf['basis']] += 1
            e['surahs'].add(D.surah(k))
            if 'gloss' in sg:
                e['gloss'][D.clean_gloss(sg['gloss'])] += 1
    T.write('quran-verb-form-occurrences.csv', ['word', 'wbw_id', 'text_indopak', 'sentence_id', 'form', 'basis', 'lemma_bw', 'lemma_ar', 'root_bw', 'root_ar',
                                                'aspect', 'voice', 'mood', 'person', 'gender', 'number', 'gloss'], occ)
    T.write('quran-verb-form-words.csv', ['form', 'lemma_bw', 'lemma_ar', 'root_bw', 'root_ar', 'occurrences', 'explicit', 'inferred', 'top_glosses',
                                          'n_surahs', 'first_word', 'example_text_indopak'],
            [[f, lb, e['lemma'].get('ar'), e['root'].get('bw'), e['root'].get('ar'), e['explicit'] + e['inferred'], e['explicit'], e['inferred'],
              D.top_glosses(e['gloss']), len(e['surahs']), e['first'], e['text']]
             for (f, lb), e in sorted(lem_rows.items(), key=lambda x: (FORMS.index(x[0][0]), -(x[1]['explicit'] + x[1]['inferred']), x[0][1] or ''))])
    root_ar = {}
    for _, _, s in D.segments(out_dir):
        if 'root' in s:
            root_ar[s['root']['bw']] = s['root']['ar']
    T.write('quran-root-form-summary.csv', ['root_bw', 'root_ar', 'n_forms', 'forms', 'total_verbs'] + ['form_' + f for f in FORMS],
            [[r, root_ar.get(r), len(c), ' | '.join(f for f in FORMS if c[f]), sum(c.values())] + [c[f] or '' for f in FORMS]
             for r, c in sorted(root_forms.items(), key=lambda x: (-len(x[1]), -sum(x[1].values()), x[0]))])

    # ---- derived nominals ------------------------------------------------------------------------------------
    dn = G.derived_noun_table(out_dir)
    pos_all = sorted({p for r in dn.values() for p in r['by_pos']})
    T.write('quran-derived-form-summary.csv', ['type', 'total'] + ['pos_' + p for p in pos_all] + ['distinct_roots', 'distinct_lemmas'],
            [[t, r['count']] + [r['by_pos'][p] or '' for p in pos_all] + [len(r['roots']), len(r['lemmas'])] for t, r in sorted(dn.items(), key=lambda x: -x[1]['count'])])
    dw = collections.OrderedDict()
    lar = {}
    for k, w in words.items():
        for d in w['derived']['derived_nouns']:
            sg = next(s for s in w['segments'] if s['location'] == d['segment'])
            lb = sg.get('lemma', {}).get('bw')
            if lb is None:
                continue
            lar[lb] = sg['lemma']['ar']
            st = dw.setdefault((d['type'], lb), D.Stats())
            st.add(k, w, sg)
            if 'root' in sg:
                st.extra[sg['root']['bw']] += 1
    type_total = collections.Counter()
    for (t, _), st in dw.items():
        type_total[t] += st.count
    T.write('quran-derived-forms-words.csv', ['type', 'lemma_bw', 'lemma_ar', 'pos', 'root_bw', 'root_ar', 'count', 'top_glosses', 'n_surahs', 'first_word',
                                              'example_text_indopak'],
            [[t, lb, lar[lb], D.most_common(st.pos), D.most_common(st.extra), root_ar.get(D.most_common(st.extra)), st.count, D.top_glosses(st.gloss),
              len(st.surahs), st.first, st.text]
             for (t, lb), st in sorted(dw.items(), key=lambda x: (-type_total[x[0][0]], -x[1].count, x[0][1]))])

    # ---- frequencies -----------------------------------------------------------------------------------------
    L, R = {}, {}
    lemma_ar = {}
    pos, fun, par = collections.Counter(), collections.Counter(), collections.Counter()
    for k, w, s in D.segments(out_dir):
        pos[s['pos']] += 1
        if s['pos'] not in G.NOT_PARTICLES:
            par[s['pos']] += 1
        if 'lemma' in s:
            lb = s['lemma']['bw']
            lemma_ar[lb] = s['lemma']['ar']
            st = L.setdefault(lb, D.Stats())
            st.add(k, w, s)
            if 'root' in s:
                st.extra[s['root']['bw']] += 1
        if 'root' in s:
            rb = s['root']['bw']
            st = R.setdefault(rb, D.Stats())
            st.add(k, w, s)
            if 'lemma' in s:
                st.extra[s['lemma']['bw']] += 1
    for w in words.values():
        fun[w['derived']['projections']['function_without_NonRel']] += 1
    T.write('quran-frequency-lemmas.csv', ['lemma_bw', 'lemma_ar', 'count', 'pos', 'pos_en', 'root_bw', 'root_ar', 'top_glosses', 'n_surahs', 'first_word',
                                           'example_text_indopak'],
            [[lb, lemma_ar[lb], st.count, D.most_common(st.pos), pos_en.get(D.most_common(st.pos)), D.most_common(st.extra), root_ar.get(D.most_common(st.extra)),
              D.top_glosses(st.gloss), len(st.surahs), st.first, st.text] for lb, st in sorted(L.items(), key=lambda x: (-x[1].count, x[0]))])
    T.write('quran-frequency-roots.csv', ['root_bw', 'root_ar', 'count', 'n_lemmas', 'top_lemma_ar', 'pos_mix', 'top_glosses', 'n_surahs', 'first_word',
                                          'example_text_indopak'],
            [[rb, root_ar.get(rb), st.count, len(st.extra), lemma_ar.get(D.most_common(st.extra)),
              ' | '.join('%s %d' % kv for kv in sorted(st.pos.items(), key=lambda kv: (-kv[1], kv[0]))), D.top_glosses(st.gloss), len(st.surahs), st.first, st.text]
             for rb, st in sorted(R.items(), key=lambda x: (-x[1].count, x[0]))])
    T.write('quran-frequency-pos.csv', ['pos', 'pos_en', 'segments'], [[k, pos_en.get(k), v] for k, v in sorted(pos.items(), key=lambda x: (-x[1], x[0]))])
    T.write('quran-frequency-functions.csv', ['function_without_NonRel', 'words'], [[k, v] for k, v in sorted(fun.items(), key=lambda x: (-x[1], x[0]))])
    T.write('quran-frequency-particles.csv', ['pos', 'pos_en', 'segments'], [[k, pos_en.get(k), v] for k, v in sorted(par.items(), key=lambda x: (-x[1], x[0]))])

    # ---- complete source-issue lists -------------------------------------------------------------------------
    Li = G.source_issue_lists(out_dir)
    T.write('source-lists/sentences-crossing-ayah.csv', ['sentence_id', 'first_word', 'last_word', 'ayah_count', 'word_count', 'ayahs'],
            [[x['sentence_id'], x['first_word'], x['last_word'], x['ayah_count'], x['word_count'], ' | '.join(x['ayahs'])] for x in Li['sentences_crossing_ayah']])
    T.write('source-lists/words-merged-in-treebank.csv', ['treebank_word', 'treebank_text', 'wbw_word_1', 'wbw_word_2', 'segment_assignment'],
            [[m['treebank_word'], m['treebank_text'], m['wbw_words'][0], m['wbw_words'][1], '; '.join('%s->%s' % kv for kv in m['segments'].items())]
             for m in Li['merged_treebank_words']])
    T.write('source-lists/words-split-across-sentences.csv', ['word', 'text_indopak', 'assigned_sentence', 'segment_sentences'],
            [[x['word'], x['text_indopak'], x['assigned_sentence'], '; '.join('%s=%s' % kv for kv in x['segment_sentences'].items())] for x in Li['words_split_across_sentences']])
    T.write('source-lists/sentences-prefix-only-fragments.csv', ['sentence_id', 'nodes', 'contents', 'has_implicit_node'],
            [[x['sentence_id'], len(x['nodes']), ' + '.join('%s(%s)' % (n['text_uthmani'], n['pos']) for n in x['nodes']), any(n['implicit'] for n in x['nodes'])]
             for x in Li['prefix_only_fragment_sentences']])
    T.write('source-lists/words-text-normalized-incomplete.csv', ['word', 'text_indopak', 'text_normalized', 'treebank_text', 'similarity'],
            [[x['word'], x['text_indopak'], x['text_normalized'], x['treebank_text'], x['similarity']] for x in Li['text_normalized_incomplete']])
    T.write('source-lists/segments-pos-differs-from-v04.csv', ['segment', 'morphology_v04_pos', 'treebank_pos'],
            [[x['segment'], x['morphology_v04'], x['treebank']] for x in Li['segments_pos_differs_from_morphology_v04']])
    T.finish()


if __name__ == '__main__':
    main()
