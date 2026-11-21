#!/usr/bin/env python3
"""Build the two canonical annotation layers for the IndoPak Nastaleeq Quran files.

  output/indopak-nastaleeq-wbw-grammar-normalized.json       word layer      (morphology)
  output/indopak-nastaleeq-sentence-grammar-normalized.json  sentence layer  (syntax)

The layers ANNOTATE indopak-nastaleeq-wbw.json / indopak-nastaleeq.json; they never change or
re-define that text. Word keys are the WBW keys (surah:ayah:word). Source of all grammar:
data/Quranic/Quranic.csv (Quranic Treebank). See docs/SCHEMA.md for every field and rule.

Usage: python3 pipeline/02_build_json.py [--data-dir data] [--out-dir output] [--normalized build/...] [--pretty]
"""
import argparse
import collections
import hashlib
import json
import os
import re
import difflib
import sqlite3
import sys
import unicodedata

import openpyxl

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import schema_map as S

SCHEMA_VERSION = '1.0.0'
WORD_FILE = 'indopak-nastaleeq-wbw-grammar-normalized.json'
SENT_FILE = 'indopak-nastaleeq-sentence-grammar-normalized.json'
ORDINALS = ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth', 'Tenth',
            'Eleventh', 'Twelfth']
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12}
MOOD_EN = {'IND': 'Indicative mood', 'JUS': 'Jussive mood', 'SUBJ': 'Subjunctive mood'}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def jload(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)



# ----------------------------------------------------------------------------- word alignment WBW <-> Treebank
_VARIANTS = {'ٱ': 'ا', 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٲ': 'ا', 'ى': 'ي', 'ی': 'ي', 'ئ': 'ي', 'ؤ': 'و', 'ة': 'ه', 'ہ': 'ه',
             'ھ': 'ه', 'ک': 'ك', 'ء': '', 'ـ': '', 'ۥ': '', 'ۦ': ''}


def skeleton(text):
    """Consonant skeleton used ONLY to align the IndoPak words with the Uthmani Treebank words (never stored as text)."""
    t = ''.join(c for c in text if not unicodedata.category(c).startswith('M') and not c.isspace()
                and not 0xE000 <= ord(c) <= 0xF8FF)
    return ''.join(_VARIANTS.get(c, c) for c in t)


def ratio(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def align_ayah(wbw, tb):
    """wbw, tb: lists of skeletons. Minimum-cost alignment allowing 1:1, 2:1 (merge) and 1:2 (split) word groups.
    Returns [(wbw_indexes, tb_indexes), ...]."""
    n, m = len(wbw), len(tb)
    INF = 1e9
    cost = [[INF] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    cost[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            c = cost[i][j]
            if c >= INF:
                continue
            opts = []
            if i < n and j < m:
                opts.append((i + 1, j + 1, 1 - ratio(wbw[i], tb[j])))
            if i + 1 < n and j < m:
                opts.append((i + 2, j + 1, 1 - ratio(wbw[i] + wbw[i + 1], tb[j]) + 0.05))
            if i < n and j + 1 < m:
                opts.append((i + 1, j + 2, 1 - ratio(wbw[i], tb[j] + tb[j + 1]) + 0.05))
            for ni, nj, d in opts:
                if c + d < cost[ni][nj]:
                    cost[ni][nj], back[ni][nj] = c + d, (i, j)
    i, j, groups = n, m, []
    while (i, j) != (0, 0):
        pi, pj = back[i][j]
        groups.append((list(range(pi, i)), list(range(pj, j))))
        i, j = pi, pj
    return groups[::-1]


def split_segments(rows, targets):
    """Distribute the segments of one merged Treebank word over its WBW words by consonant skeleton."""
    out, k = [], 0
    for t in targets:
        part, acc = [], ''
        while k < len(rows) and acc != t:
            acc += skeleton(rows[k]['uthmani_token'])
            part.append(rows[k])
            k += 1
        if acc != t:
            raise ValueError('cannot split segments %s over %s' % ([r['location'] for r in rows], targets))
        out.append(part)
    if k != len(rows):
        raise ValueError('segments left over: ' + str([r['location'] for r in rows[k:]]))
    return out


def align_words(normalized, rows):
    """Map every Treebank row to the WBW word it belongs to.

    The IndoPak WBW text and the (Uthmani) Treebank sometimes split the text into words differently. Ayahs with the
    same number of words are aligned 1:1; the others are aligned by text (3 ayahs, each with the Treebank word
    'baEdamaA' = two WBW words). Returns (row_word {tid: 'surah:ayah:word'}, merges [...])."""
    tb = collections.OrderedDict()
    for r in rows:
        p = S.parse_loc(r['location'])
        if p:
            tb.setdefault((p[0], p[1]), collections.OrderedDict()).setdefault(p[2], []).append(r)
    wbw = collections.defaultdict(list)
    for k, v in normalized.items():
        if v['normalized']:
            sx, ax, wx = map(int, k.split(':'))
            wbw[(sx, ax)].append((wx, v['normalized']))
    row_word, merges = {}, []
    for ay in sorted(wbw):
        W_ = sorted(wbw[ay])
        T = list(tb[ay].items())
        if len(W_) == len(T):
            groups = [([i], [i]) for i in range(len(W_))]
        else:
            groups = align_ayah([skeleton(t) for _, t in W_], [skeleton(''.join(x['uthmani_token'] for x in rs)) for _, rs in T])
        for wi, ti in groups:
            if len(ti) != 1:
                raise ValueError('Treebank word split over several WBW words is not supported: %s' % (ay,))
            tnum, trows = T[ti[0]]
            keys = ['%d:%d:%d' % (ay[0], ay[1], W_[i][0]) for i in wi]
            if len(keys) == 1:
                parts = [trows]
            else:
                parts = split_segments(trows, [skeleton(W_[i][1]) for i in wi])
                merges.append(collections.OrderedDict([
                    ('treebank_word', '%d:%d:%d' % (ay[0], ay[1], tnum)), ('wbw_words', keys),
                    ('treebank_text', ''.join(x['uthmani_token'] for x in trows)),
                    ('segments', {r['location'][1:-1]: k for k, part in zip(keys, parts) for r in part})]))
            for k, part in zip(keys, parts):
                for r in part:
                    row_word[int(r['tid'])] = k
    return row_word, merges


# ----------------------------------------------------------------------------- reference data
def read_feature_guide(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = {}
    for ws in wb:
        rows = [['' if c is None else str(c).strip() for c in r] for r in ws.iter_rows(values_only=True)]
        rows = [r for r in rows if any(r)]
        hdr = rows[0]
        tag_i = hdr.index('Tag') if 'Tag' in hdr else None
        entries = {}
        if tag_i is not None:
            id_first = hdr[0].lower() == 'id'
            for r in rows[1:]:
                if id_first and not r[0].isdigit():
                    break                                    # a title line / sub-table starts here
                if len(r) > tag_i and r[tag_i]:
                    entries[r[tag_i]] = dict(zip(hdr, r))
        sheets[ws.title] = {'columns': hdr, 'entries': entries, 'rows': rows}
    return sheets


def build_reference(data_dir):
    q = os.path.join(data_dir, 'Quranic')
    pos = {r['pos']: {'id': int(r['pid']), 'ar': r['pos_ar'], 'en': r['pos_en']} for r in S.read_tsv16(os.path.join(q, 'CAPoS.csv'))}
    rel = {r['rel_en']: {'id': int(r['rel_id']), 'ar': r['rel_ar']} for r in S.read_tsv16(os.path.join(q, 'RelLabels.csv'))}
    ctag = {r['tag']: {'id': int(r['pid']), 'ar': r['tag_ar'], 'en': r['tag_en']} for r in S.read_tsv16(os.path.join(q, 'ConstituentsTags.csv'))}
    roots = {r['root']: {'ar': r['root_ar'], 'size': int(r['size'])} for r in S.read_tsv16(os.path.join(q, 'CARootLexicon.csv'))}
    lemmas = {r['lemma']: {'ar': r['lemma_ar'], 'size': int(r['size'])} for r in S.read_tsv16(os.path.join(q, 'CALemmaLexicon.csv'))}
    feats = read_feature_guide(os.path.join(q, 'CAMorphFeatures.xlsx'))

    corrections = []
    verb_forms = {}
    for tag, e in feats['VerbForm']['entries'].items():
        value = tag.strip('()')
        n = ROMAN[value]
        src_en = e['English Description']
        m = re.match(r'(\w+) form', src_en)
        corrected = ORDINALS[n - 1] + ' form' + (' (default)' if value == 'I' else '')
        flagged = not (m and m.group(1) == ORDINALS[n - 1])
        verb_forms[value] = {'tag': tag, 'number': n, 'ar': e['Arabic Description'], 'pattern': e['Pattern'],
                             'source_description_en': src_en, 'description_en': corrected,
                             'source_description_flagged': flagged}
        if flagged:
            corrections.append({'table': 'VerbForm', 'key': tag, 'field': 'English Description', 'source': src_en,
                                'corrected': corrected,
                                'reason': 'English ordinal does not match the form number given by the tag and the Arabic pattern'})
    verb_moods = {}
    for tag, e in feats['VerbMood']['entries'].items():
        src_en = e['English Description']
        verb_moods[tag] = {'ar': e['Arabic Description'], 'source_description_en': src_en,
                           'description_en': MOOD_EN.get(tag, src_en), 'source_description_flagged': MOOD_EN.get(tag, src_en) != src_en}
        if MOOD_EN.get(tag, src_en) != src_en:
            corrections.append({'table': 'VerbMood', 'key': tag, 'field': 'English Description', 'source': src_en,
                                'corrected': MOOD_EN[tag],
                                'reason': 'English description contradicts the Arabic term (JUS = majzum = jussive; SUBJ = mansub = subjunctive)'})
    return {'pos': pos, 'relations': rel, 'constituent_tags': ctag, 'roots': roots, 'lemmas': lemmas,
            'features': feats, 'verb_forms': verb_forms, 'verb_moods': verb_moods,
            'corrections': corrections}


def secondary_db(data_dir):
    spec = {'stem': ('word-stem.db', 'select w.word_location, s.id, s.text from stem_words w join stems s on s.id=w.stem_id'),
            'lemma': ('word-lemma.db', 'select w.word_location, s.id, s.text from lemma_words w join lemmas s on s.id=w.lemma_id'),
            'root': ('word-root.db', 'select w.word_location, s.id, s.arabic_trilateral from root_words w join roots s on s.id=w.root_id')}
    out = collections.defaultdict(dict)
    for kind, (fn, sql) in spec.items():
        con = sqlite3.connect('file:' + os.path.join(data_dir, fn) + '?mode=ro', uri=True)
        for loc, i, text in con.execute(sql + ' order by 1, 2'):
            out[loc].setdefault(kind, []).append({'id': i, 'text': text})
        con.close()
    return out


# ----------------------------------------------------------------------------- main build
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', default='data')
    ap.add_argument('--out-dir', default='output')
    ap.add_argument('--normalized', default='build/indopak-nastaleeq-wbw-normalized.json', help='stage 1 output')
    ap.add_argument('--pretty', action='store_true', help='indent the JSON (much larger files)')
    a = ap.parse_args()
    D = a.data_dir
    os.makedirs(a.out_dir, exist_ok=True)

    wbw = jload(os.path.join(D, 'indopak-nastaleeq-wbw.json'))
    normalized = jload(a.normalized)
    header, rows = S.read_treebank(os.path.join(D, 'Quranic', 'Quranic.csv'))
    ref = build_reference(D)
    sec_db = secondary_db(D)
    inputs = {fn: sha256(os.path.join(D, fn)) for fn in
              ['indopak-nastaleeq.json', 'indopak-nastaleeq-wbw.json',
               'quranic-corpus-morphology-0.4.txt', 'Quranic/Quranic.csv', 'Quranic/CAPoS.csv', 'Quranic/RelLabels.csv',
               'Quranic/ConstituentsTags.csv', 'Quranic/CARootLexicon.csv', 'Quranic/CALemmaLexicon.csv',
               'Quranic/CAMorphFeatures.xlsx', 'word-stem.db', 'word-lemma.db', 'word-root.db']}

    inputs['indopak-nastaleeq-wbw-normalized.json'] = sha256(a.normalized)      # stage 1 output, identical to the supplied file
    # ---- align Treebank words with WBW words (text based), then group rows
    row_word, merges = align_words(normalized, rows)
    word_rows = collections.OrderedDict()                  # WBW key 'surah:ayah:word' -> rows
    sent_rows = collections.OrderedDict()                  # sentence_id -> rows
    for r in rows:
        sent_rows.setdefault(int(r['sentence_id']), []).append(r)
        k = row_word.get(int(r['tid']))
        if k:
            word_rows.setdefault(k, []).append(r)

    # a word belongs to the sentence of its (first) STEM segment; its segments keep their own sentence ids
    word_sid = {}
    for k, rs in word_rows.items():
        stem = next(r for r in rs if r['segment'] == 'STEM')
        word_sid[k] = int(stem['sentence_id'])

    # ---- the written words, in text order (verse-end markers are not words)
    word_keys = sorted((k for k, v in normalized.items() if v['normalized']),
                       key=lambda k: tuple(int(x) for x in k.split(':')))
    by_ayah = collections.defaultdict(list)
    for k in word_keys:
        by_ayah['%s:%s' % tuple(k.split(':')[:2])].append(k)
    neighbors = {}
    for ks in by_ayah.values():
        for i, k in enumerate(ks):
            neighbors[k] = {'prev': ks[i - 1] if i else None, 'next': ks[i + 1] if i + 1 < len(ks) else None}

    # ---- word layer
    words = collections.OrderedDict()
    stats = collections.Counter()
    word_proj = {}
    for k in word_keys:
        w, n = wbw[k], normalized[k]
        rec = collections.OrderedDict()
        rec['wbw_id'] = w['id']
        rec['text_indopak'] = w['text']
        rec['text_normalized'] = n['normalized']
        rec['text_exact'] = n['exact']
        if 'restored_from' in n:
            rec['restored_from'] = n['restored_from']
        rs = word_rows.get(k)
        if rs is None:
            rec['annotation_status'] = 'absent_in_treebank'
            rec['sentence_id'] = None
            rec['segments'] = []
            stats['words_absent_in_treebank'] += 1
        else:
            rec['annotation_status'] = 'annotated'
            rec['sentence_id'] = word_sid[k]
            segs = []
            for r in rs:
                seg = collections.OrderedDict()
                seg['treebank_tid'] = int(r['tid'])
                seg['location'] = r['location'][1:-1]
                seg.update(S.build_morph(r))
                seg['syntax_ref'] = {'sentence_id': int(r['sentence_id']), 'token_id': int(r['token_id'])}
                segs.append(seg)
            rec['segments'] = segs
            stems = [r for r in rs if r['segment'] == 'STEM']
            nonrel = [r['rel_label'] for r in rs if r['rel_label'] != 'NonRel']
            proj = {'pos_stem': '+'.join(r['pos'] for r in stems),
                    'pos_all_segments': '+'.join(r['pos'] for r in rs),
                    'function_all': '+'.join(r['rel_label'] for r in rs),
                    'function_without_NonRel': '+'.join(nonrel) if nonrel else 'NonRel',
                    'function_stem': '+'.join(r['rel_label'] for r in stems)}
            word_proj[k] = proj
            verb_forms, nominal_forms, dnouns = [], [], []
            for r in stems:
                loc = r['location'][1:-1]
                if r['pos'] == 'V':
                    raw = S.val(r['verb_form'])
                    verb_forms.append({'segment': loc, 'value': raw.strip('()') if raw else 'I',
                                       'basis': 'explicit' if raw else 'inferred'})
                elif S.val(r['verb_form']):
                    nominal_forms.append({'segment': loc, 'pos': r['pos'], 'form_raw': r['verb_form']})
                if S.val(r['derived_nouns']):
                    dnouns.append({'segment': loc, 'pos': r['pos'], 'type': r['derived_nouns']})
            stats['verb_words'] += bool(verb_forms)
            for vf in verb_forms:
                stats['verb_form_' + vf['basis']] += 1
            stats['nonverb_form_annotations'] += len(nominal_forms)
            stats['derived_noun_annotations'] += len(dnouns)
            stats['split_words'] += len({int(r['sentence_id']) for r in rs}) > 1
            rec['derived'] = collections.OrderedDict([
                ('is_verb', bool(verb_forms)),
                ('verb_forms', verb_forms),
                ('nominal_form_annotations', nominal_forms),
                ('derived_nouns', dnouns),
                ('prefix_tags', [r['prefix'] for r in rs if r['segment'] == 'PREFIX' and S.val(r['prefix'])]),
                ('suffix_tags', [r['suffix'] for r in rs if r['segment'] == 'SUFFIX' and S.val(r['suffix'])]),
                ('n_segments', len(rs)),
                ('neighbors', neighbors[k]),
                ('projections', proj),
            ])
            stats['segments'] += len(rs)
        if k in sec_db:
            rec['secondary_db'] = sec_db[k]
        words[k] = rec

    # ---- sentence layer
    sentences = collections.OrderedDict()
    for sid, rs in sent_rows.items():
        nodes, last_word = [], None
        for r in rs:
            p = S.parse_loc(r['location'])
            wk = row_word.get(int(r['tid']))
            node = collections.OrderedDict()
            node['token_id'] = int(r['token_id'])
            node['treebank_tid'] = int(r['tid'])
            node['sentence_word'] = int(r['sentence_word'])
            if p:
                last_word = wk
                node['implicit'] = False
                node['word'] = wk
                node['segment'] = r['location'][1:-1]
                if word_sid[wk] != sid:
                    node['word_in_sentence'] = word_sid[wk]
                node['pos'] = r['pos']
            else:
                node['implicit'] = True
                node['word'] = None
                for c in ('chapter_id', 'verse_id', 'word_id', 'tok_id'):
                    node[c] = r[c]
                node['anchor'] = {'after_word': last_word, 'before_word': None}
                node['morphology'] = S.build_morph(r)
            node.update(S.build_syntax(r))
            nodes.append(node)
        # fill 'before_word' for implicit nodes
        nxt = None
        for node in reversed(nodes):
            if node['implicit']:
                node['anchor']['before_word'] = nxt
            elif node['word']:
                nxt = node['word']
        swords = []
        for node in nodes:
            wk = node['word']
            if wk and word_sid[wk] == sid and wk not in swords:
                swords.append(wk)
        ayahs = []
        for wk in (swords or [n['word'] for n in nodes if n['word']]):
            ay = '%s:%s' % tuple(wk.split(':')[:2])
            if ay not in ayahs:
                ayahs.append(ay)
        cons = []
        last_tid = len(nodes) - 1
        for node in nodes:
            loc = node.get('constituents_loc')
            if not loc:
                continue
            for a_, b_ in re.findall(r'\[(\d+)-(\d+)\]', loc):
                a_, b_ = int(a_), int(b_)
                ws = []
                for nd in nodes[a_:b_ + 1]:
                    if nd['word'] and nd['word'] not in ws:
                        ws.append(nd['word'])
                cons.append(collections.OrderedDict([
                    ('tag', node.get('constituent_label')), ('token_span', [a_, b_]),
                    ('source_token_id', node['token_id']), ('first_word', ws[0] if ws else None),
                    ('last_word', ws[-1] if ws else None), ('words', ws), ('text', node.get('constituents_text'))]))
        posseq = {'stem': [word_proj[w]['pos_stem'] for w in swords],
                  'all_segments': [word_proj[w]['pos_all_segments'] for w in swords]}
        funseq = {'all': [word_proj[w]['function_all'] for w in swords],
                  'without_NonRel': [word_proj[w]['function_without_NonRel'] for w in swords],
                  'stem': [word_proj[w]['function_stem'] for w in swords]}
        sentences[str(sid)] = collections.OrderedDict([
            ('sentence_id', sid),
            ('span', collections.OrderedDict([('first_word', swords[0] if swords else None),
                                              ('last_word', swords[-1] if swords else None),
                                              ('ayahs', ayahs), ('crosses_ayah', len(ayahs) > 1)])),
            ('words', swords),
            ('nodes', nodes),
            ('constituents', cons),
            ('derived', collections.OrderedDict([
                ('word_count', len(swords)), ('node_count', len(nodes)),
                ('implicit_node_count', sum(n['implicit'] for n in nodes)),
                ('is_prefix_only_fragment', not swords),
                ('split_words', sorted({n['word'] for n in nodes if n.get('word_in_sentence')})),
                ('root_nodes', [{'token_id': n['token_id'], 'word': n['word'], 'pos': n.get('pos')}
                                for n in nodes if n.get('rel') == 'root']),
                ('pos_sequence', posseq), ('function_sequence', funseq)])),
        ])
        stats['nodes'] += len(nodes)
        stats['implicit_nodes'] += sum(n['implicit'] for n in nodes)
        stats['crossing_sentences'] += len(ayahs) > 1
        stats['sentences_without_assigned_words'] += not swords

    # ---- source inconsistencies (reported, never "fixed")
    rel_ar = {k: v['ar'] for k, v in ref['relations'].items()}
    pos_ar = {k: v['ar'] for k, v in ref['pos'].items()}
    issues = {
        'rows_rel_label_ar_differs_from_RelLabels': sum(1 for r in rows if rel_ar.get(r['rel_label']) not in (None, r['rel_label_ar'])),
        'rows_pos_ar_differs_from_CAPoS': sum(1 for r in rows if pos_ar.get(r['pos']) not in (None, r['pos_ar'])),
        'rel_labels_missing_from_RelLabels': sorted({r['rel_label'] for r in rows} - set(rel_ar)),
        'pos_missing_from_CAPoS': sorted({r['pos'] for r in rows} - set(pos_ar)),
        'roots_missing_from_CARootLexicon': sorted({r['root'] for r in rows if r['root'] != '_'} - set(ref['roots'])),
        'lemmas_missing_from_CALemmaLexicon': sorted({r['lemma'] for r in rows if r['lemma'] != '_'} - set(ref['lemmas'])),
        'feature_guide_corrections': len(ref['corrections']),
    }
    v04 = {}
    with open(os.path.join(D, 'quranic-corpus-morphology-0.4.txt'), encoding='utf-8') as f:
        for line in f:
            if line.startswith('('):
                q = line.rstrip('\r\n').split('\t')
                v04[q[0][1:-1]] = q
    pos_diff = [{'segment': r['location'][1:-1], 'morphology_v04': v04[r['location'][1:-1]][2], 'treebank': r['pos']}
                for r in rows if r['location'] != '_' and v04[r['location'][1:-1]][2] != r['pos']]
    issues['segments_pos_differs_from_morphology_v04'] = {
        'count': len(pos_diff),
        'note': 'features_raw still carries the v0.4 POS; the Treebank pos column re-tags these segments (e.g. N -> T). '
                'The Treebank pos is the value stored in "pos".',
        'transitions': dict(collections.Counter(d['morphology_v04'] + '->' + d['treebank'] for d in pos_diff)),
        'segments': pos_diff}
    source_row_pairs = {
        'treebank_rows': len(rows), 'treebank_rows_with_word_location': sum(len(v) for v in word_rows.values()),
        'treebank_rows_implicit': len(rows) - sum(len(v) for v in word_rows.values())}
    absent = [k for k in word_keys if k not in word_rows]
    outliers = []
    for k, w in words.items():
        if w['segments']:
            a_, b_ = skeleton(w['text_normalized']), skeleton(''.join(sg['text_uthmani'] for sg in w['segments']))
            r_ = ratio(a_, b_)
            if r_ < 0.7:
                outliers.append({'word': k, 'text_indopak': w['text_indopak'], 'text_normalized': w['text_normalized'],
                                 'treebank_text': ''.join(sg['text_uthmani'] for sg in w['segments']), 'similarity': round(r_, 2)})
    issues['text_normalized_incomplete'] = {
        'note': 'The IndoPak font stores some letter clusters as one private-use glyph, which the supplied normalized text drops. '
                'These words are aligned correctly; only text_normalized is short. The Treebank spelling is listed for reference.',
        'words': outliers}
    markers = sum(1 for v in normalized.values() if not v['normalized'])

    def meta(layer, extra):
        m = collections.OrderedDict([
            ('schema_version', SCHEMA_VERSION), ('layer', layer),
            ('description', 'Annotation layer for indopak-nastaleeq-wbw.json / indopak-nastaleeq.json. '
                            'It never changes or re-defines the Quran text; records are keyed by the WBW location.'),
            ('text_authority', {fn: inputs[fn] for fn in ('indopak-nastaleeq.json', 'indopak-nastaleeq-wbw.json')}),
            ('input_sha256', inputs),
            ('grammar_source', 'Quranic Arabic Corpus / Quranic Treebank (data/Quranic/Quranic.csv); morphology v0.4 cross-checked by validate.py'),
            ('null_policy', 'A source value "_" means no value; the JSON key is absent. lemma_ar / root_ar hold the placeholder '
                            '"\u0640" in the source whenever lemma / root is absent; it is re-created on round trip, not stored.'),
            ('derived_policy', 'Everything under a "derived" key, plus the sentence-level "constituents" list, is computed '
                               'by this project from original annotations; original annotations are never replaced.')])
        m.update(extra)
        return m

    word_meta = meta('word-morphology', collections.OrderedDict([
        ('counts', collections.OrderedDict([
            ('words', len(words)), ('verse_end_markers_excluded', markers),
            ('words_annotated', len(words) - len(absent)), ('words_absent_in_treebank', len(absent)),
            ('segments', stats['segments']), ('words_with_verb_stem', stats['verb_words']),
            ('verb_form_explicit', stats['verb_form_explicit']), ('verb_form_inferred_I', stats['verb_form_inferred']),
            ('non_verb_segments_with_form_annotation', stats['nonverb_form_annotations']),
            ('derived_noun_annotations', stats['derived_noun_annotations']),
            ('words_split_across_sentences', stats['split_words'])])),
        ('words_absent_in_treebank', absent),
        ('word_alignment', collections.OrderedDict([
            ('method', 'Treebank (Uthmani) and WBW (IndoPak) split the text into words differently in 3 ayahs: the Treebank writes '
                       'baEdamaA as ONE word with two segments, WBW writes two words. Ayahs with equal word counts are aligned 1:1; '
                       'these 3 are aligned by text (minimum-cost alignment) and the merged word\'s segments are distributed over '
                       'the two WBW words. Segment locations stay the original Treebank locations.'),
            ('treebank_words', len({'%d:%d:%d' % S.parse_loc(r['location'])[:3] for r in rows if r['location'] != '_'})),
            ('wbw_words', len(words)),
            ('merged_treebank_words', merges),
            ('ayahs_with_shifted_word_numbers', sorted({m['treebank_word'].rsplit(':', 1)[0] for m in merges}))])),
        ('derivation_rules', collections.OrderedDict([
            ('sentence_id', 'sentence of the first STEM segment; each segment keeps its own sentence id in syntax_ref'),
            ('verb_forms', 'only STEM segments with pos V. explicit: Form given in the Treebank. inferred: no Form given -> Form I '
                           '(the default stated in CAMorphFeatures.xlsx). Form I is never explicit in the source.'),
            ('nominal_form_annotations', 'non-verb STEM segments that carry a verb_form value; never counted as verbs'),
            ('projections', 'whole-word labels joined with "+" in segment order. pos_stem / function_stem use STEM segments only; '
                            'pos_all_segments / function_all use every segment; function_without_NonRel drops NonRel '
                            '(a word whose only label is NonRel keeps "NonRel").')])),
        ('source_issues', issues)]))
    sent_meta = meta('sentence-syntax', collections.OrderedDict([
        ('counts', collections.OrderedDict([
            ('sentences', len(sentences)), ('nodes', stats['nodes']), ('implicit_nodes', stats['implicit_nodes']),
            ('sentences_crossing_ayah', stats['crossing_sentences']),
            ('sentences_without_assigned_words', stats['sentences_without_assigned_words']),
            ('words_referenced', sum(len(s['words']) for s in sentences.values()))])),
        ('node_rules', collections.OrderedDict([
            ('token_id', 'row index inside the sentence; head and constituent spans refer to token_id'),
            ('head', 'Treebank ref_token_id; a root node or NonRel node points to itself'),
            ('implicit', 'Treebank rows without a Quranic word location (e.g. an unspoken subject); kept, not part of "words"'),
            ('anchor', 'implicit nodes: nearest written words before / after, so a UI can place them without altering the text'),
            ('word_in_sentence', 'present when a segment belongs to a word assigned to a different sentence (41 words)')])),
        ('source_row_accounting', source_row_pairs),
        ('source_issues', collections.OrderedDict([
            ('prefix_only_fragment_sentences', [int(k) for k, v in sentences.items() if not v['words']]),
            ('prefix_only_fragment_note', 'Treebank sentences that contain only the prefix segments of a word whose stem starts the next '
                                          'sentence (25 are two prefixes; one is a prefix plus an implicit node). They are kept (original ids and boundaries are preserved) but own no written word.')]))]))

    word_ref = {k: ref[k] for k in ('pos', 'features', 'verb_forms', 'verb_moods', 'roots', 'lemmas', 'corrections')}
    sent_ref = {k: ref[k] for k in ('pos', 'relations', 'constituent_tags')}
    dump = dict(ensure_ascii=False, indent=1) if a.pretty else dict(ensure_ascii=False, separators=(',', ':'))
    for fn, doc in ((WORD_FILE, {'metadata': word_meta, 'reference_data': word_ref, 'words': words}),
                    (SENT_FILE, {'metadata': sent_meta, 'reference_data': sent_ref, 'sentences': sentences})):
        path = os.path.join(a.out_dir, fn)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, **dump)
        print('wrote', path, '%.1f MB' % (os.path.getsize(path) / 1e6))
    print(json.dumps(word_meta['counts'], indent=1))
    print(json.dumps(sent_meta['counts'], indent=1))


if __name__ == '__main__':
    main()
