#!/usr/bin/env python3
"""Stage 7: lexicon and morphology tables for study and linguistic work, from the two JSON layers ONLY.

Writes output/lexicon/
  quran-root-families.csv     every root with each of its words (lemma): word type, verb form, derived type, counts, glosses
  quran-surface-forms.csv     every attested written form of every dictionary word, with its grammatical features
  quran-verb-paradigms.csv    attested verb conjugations: form x tense x voice x mood x person-gender-number
  quran-noun-features.csv     nouns / adjectives / proper nouns by case, definiteness, gender, number
  quran-pronouns.csv          every pronoun (independent and attached) with person, gender, number, host and role
  quran-pronouns-summary.csv  the same grouped by person / gender / number / role (spellings merged)
  quran-affixes.csv           every prefix and suffix tag with meaning, counts and what it attaches to
  quran-function-words.csv    particles, relatives, demonstratives, time/place words (lemma level)
  quran-special-groups.csv    kana / inna / kada and their sisters, word by word
  quran-hapax-lemmas.csv      dictionary words that occur only once
  quran-hapax-roots.csv       roots that occur only once
  quran-proper-nouns.csv      proper nouns
  tables-report-07_lexicon_tables.json
Usage: python3 pipeline/07_lexicon_tables.py [--out-dir output]
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
    W = G.load(out_dir)[0]
    words, rd = W['words'], W['reference_data']
    X = D.SyntaxIndex(out_dir)
    pos_en = {k: v['en'] for k, v in rd['pos'].items()}
    feats = rd['features']
    T = D.Table('lexicon', '07_lexicon_tables', out_dir)

    # ---- per-lemma and per-root statistics (all segments that carry a lemma / root)
    L, R, lemma_ar, root_ar = {}, {}, {}, {}
    lf, ld, lroot = {}, {}, {}                                # lemma -> verb forms / derived types / roots seen
    fam = collections.defaultdict(dict)                       # root -> lemma -> Stats
    surf = collections.OrderedDict()
    for k, w, s in D.segments(out_dir):
        if 'lemma' not in s:
            continue
        lb = s['lemma']['bw']
        lemma_ar[lb] = s['lemma']['ar']
        L.setdefault(lb, D.Stats()).add(k, w, s)
        vf = D.verb_form_by_segment(w).get(s['location'])
        dt = D.derived_type_by_segment(w).get(s['location'])
        if vf:
            lf.setdefault(lb, collections.Counter())[vf] += 1
        if dt:
            ld.setdefault(lb, collections.Counter())[dt] += 1
        if 'root' in s:
            rb = s['root']['bw']
            root_ar[rb] = s['root']['ar']
            lroot.setdefault(lb, collections.Counter())[rb] += 1
            R.setdefault(rb, D.Stats()).add(k, w, s)
            fam[rb].setdefault(lb, D.Stats()).add(k, w, s)
        mood = (s.get('mood') or '').replace('MOOD:', '')
        key = (lb, w['text_indopak'], s['pos'], vf or '', s.get('aspect', ''), s.get('voice', ''), mood, s.get('person', ''), s.get('gender', ''),
               s.get('number', ''), s.get('case', ''), s.get('state', ''))
        e = surf.setdefault(key, [0, k])
        e[0] += 1

    # ---- root families
    T.write('quran-root-families.csv', ['root_bw', 'root_ar', 'root_count', 'lemma_bw', 'lemma_ar', 'pos', 'verb_form', 'derived_type', 'count', 'top_glosses',
                                        'n_surahs', 'first_word', 'example_text_indopak'],
            [[rb, root_ar[rb], R[rb].count, lb, lemma_ar[lb], D.most_common(st.pos), D.most_common(lf.get(lb, {})), D.most_common(ld.get(lb, {})), st.count,
              D.top_glosses(st.gloss), len(st.surahs), st.first, st.text]
             for rb in sorted(fam, key=lambda r: (-R[r].count, r)) for lb, st in sorted(fam[rb].items(), key=lambda x: (-x[1].count, x[0]))])

    # ---- surface forms
    T.write('quran-surface-forms.csv', ['lemma_bw', 'lemma_ar', 'text_indopak', 'pos', 'verb_form', 'aspect', 'voice', 'mood', 'person', 'gender', 'number', 'case',
                                        'state', 'count', 'first_word'],
            [[k[0], lemma_ar[k[0]]] + list(k[1:]) + [v[0], v[1]]
             for k, v in sorted(surf.items(), key=lambda kv: (-L[kv[0][0]].count, kv[0][0], -kv[1][0], kv[0][1]))])

    # ---- verb paradigms
    para = collections.OrderedDict()
    for k, w in words.items():
        for vf in w['derived']['verb_forms']:
            s = next(g for g in w['segments'] if g['location'] == vf['segment'])
            mood = (s.get('mood') or '').replace('MOOD:', '')
            key = (vf['value'], s.get('aspect', ''), s.get('voice', ''), mood, D.pgn(s))
            e = para.setdefault(key, {'count': 0, 'lemmas': set(), 'first': k, 'text': w['text_indopak'], 'lemma': s.get('lemma', {}).get('ar'),
                                      'gloss': D.clean_gloss(s['gloss']) if 'gloss' in s else None, 'person': s.get('person', ''), 'gender': s.get('gender', ''),
                                      'number': s.get('number', '')})
            e['count'] += 1
            e['lemmas'].add(s.get('lemma', {}).get('bw'))
    asp = {'PERF': 0, 'IMPF': 1, 'IMPV': 2}
    T.write('quran-verb-paradigms.csv', ['form', 'aspect', 'voice', 'mood', 'person_gender_number', 'person', 'gender', 'number', 'count', 'distinct_verbs',
                                         'example_word', 'example_text_indopak', 'example_verb', 'example_gloss'],
            [[f, ap_, vo, mo, p, e['person'], e['gender'], e['number'], e['count'], len(e['lemmas']), e['first'], e['text'], e['lemma'], e['gloss']]
             for (f, ap_, vo, mo, p), e in sorted(para.items(), key=lambda kv: (FORMS.index(kv[0][0]), asp.get(kv[0][1], 9), kv[0][2], kv[0][3], kv[0][4]))])

    # ---- noun features
    nf = collections.OrderedDict()
    for k, w, s in D.segments(out_dir):
        if s['pos'] not in ('N', 'ADJ', 'PN'):
            continue
        has_det = any(g['pos'] == 'DET' for g in w['segments'])
        defin = 'definite (Al-)' if has_det else ('indefinite (marked)' if s.get('state') == 'INDEF' else 'unmarked')
        key = (s['pos'], s.get('case', ''), defin, s.get('gender', ''), s.get('number', ''), D.derived_type_by_segment(w).get(s['location'], ''))
        e = nf.setdefault(key, {'count': 0, 'lemmas': set(), 'first': k, 'text': w['text_indopak']})
        e['count'] += 1
        e['lemmas'].add(s.get('lemma', {}).get('bw'))
    case_en = {t: v['English Description'] for t, v in feats['NominalCase']['entries'].items()}
    T.write('quran-noun-features.csv', ['pos', 'case', 'case_meaning', 'definiteness', 'gender', 'number', 'derived_type', 'count', 'distinct_lemmas',
                                        'first_word', 'example_text_indopak'],
            [[p, c, case_en.get(c), d, g, n, dt, e['count'], len(e['lemmas']), e['first'], e['text']]
             for (p, c, d, g, n, dt), e in sorted(nf.items(), key=lambda kv: (kv[0][0], kv[0][1], -kv[1]['count']))])

    # ---- pronouns (no lemma in the notes, so counted by form)
    pr = collections.OrderedDict()
    for k, w, s in D.segments(out_dir):
        if s['pos'] != 'PRON':
            continue
        i = w['segments'].index(s)
        prev = w['segments'][i - 1] if i else None
        attached = s['type'] == 'SUFFIX' or (prev is not None and prev['pos'] == 'P')
        node, _ = X.node(s)
        key = (s['text_uthmani'], s.get('person', ''), s.get('gender', ''), s.get('number', ''), 'attached' if attached else 'independent',
               prev['pos'] if attached and prev else '', node['rel'])
        e = pr.setdefault(key, [0, k, w['text_indopak']])
        e[0] += 1
    T.write('quran-pronouns.csv', ['pronoun_uthmani', 'person', 'gender', 'number', 'attached', 'host_pos', 'role', 'count', 'first_word', 'example_text_indopak'],
            [list(k) + v for k, v in sorted(pr.items(), key=lambda kv: (-kv[1][0], kv[0]))])

    ps = collections.OrderedDict()
    for (txt, pe, ge, nu, att, host, role), (cnt, first, ex) in pr.items():
        e = ps.setdefault((pe, ge, nu, att, host, role), {'count': 0, 'spellings': collections.Counter(), 'first': first, 'ex': ex})
        e['count'] += cnt
        e['spellings'][txt] += cnt
    T.write('quran-pronouns-summary.csv', ['person', 'gender', 'number', 'attached', 'host_pos', 'role', 'count', 'n_spellings', 'top_spellings_uthmani', 'first_word',
                                           'example_text_indopak'],
            [list(k) + [e['count'], len(e['spellings']), ' | '.join('%s (%d)' % kv for kv in e['spellings'].most_common(5)), e['first'], e['ex']]
             for k, e in sorted(ps.items(), key=lambda kv: (-kv[1]['count'], kv[0]))])

    # ---- affixes
    pre_en = {t: v['English Description'] for t, v in feats['Prefixs']['entries'].items()}
    suf_en = {t: v['English Description'] for t, v in feats['Suffixs']['entries'].items()}
    af = collections.OrderedDict()
    for k, w, s in D.segments(out_dir):
        if s['type'] == 'STEM':
            continue
        tag = s.get('prefix') if s['type'] == 'PREFIX' else s.get('suffix')
        if tag is None:
            continue
        stem = next((g for g in w['segments'] if g['type'] == 'STEM'), None)
        e = af.setdefault((s['type'], tag), {'count': 0, 'pos': collections.Counter(), 'text': collections.Counter(), 'host': collections.Counter(),
                                              'first': k, 'ex': w['text_indopak']})
        e['count'] += 1
        e['pos'][s['pos']] += 1
        e['text'][s['text_uthmani']] += 1
        e['host'][stem['pos'] if stem else ''] += 1
    T.write('quran-affixes.csv', ['kind', 'tag', 'pos', 'pos_en', 'meaning', 'most_common_text_uthmani', 'count', 'attaches_to_most', 'attaches_to_mix', 'first_word',
                                  'example_text_indopak'],
            [[kind, tag, D.most_common(e['pos']), pos_en.get(D.most_common(e['pos'])), (pre_en if kind == 'PREFIX' else suf_en).get(tag),
              D.most_common(e['text']), e['count'], D.most_common(e['host']), ' | '.join('%s %d' % kv for kv in e['host'].most_common(4)), e['first'], e['ex']]
             for (kind, tag), e in sorted(af.items(), key=lambda kv: (kv[0][0] != 'PREFIX', -kv[1]['count'], kv[0][1]))])

    # ---- function words (lemma level) and hapax / proper nouns
    wp = collections.defaultdict(lambda: [0, 0])
    for k, w, s in D.segments(out_dir):
        if 'lemma' in s and D.most_common(L[s['lemma']['bw']].pos) not in D.CONTENT_POS:
            wp[s['lemma']['bw']][0] += any(g['type'] == 'PREFIX' for g in w['segments'])
            wp[s['lemma']['bw']][1] += any(g['type'] == 'SUFFIX' for g in w['segments'])
    T.write('quran-function-words.csv', ['lemma_bw', 'lemma_ar', 'pos', 'pos_en', 'count', 'with_prefix', 'with_suffix', 'top_glosses', 'n_surahs', 'first_word',
                                         'example_text_indopak'],
            [[lb, lemma_ar[lb], D.most_common(L[lb].pos), pos_en.get(D.most_common(L[lb].pos)), L[lb].count, wp[lb][0], wp[lb][1], D.top_glosses(L[lb].gloss),
              len(L[lb].surahs), L[lb].first, L[lb].text]
             for lb in sorted(wp, key=lambda x: (-L[x].count, x))])
    sg = collections.OrderedDict()
    sp_en = {t: v['English Description'] for t, v in feats['SpecialGroup']['entries'].items()}
    for k, w, s in D.segments(out_dir):
        if 'special_group' in s:
            e = sg.setdefault((s['special_group'], s.get('lemma', {}).get('bw')), D.Stats())
            e.add(k, w, s)
    T.write('quran-special-groups.csv', ['group', 'group_meaning', 'lemma_bw', 'lemma_ar', 'pos', 'count', 'top_glosses', 'first_word', 'example_text_indopak'],
            [[g, sp_en.get(g), lb, lemma_ar.get(lb), D.most_common(e.pos), e.count, D.top_glosses(e.gloss), e.first, e.text]
             for (g, lb), e in sorted(sg.items(), key=lambda kv: (kv[0][0], -kv[1].count, str(kv[0][1])))])
    T.write('quran-hapax-lemmas.csv', ['lemma_bw', 'lemma_ar', 'pos', 'pos_en', 'root_bw', 'root_ar', 'gloss', 'word', 'text_indopak', 'surah'],
            [[lb, lemma_ar[lb], D.most_common(st.pos), pos_en.get(D.most_common(st.pos)), D.most_common(lroot.get(lb, {})), root_ar.get(D.most_common(lroot.get(lb, {}))),
              D.first_gloss(st.gloss), st.first, st.text, D.surah(st.first)]
             for lb, st in sorted(L.items(), key=lambda kv: tuple(int(x) for x in kv[1].first.split(':'))) if st.count == 1])
    T.write('quran-hapax-roots.csv', ['root_bw', 'root_ar', 'lemma_ar', 'pos', 'gloss', 'word', 'text_indopak', 'surah'],
            [[rb, root_ar[rb], next((g['lemma']['ar'] for g in words[st.first]['segments'] if g.get('root', {}).get('bw') == rb), None), D.most_common(st.pos),
              D.first_gloss(st.gloss), st.first, st.text, D.surah(st.first)]
             for rb, st in sorted(R.items(), key=lambda kv: tuple(int(x) for x in kv[1].first.split(':'))) if st.count == 1])
    T.write('quran-proper-nouns.csv', ['lemma_bw', 'lemma_ar', 'count', 'n_surahs', 'top_glosses', 'first_word', 'example_text_indopak'],
            [[lb, lemma_ar[lb], st.count, len(st.surahs), D.top_glosses(st.gloss), st.first, st.text]
             for lb, st in sorted(L.items(), key=lambda kv: (-kv[1].count, kv[0])) if D.most_common(st.pos) == 'PN'])
    T.finish()


if __name__ == '__main__':
    main()
