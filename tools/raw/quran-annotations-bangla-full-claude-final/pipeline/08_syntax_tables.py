#!/usr/bin/env python3
"""Stage 8: syntax and collocation tables, from the two JSON layers ONLY (relations, heads and constituents are the
Treebank's own annotations; the tables only count them).

Writes output/syntax/
  quran-case-by-function.csv         case ending x sentence role x head type
  quran-verb-valency.csv             per verb: with object, subject kinds, passive, preposition complement ...
  quran-verb-preposition-pairs.csv   which prepositions each verb links to
  quran-idafa-pairs.csv              possessive constructions: first term + possessor
  quran-noun-adjective-pairs.csv     noun + adjective pairs with gender / number / case agreement
  quran-preposition-usage.csv        per preposition: counts, what it governs, what it links to
  quran-particle-mood-government.csv particles x the aspect and mood of the verb they are linked to (with direction)
  quran-implicit-elements.csv        every implicit (unwritten) element; quran-implicit-elements-summary.csv groups them
  quran-constituents.csv             every marked phrase / clause; quran-constituents-summary.csv counts per tag
  quran-sentence-length-distribution.csv
  tables-report-08_syntax_tables.json
Usage: python3 pipeline/08_syntax_tables.py [--out-dir output]
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import grammar_data as G
import study_data as D

FORMS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']
CASE_ORDER = {'NOM': 0, 'ACC': 1, 'GEN': 2}
SKIP_PARTICLES = {'DET', 'P', 'CONJ'}


def is_subject(rel):
    return rel == 'Subj' or rel.lower().startswith('subj')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='output')
    a = ap.parse_args()
    out_dir = os.path.abspath(a.out_dir)
    W, S = G.load(out_dir)
    words, sents = W['words'], S['sentences']
    RD = S['reference_data']
    rel_ar = {k: v['ar'] for k, v in RD['relations'].items()}
    for need in ('Obj', 'Subj', 'link', 'Poss', 'Adj', 'gen', 'Pass', 'cog', 'circ'):
        assert need in rel_ar, need
    pos_en = {k: v['en'] for k, v in RD['pos'].items()}
    X = D.SyntaxIndex(out_dir)
    T = D.Table('syntax', '08_syntax_tables', out_dir)
    case_en = {t: v['English Description'] for t, v in W['reference_data']['features']['NominalCase']['entries'].items()}

    # ---- case x role x head type
    cf = collections.OrderedDict()
    for k, w, s in D.segments(out_dir):
        if 'case' not in s:
            continue
        node, sid = X.node(s)
        hp = 'self' if node['head'] == node['token_id'] else G.node_pos(X.head_node(sid, node))
        e = cf.setdefault((s['case'], node['rel'], hp), [0, k, w['text_indopak']])
        e[0] += 1
    tot = collections.Counter()
    for (c, r, h), e in cf.items():
        tot[c] += e[0]
    T.write('quran-case-by-function.csv', ['case', 'case_meaning', 'role', 'role_ar', 'head_pos', 'count', 'pct_of_case', 'first_word', 'example_text_indopak'],
            [[c, case_en.get(c), r, rel_ar.get(r), h, e[0], round(100 * e[0] / tot[c], 2), e[1], e[2]]
             for (c, r, h), e in sorted(cf.items(), key=lambda kv: (CASE_ORDER.get(kv[0][0], 9), -kv[1][0], kv[0][1:]))])

    # ---- verb valency + verb/preposition pairs
    val, vp = collections.OrderedDict(), collections.OrderedDict()
    for k, w in words.items():
        for vf in w['derived']['verb_forms']:
            s = X.seg[(k, vf['segment'])]
            node, sid = X.node(s)
            deps = X.dependents(sid, node)
            key = (vf['value'], s.get('lemma', {}).get('bw'))
            e = val.setdefault(key, {'lemma': s.get('lemma', {}).get('ar'), 'root': s.get('root', {}).get('ar'), 'n': 0, 'obj': 0, 'obj2': 0, 'cog': 0, 'pass': 0,
                                     'sa': 0, 'ss': 0, 'si': 0, 'prep': 0, 'circ': 0, 'gloss': collections.Counter(), 'first': k, 'text': w['text_indopak']})
            e['n'] += 1
            rels = [d['rel'] for d in deps]
            e['obj'] += 'Obj' in rels
            e['obj2'] += rels.count('Obj') >= 2
            e['cog'] += 'cog' in rels
            e['pass'] += 'Pass' in rels
            e['circ'] += 'circ' in rels
            subj = [d for d in deps if is_subject(d['rel'])]
            e['sa'] += any(not d['implicit'] and d['word'] == k for d in subj)
            e['ss'] += any(not d['implicit'] and d['word'] != k for d in subj)
            e['si'] += any(d['implicit'] for d in subj)
            if 'gloss' in s:
                e['gloss'][D.clean_gloss(s['gloss'])] += 1
            preps = [d for d in deps if d['rel'] == 'link' and G.node_pos(d) == 'P']
            e['prep'] += bool(preps)
            for d in preps:
                sp = X.seg_of(d)
                if sp is not None:
                    pid, ptxt = D.prep_id(sp), sp['text_uthmani']
                else:                                              # an implicit (unwritten) preposition
                    m = d['morphology']
                    pid, ptxt = '(implicit) ' + (m.get('lemma', {}).get('bw') or m['text_uthmani']), m['text_uthmani']
                pe = vp.setdefault((key, pid), {'n': 0, 'text': collections.Counter(), 'first': k, 'ex': w['text_indopak']})
                pe['n'] += 1
                pe['text'][ptxt] += 1
    T.write('quran-verb-valency.csv', ['form', 'lemma_bw', 'lemma_ar', 'root_ar', 'occurrences', 'with_object', 'with_two_objects', 'with_cognate_object',
                                       'with_passive_subject', 'subject_attached', 'subject_separate_word', 'subject_implicit', 'with_preposition',
                                       'with_circumstantial', 'top_glosses', 'first_word', 'example_text_indopak'],
            [[f, lb, e['lemma'], e['root'], e['n'], e['obj'], e['obj2'], e['cog'], e['pass'], e['sa'], e['ss'], e['si'], e['prep'], e['circ'],
              D.top_glosses(e['gloss']), e['first'], e['text']] for (f, lb), e in sorted(val.items(), key=lambda kv: (-kv[1]['n'], kv[0][1] or '', kv[0][0]))])
    T.write('quran-verb-preposition-pairs.csv', ['form', 'verb_bw', 'verb_ar', 'root_ar', 'preposition', 'preposition_uthmani', 'count', 'verb_occurrences',
                                                 'pct_of_verb_uses', 'first_word', 'example_text_indopak'],
            [[vkey[0], vkey[1], val[vkey]['lemma'], val[vkey]['root'], prep, D.most_common(e['text']), e['n'], val[vkey]['n'],
              round(100 * e['n'] / val[vkey]['n'], 1), e['first'], e['ex']]
             for (vkey, prep), e in sorted(vp.items(), key=lambda kv: (-kv[1]['n'], kv[0][0][1] or '', kv[0][1]))])

    # ---- idafa and noun-adjective pairs
    ida, adj = collections.OrderedDict(), collections.OrderedDict()
    for sid, s in sents.items():
        for n in s['nodes']:
            if n['implicit'] or n['rel'] not in ('Poss', 'Adj') or n['head'] == n['token_id']:
                continue
            sg, h = X.seg_of(n), s['nodes'][n['head']]
            sh = X.seg_of(h)
            if sg is None:
                continue
            first_term = X.label(h)
            if n['rel'] == 'Poss':
                poss = X.label(n) if 'lemma' in sg else '<PRON %s>' % D.pgn(sg)
                e = ida.setdefault((first_term, poss), {'n': 0, 'fa': X.label_ar(h), 'pa': sg.get('lemma', {}).get('ar') or sg['text_uthmani'], 'pos': sg['pos'],
                                                        'first': h.get('word') or n['word'], 'text': None})
                e['n'] += 1
                if e['text'] is None:
                    ws = [x for x in dict.fromkeys([h.get('word'), n['word']]) if x]
                    e['text'] = ' '.join(words[x]['text_indopak'] for x in ws)
            else:
                if sh is None:
                    continue
                e = adj.setdefault((first_term, X.label(n)), {'n': 0, 'na': X.label_ar(h), 'aa': X.label_ar(n), 'sg': 0, 'dg': 0, 'sn': 0, 'dn': 0, 'sc': 0, 'dc': 0,
                                                              'first': n['word'], 'text': words[n['word']]['text_indopak']})
                e['n'] += 1
                for f, a_, b_ in (('g', 'gender', 'gender'), ('n', 'number', 'number'), ('c', 'case', 'case')):
                    if a_ in sh and b_ in sg:
                        e['s' + f if sh[a_] == sg[b_] else 'd' + f] += 1
    T.write('quran-idafa-pairs.csv', ['first_term_bw', 'first_term_ar', 'possessor_bw', 'possessor_ar', 'possessor_pos', 'count', 'first_word', 'example_text_indopak'],
            [[k[0], e['fa'], k[1], e['pa'], e['pos'], e['n'], e['first'], e['text']] for k, e in sorted(ida.items(), key=lambda kv: (-kv[1]['n'], kv[0]))])
    T.write('quran-noun-adjective-pairs.csv', ['noun_bw', 'noun_ar', 'adjective_bw', 'adjective_ar', 'count', 'same_gender', 'different_gender', 'same_number',
                                               'different_number', 'same_case', 'different_case', 'first_word', 'example_text_indopak'],
            [[k[0], e['na'], k[1], e['aa'], e['n'], e['sg'], e['dg'], e['sn'], e['dn'], e['sc'], e['dc'], e['first'], e['text']]
             for k, e in sorted(adj.items(), key=lambda kv: (-kv[1]['n'], kv[0]))])

    # ---- preposition usage
    pu = collections.OrderedDict()
    pre_en = {t: v['English Description'] for t, v in W['reference_data']['features']['Prefixs']['entries'].items()}
    for k, w, s in D.segments(out_dir):
        if s['pos'] != 'P':
            continue
        node, sid = X.node(s)
        e = pu.setdefault(D.prep_id(s), {'n': 0, 'pref': 0, 'text': collections.Counter(), 'gl': collections.Counter(), 'gov': collections.Counter(),
                                         'govpos': collections.Counter(), 'head': collections.Counter(), 'first': k, 'ex': w['text_indopak'], 'tag': s.get('prefix')})
        e['n'] += 1
        e['pref'] += s['type'] == 'PREFIX'
        e['text'][s['text_uthmani']] += 1
        if 'gloss' in s and s['type'] != 'PREFIX':
            e['gl'][D.clean_gloss(s['gloss'])] += 1
        for d in X.dependents(sid, node):
            if d['rel'] == 'gen':
                e['gov'][X.label(d)] += 1
                e['govpos'][G.node_pos(d)] += 1
        if node['head'] != node['token_id'] and node['rel'] == 'link':
            e['head'][X.label(X.head_node(sid, node))] += 1
    T.write('quran-preposition-usage.csv', ['preposition', 'preposition_uthmani', 'meaning', 'count', 'as_prefix', 'as_separate_word', 'governs_pos_mix', 'top_governed',
                                            'top_linked_to', 'first_word', 'example_text_indopak'],
            [[p, D.most_common(e['text']), pre_en.get(e['tag']) or D.first_gloss(e['gl']), e['n'], e['pref'], e['n'] - e['pref'],
              ' | '.join('%s %d' % kv for kv in e['govpos'].most_common(4)), ' | '.join('%s (%d)' % kv for kv in e['gov'].most_common(6)),
              ' | '.join('%s (%d)' % kv for kv in e['head'].most_common(6)), e['first'], e['ex']] for p, e in sorted(pu.items(), key=lambda kv: (-kv[1]['n'], kv[0]))])

    # ---- particles and the verbs they are linked to (both directions: the Treebank makes some particles heads of the
    #      verb (negation, equation, ...) and others dependents of the verb (future, emphasis, ...))
    pm = collections.OrderedDict()

    def add_pm(pid, ps_, direction, rel, sv, k, w, text):
        mood = (sv.get('mood') or '').replace('MOOD:', '') or 'none'
        e = pm.setdefault((pid, ps_, direction, rel, sv.get('aspect', ''), mood), {'n': 0, 'text': collections.Counter(), 'first': k, 'ex': w['text_indopak']})
        e['n'] += 1
        e['text'][text] += 1
    for k, w, s in D.segments(out_dir):
        if s['pos'] in G.NOT_PARTICLES or s['pos'] in SKIP_PARTICLES:
            continue
        node, sid = X.node(s)
        pid = s.get('lemma', {}).get('bw') or s.get('prefix') or s.get('suffix') or s['text_uthmani']
        if node['head'] != node['token_id'] and node['rel'] != 'NonRel':
            sv = X.seg_of(X.head_node(sid, node))
            if sv is not None and sv['pos'] == 'V':
                add_pm(pid, s['pos'], 'particle depends on verb', node['rel'], sv, k, w, s['text_uthmani'])
        for d in X.dependents(sid, node):
            sv = X.seg_of(d)
            if sv is not None and sv['pos'] == 'V' and d['rel'] != 'NonRel':
                add_pm(pid, s['pos'], 'verb depends on particle', d['rel'], sv, k, w, s['text_uthmani'])
    ptot = collections.Counter()
    for (pid, *_), e in pm.items():
        ptot[pid] += e['n']
    T.write('quran-particle-mood-government.csv', ['particle', 'particle_uthmani', 'pos', 'pos_en', 'direction', 'relation', 'verb_aspect', 'verb_mood', 'count',
                                                   'pct_of_particle', 'first_word', 'example_text_indopak'],
            [[pid, D.most_common(e['text']), ps_, pos_en.get(ps_), dr, rl, asp, mo, e['n'], round(100 * e['n'] / ptot[pid], 1), e['first'], e['ex']]
             for (pid, ps_, dr, rl, asp, mo), e in sorted(pm.items(), key=lambda kv: (-ptot[kv[0][0]], kv[0][0], -kv[1]['n']))])

    # ---- implicit elements
    imp_rows, imp_sum = [], collections.OrderedDict()
    for sid, s in sents.items():
        for n in s['nodes']:
            if not n['implicit']:
                continue
            h = s['nodes'][n['head']]
            m = n['morphology']
            hw = h.get('word')
            ay = D.ayah_key(n['anchor']['after_word'] or n['anchor']['before_word']) if (n['anchor']['after_word'] or n['anchor']['before_word']) else None
            imp_rows.append([int(sid), n['token_id'], m['text_uthmani'], G.node_pos(n), n['rel'], rel_ar.get(n['rel']), n['head'], hw, words[hw]['text_indopak'] if hw else None,
                             G.node_pos(h), n['anchor']['after_word'], n['anchor']['before_word'], ay])
            e = imp_sum.setdefault((m['text_uthmani'], G.node_pos(n), n['rel']), [0, int(sid), ay])
            e[0] += 1
    T.write('quran-implicit-elements.csv', ['sentence_id', 'token_id', 'text_uthmani', 'pos', 'role', 'role_ar', 'head_token', 'head_word', 'head_text_indopak',
                                            'head_pos', 'after_word', 'before_word', 'ayah'], imp_rows)
    T.write('quran-implicit-elements-summary.csv', ['text_uthmani', 'pos', 'role', 'role_ar', 'count', 'first_sentence_id', 'first_ayah'],
            [[t, p, r, rel_ar.get(r), e[0], e[1], e[2]] for (t, p, r), e in sorted(imp_sum.items(), key=lambda kv: (-kv[1][0], kv[0]))])

    # ---- constituents + sentence lengths
    ctag = RD['constituent_tags']
    cons, csum = [], collections.OrderedDict()
    lens = collections.Counter()
    cross = collections.Counter()
    for sid, s in sents.items():
        lens[s['derived']['word_count']] += 1
        cross[s['derived']['word_count']] += s['span']['crosses_ayah']
        for c in s['constituents']:
            ws = c['words']
            cons.append([c['tag'], ctag.get(c['tag'], {}).get('en'), int(sid), c['first_word'], c['last_word'], D.ayah_key(ws[0]) if ws else None,
                         D.ayah_key(ws[-1]) if ws else None, len(ws), ' '.join(words[x]['text_indopak'] for x in ws), c['text']])
            e = csum.setdefault(c['tag'], {'n': 0, 'w': [], 's': set()})
            e['n'] += 1
            e['w'].append(len(ws))
            e['s'].add(sid)
    T.write('quran-constituents.csv', ['tag', 'tag_en', 'sentence_id', 'first_word', 'last_word', 'first_ayah', 'last_ayah', 'word_count', 'text_indopak', 'treebank_text'], cons)
    T.write('quran-constituents-summary.csv', ['tag', 'tag_en', 'count', 'sentences', 'average_words', 'max_words', 'with_no_written_word'],
            [[t, ctag.get(t, {}).get('en'), e['n'], len(e['s']), round(sum(e['w']) / e['n'], 2), max(e['w']), sum(1 for x in e['w'] if x == 0)]
             for t, e in sorted(csum.items(), key=lambda kv: -kv[1]['n'])])
    ns, cum = sum(lens.values()), 0
    rows = []
    for L in sorted(lens):
        cum += lens[L]
        rows.append([L, lens[L], cross[L], round(100 * lens[L] / ns, 2), round(100 * cum / ns, 2)])
    T.write('quran-sentence-length-distribution.csv', ['words_in_sentence', 'sentences', 'of_which_cross_ayah', 'pct_of_sentences', 'cumulative_pct'], rows)
    T.finish()


if __name__ == '__main__':
    main()
