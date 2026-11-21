#!/usr/bin/env python3
"""Stage 5: analysis tables and complete source-issue lists, written from the two JSON layers ONLY.

Writes output/analysis/
  quran-verb-form-summary.csv        per form I-XII: explicit / inferred / total verbs, distinct roots and lemmas
  quran-verb-form-words.csv          per form: each lemma (word) with its root and counts
  quran-root-form-summary.csv        per root: which forms it occurs in and how often
  quran-verb-form-occurrences.csv    every verb occurrence with form, basis and features
  quran-derived-form-summary.csv     derived nominals (participles, verbal nouns), kept apart from verbs
  quran-frequency-{lemmas,roots,pos,functions,particles}.csv
  source-lists/*.csv                 COMPLETE lists of merged / split / fragment / crossing / re-tagged items
  analysis-report.json               row counts per file and the hashes of the two JSON inputs
Usage: python3 pipeline/05_analysis.py [--out-dir output]
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import grammar_data as G

FORMS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='output')
    a = ap.parse_args()
    out = os.path.abspath(os.path.join(a.out_dir, 'analysis'))
    os.makedirs(os.path.join(out, 'source-lists'), exist_ok=True)
    W, S = G.load(os.path.abspath(a.out_dir))
    words, rd = W['words'], W['reference_data']
    report = {'input_sha256': {fn: sha(os.path.join(a.out_dir, fn)) for fn in (G.WORD_FILE, G.SENT_FILE)},
              'source_policy': 'computed from the two JSON layers only', 'files': {}}

    def write(rel, header, rows):
        path = os.path.join(out, rel)
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        report['files'][rel] = len(rows)

    # ---- verb forms
    rows, root_forms = G.verb_form_table(os.path.abspath(a.out_dir))
    write('quran-verb-form-summary.csv', ['form', 'description', 'pattern', 'explicit', 'inferred', 'total', 'distinct_roots', 'distinct_lemmas'],
          [[f, rd['verb_forms'][f]['description_en'], rd['verb_forms'][f]['pattern'], r['explicit'], r['inferred'], r['explicit'] + r['inferred'],
            len(r['roots']), len(r['lemmas'])] for f, r in rows.items()])
    occ, lem_rows = [], collections.OrderedDict()
    for k, w in words.items():
        for vf in w['derived']['verb_forms']:
            sg = next(s for s in w['segments'] if s['location'] == vf['segment'])
            lem, root = sg.get('lemma', {}), sg.get('root', {})
            occ.append([k, w['wbw_id'], w['text_indopak'], w['sentence_id'], vf['value'], vf['basis'], lem.get('bw'), lem.get('ar'), root.get('bw'),
                        root.get('ar'), sg.get('aspect'), sg.get('voice'), (sg.get('mood') or '').replace('MOOD:', '') or None, sg.get('person'),
                        sg.get('gender'), sg.get('number'), sg.get('gloss')])
            e = lem_rows.setdefault((vf['value'], lem.get('bw')), {'lemma': lem, 'root': root, 'explicit': 0, 'inferred': 0, 'first': k, 'text': w['text_indopak']})
            e[vf['basis']] += 1
    write('quran-verb-form-occurrences.csv', ['word', 'wbw_id', 'text_indopak', 'sentence_id', 'form', 'basis', 'lemma_bw', 'lemma_ar', 'root_bw', 'root_ar',
                                              'aspect', 'voice', 'mood', 'person', 'gender', 'number', 'gloss'], occ)
    write('quran-verb-form-words.csv', ['form', 'lemma_bw', 'lemma_ar', 'root_bw', 'root_ar', 'occurrences', 'explicit', 'inferred', 'first_word', 'example_text_indopak'],
          [[f, lb, e['lemma'].get('ar'), e['root'].get('bw'), e['root'].get('ar'), e['explicit'] + e['inferred'], e['explicit'], e['inferred'], e['first'], e['text']]
           for (f, lb), e in sorted(lem_rows.items(), key=lambda x: (FORMS.index(x[0][0]), -(x[1]['explicit'] + x[1]['inferred']), x[0][1] or ''))])
    root_ar = {}
    for w in words.values():
        for s in w['segments']:
            if 'root' in s:
                root_ar[s['root']['bw']] = s['root']['ar']
    write('quran-root-form-summary.csv', ['root_bw', 'root_ar', 'n_forms', 'forms', 'total_verbs'] + ['form_' + f for f in FORMS],
          [[r, root_ar.get(r), len(c), ' | '.join(f for f in FORMS if c[f]), sum(c.values())] + [c[f] or '' for f in FORMS]
           for r, c in sorted(root_forms.items(), key=lambda x: (-len(x[1]), -sum(x[1].values()), x[0]))])
    # ---- derived nominals
    dn = G.derived_noun_table(os.path.abspath(a.out_dir))
    pos_all = sorted({p for r in dn.values() for p in r['by_pos']})
    write('quran-derived-form-summary.csv', ['type', 'total'] + ['pos_' + p for p in pos_all] + ['distinct_roots', 'distinct_lemmas'],
          [[t, r['count']] + [r['by_pos'][p] or '' for p in pos_all] + [len(r['roots']), len(r['lemmas'])] for t, r in sorted(dn.items(), key=lambda x: -x[1]['count'])])
    # ---- frequencies
    lem, root, pos, fun, par = (collections.Counter() for _ in range(5))
    lar, rar = {}, {}
    for w in words.values():
        for s in w['segments']:
            pos[s['pos']] += 1
            if 'lemma' in s:
                lem[s['lemma']['bw']] += 1
                lar[s['lemma']['bw']] = s['lemma']['ar']
            if 'root' in s:
                root[s['root']['bw']] += 1
            if s['pos'] not in G.NOT_PARTICLES:
                par[s['pos']] += 1
        fun[w['derived']['projections']['function_without_NonRel']] += 1
    pe = S['reference_data']['pos']
    write('quran-frequency-lemmas.csv', ['lemma_bw', 'lemma_ar', 'count'], [[k, lar[k], v] for k, v in lem.most_common()])
    write('quran-frequency-roots.csv', ['root_bw', 'root_ar', 'count'], [[k, root_ar.get(k), v] for k, v in root.most_common()])
    write('quran-frequency-pos.csv', ['pos', 'pos_en', 'segments'], [[k, pe.get(k, {}).get('en'), v] for k, v in pos.most_common()])
    write('quran-frequency-functions.csv', ['function_without_NonRel', 'words'], [[k, v] for k, v in fun.most_common()])
    write('quran-frequency-particles.csv', ['pos', 'pos_en', 'segments'], [[k, pe.get(k, {}).get('en'), v] for k, v in par.most_common()])
    # ---- complete source-issue lists
    L = G.source_issue_lists(os.path.abspath(a.out_dir))
    write('source-lists/sentences-crossing-ayah.csv', ['sentence_id', 'first_word', 'last_word', 'ayah_count', 'word_count', 'ayahs'],
          [[x['sentence_id'], x['first_word'], x['last_word'], x['ayah_count'], x['word_count'], ' | '.join(x['ayahs'])] for x in L['sentences_crossing_ayah']])
    write('source-lists/words-merged-in-treebank.csv', ['treebank_word', 'treebank_text', 'wbw_word_1', 'wbw_word_2', 'segment_assignment'],
          [[m['treebank_word'], m['treebank_text'], m['wbw_words'][0], m['wbw_words'][1], '; '.join('%s->%s' % kv for kv in m['segments'].items())]
           for m in L['merged_treebank_words']])
    write('source-lists/words-split-across-sentences.csv', ['word', 'text_indopak', 'assigned_sentence', 'segment_sentences'],
          [[x['word'], x['text_indopak'], x['assigned_sentence'], '; '.join('%s=%s' % kv for kv in x['segment_sentences'].items())] for x in L['words_split_across_sentences']])
    write('source-lists/sentences-prefix-only-fragments.csv', ['sentence_id', 'nodes', 'contents', 'has_implicit_node'],
          [[x['sentence_id'], len(x['nodes']), ' + '.join('%s(%s)' % (n['text_uthmani'], n['pos']) for n in x['nodes']), any(n['implicit'] for n in x['nodes'])]
           for x in L['prefix_only_fragment_sentences']])
    write('source-lists/words-text-normalized-incomplete.csv', ['word', 'text_indopak', 'text_normalized', 'treebank_text', 'similarity'],
          [[x['word'], x['text_indopak'], x['text_normalized'], x['treebank_text'], x['similarity']] for x in L['text_normalized_incomplete']])
    write('source-lists/segments-pos-differs-from-v04.csv', ['segment', 'morphology_v04_pos', 'treebank_pos'],
          [[x['segment'], x['morphology_v04'], x['treebank']] for x in L['segments_pos_differs_from_morphology_v04']])
    with open(os.path.join(out, 'analysis-report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    for rel, n in report['files'].items():
        print('  %-52s %7d rows' % (rel, n))


if __name__ == '__main__':
    main()
