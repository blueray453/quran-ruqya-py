#!/usr/bin/env python3
"""Validate the two annotation layers against the supplied source files.

Hard checks (exit code 1 if any fails):
  inputs        input files unchanged (data/CHECKSUMS.sha256 and metadata hashes)
  alignment     word layer keys == the written words of indopak-nastaleeq-wbw.json (text and id equal)
  lossless      every one of the 139,376 Treebank rows, all 43 columns, is re-created exactly from the two JSON files;
                each row is stored exactly once per owning layer
  structure     sentence ids, token ids, heads, constituent spans, word <-> sentence membership
  derived       projections, verb forms and sequences recomputed independently from original fields
  reference     every POS / relation / constituent tag / form / case value used is defined in reference_data
  cross-check   Quranic Corpus morphology v0.4 agrees with the Treebank on every segment (pos + feature string)
Informational (reported, never "fixed"): source inconsistencies.

Usage: python3 src/validate.py [--data-dir data] [--out-dir output]
"""
import argparse
import collections
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_map as S

WORD_FILE = 'indopak-nastaleeq-wbw-grammar-normalized.json'
SENT_FILE = 'indopak-nastaleeq-sentence-grammar-normalized.json'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def jload(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', default='data')
    ap.add_argument('--out-dir', default='output')
    a = ap.parse_args()
    D, O = a.data_dir, a.out_dir
    results, info = [], collections.OrderedDict()

    def check(group, name, ok, detail=''):
        results.append({'group': group, 'check': name, 'ok': bool(ok), 'detail': detail})
        print(('PASS ' if ok else 'FAIL ') + f'[{group}] {name}' + (f'  -> {detail}' if detail and not ok else ''))

    WD, SD = jload(os.path.join(O, WORD_FILE)), jload(os.path.join(O, SENT_FILE))
    words, sents = WD['words'], SD['sentences']
    wbw = jload(os.path.join(D, 'indopak-nastaleeq-wbw.json'))
    verse = jload(os.path.join(D, 'indopak-nastaleeq.json'))
    normalized = jload(os.path.join(D, 'indopak-nastaleeq-wbw-normalized.json'))
    header, rows = S.read_treebank(os.path.join(D, 'Quranic', 'Quranic.csv'))

    # ------------------------------------------------------------------ inputs unchanged
    bad = []
    with open(os.path.join(D, 'CHECKSUMS.sha256')) as f:
        for line in f:
            h, p = line.split()
            if sha256(os.path.join(D, p)) != h:
                bad.append(p)
    check('inputs', 'data/ files match CHECKSUMS.sha256 (supplied files unchanged)', not bad, str(bad))
    cur = {k: sha256(os.path.join(D, k)) for k in WD['metadata']['input_sha256']}
    check('inputs', 'both layers were built from the current input files',
          cur == WD['metadata']['input_sha256'] == SD['metadata']['input_sha256'])
    check('inputs', 'text authority hashes recorded for the two Quran files',
          set(WD['metadata']['text_authority']) == {'indopak-nastaleeq.json', 'indopak-nastaleeq-wbw.json'})

    # ------------------------------------------------------------------ alignment with the Quran text
    real = {k for k, v in normalized.items() if v['normalized']}
    markers = set(wbw) - real
    check('alignment', 'word layer keys == written words of the WBW file (verse-end markers excluded)',
          set(words) == real and not (set(words) & markers), f'{len(set(words) ^ real)} differ')
    check('alignment', 'word count 77,432 and marker count 6,236', len(words) == 77432 and len(markers) == 6236)
    check('alignment', 'text_indopak and wbw_id equal the WBW file for every word',
          all(words[k]['text_indopak'] == wbw[k]['text'] and words[k]['wbw_id'] == wbw[k]['id'] for k in words))
    order = sorted(words, key=lambda k: tuple(int(x) for x in k.split(':')))
    check('alignment', 'word keys are in Quranic text order', list(words) == order)
    per = collections.defaultdict(list)
    for k, v in wbw.items():
        per[(int(v['surah']), int(v['ayah']))].append((int(v['word']), v['text']))
    mism = sum(1 for v in verse.values()
               if ' '.join(t for _, t in sorted(per[(int(v['surah']), int(v['ayah']))])) != v['text'])
    check('alignment', 'WBW words joined == indopak-nastaleeq.json verse text for all 6,236 ayahs', mism == 0, str(mism))

    # ------------------------------------------------------------------ lossless round trip
    seg_by_tid, node_by_tid = {}, {}
    dup = 0
    for k, w in words.items():
        for seg in w['segments']:
            dup += seg['treebank_tid'] in seg_by_tid
            seg_by_tid[seg['treebank_tid']] = (k, seg)
    for sid, s in sents.items():
        for n in s['nodes']:
            dup += n['treebank_tid'] in node_by_tid
            node_by_tid[n['treebank_tid']] = (int(sid), n)
    csv_tids = [int(r['tid']) for r in rows]
    real_tids = {int(r['tid']) for r in rows if r['location'] != '_'}
    check('lossless', 'no Treebank row appears twice in either layer', dup == 0, str(dup))
    check('lossless', 'every row is a node of exactly one sentence (139,376)',
          set(node_by_tid) == set(csv_tids) and len(node_by_tid) == len(rows))
    check('lossless', 'rows with a word location are word segments; implicit rows are not',
          set(seg_by_tid) == real_tids and not (set(seg_by_tid) & (set(csv_tids) - real_tids)))
    flat = [n['treebank_tid'] for s in sents.values() for n in s['nodes']]
    check('lossless', 'sentence order and node order reproduce the original file order', flat == csv_tids)

    mism_cols = collections.Counter()
    mism_rows = 0
    for r in rows:
        tid = int(r['tid'])
        sid, n = node_by_tid[tid]
        cols = {'tid': str(tid), 'sentence_id': str(sid), 'token_id': str(n['token_id']),
                'sentence_word': str(n['sentence_word'])}
        if r['location'] != '_':
            wk, seg = seg_by_tid[tid]
            loc = seg['location']
            p = loc.split(':')
            cols.update(location='(' + loc + ')', chapter_id=p[0], verse_id=p[1], word_id=p[2], tok_id=p[3])
            morph = seg
            ok_ptr = (seg['syntax_ref'] == {'sentence_id': sid, 'token_id': n['token_id']} and n['word'] == wk
                      and n['segment'] == loc and n['pos'] == seg['pos'] and not n['implicit'])
            if not ok_ptr:
                mism_cols['pointer'] += 1
        else:
            cols.update(location='_', chapter_id=n['chapter_id'], verse_id=n['verse_id'], word_id=n['word_id'],
                        tok_id=n['tok_id'])
            morph = n['morphology']
            if not n['implicit']:
                mism_cols['implicit_flag'] += 1
        cols.update(S.morph_to_cols(morph))
        cols.update(S.syntax_to_cols(n))
        bad_here = False
        if set(cols) != set(header):
            mism_cols['column_set'] += 1
            bad_here = True
        for c in header:
            if cols.get(c) != r[c]:
                mism_cols[c] += 1
                bad_here = True
        mism_rows += bad_here
    check('lossless', 'all 43 columns of all 139,376 rows re-created exactly from the two JSON files',
          not mism_cols and mism_rows == 0, str(dict(mism_cols)))

    # ------------------------------------------------------------------ structure
    check('structure', 'sentence ids are exactly 1..11693',
          sorted(int(k) for k in sents) == list(range(1, 11694)))
    bad = [sid for sid, s in sents.items()
           if [n['token_id'] for n in s['nodes']] != list(range(len(s['nodes'])))
           or any(not 0 <= n['head'] < len(s['nodes']) for n in s['nodes'])]
    check('structure', 'token_id == index in sentence; every head points to a node of the same sentence', not bad, str(bad[:5]))
    bad = [sid for sid, s in sents.items() for c in s['constituents']
           if not (0 <= c['token_span'][0] <= c['token_span'][1] < len(s['nodes']))]
    check('structure', 'constituent spans lie inside their sentence', not bad, str(bad[:5]))
    member = collections.Counter(wk for s in sents.values() for wk in s['words'])
    annotated = {k for k, w in words.items() if w['annotation_status'] == 'annotated'}
    check('structure', 'every annotated word is in exactly one sentence "words" list',
          set(member) == annotated and all(v == 1 for v in member.values()))
    check('structure', 'word.sentence_id agrees with the sentence that lists the word',
          all(words[wk]['sentence_id'] == int(sid) for sid, s in sents.items() for wk in s['words']))
    check('structure', 'sentence words are in text order and span fields are correct',
          all(s['words'] == sorted(s['words'], key=lambda k: tuple(int(x) for x in k.split(':')))
              and s['span']['crosses_ayah'] == (len(s['span']['ayahs']) > 1)
              and (not s['words'] or (s['span']['first_word'], s['span']['last_word']) == (s['words'][0], s['words'][-1]))
              for s in sents.values()))
    absent = [k for k, w in words.items() if w['annotation_status'] != 'annotated']
    check('structure', 'exactly the 3 expected words lack Treebank annotation',
          sorted(absent) == sorted(['2:181:14', '8:6:12', '13:37:20']) == sorted(WD['metadata']['words_absent_in_treebank']))
    split = [k for k, w in words.items() if w['segments'] and len({sg['syntax_ref']['sentence_id'] for sg in w['segments']}) > 1]
    check('structure', '41 words span two sentence ids; each is assigned to its stem sentence',
          len(split) == 41 and all(words[k]['sentence_id'] == next(sg for sg in words[k]['segments'] if sg['type'] == 'STEM')['syntax_ref']['sentence_id'] for k in split))
    imp = [n for s in sents.values() for n in s['nodes'] if n['implicit']]
    check('structure', 'implicit nodes (11,157) have no word, have an anchor and are outside "words"',
          len(imp) == 11157 and all(n['word'] is None and 'anchor' in n for n in imp))

    # ------------------------------------------------------------------ derived fields recomputed
    nodes_of = collections.defaultdict(list)
    for s in sents.values():
        for n in s['nodes']:
            if n['word']:
                nodes_of[n['word']].append(n)
    bad = []
    for k in annotated:
        w = words[k]
        ns = sorted(nodes_of[k], key=lambda n: n['treebank_tid'])
        types = {sg['location']: sg['type'] for sg in w['segments']}
        stem = [n for n in ns if types[n['segment']] == 'STEM']
        nonrel = [n['rel'] for n in ns if n['rel'] != 'NonRel']
        exp = {'pos_stem': '+'.join(n['pos'] for n in stem), 'pos_all_segments': '+'.join(n['pos'] for n in ns),
               'function_all': '+'.join(n['rel'] for n in ns),
               'function_without_NonRel': '+'.join(nonrel) if nonrel else 'NonRel',
               'function_stem': '+'.join(n['rel'] for n in stem)}
        if exp != w['derived']['projections']:
            bad.append(k)
    check('derived', 'word projections recomputed from sentence nodes + segment types', not bad, str(bad[:5]))
    bad = [sid for sid, s in sents.items()
           if s['derived']['pos_sequence'] != {'stem': [words[w]['derived']['projections']['pos_stem'] for w in s['words']],
                                               'all_segments': [words[w]['derived']['projections']['pos_all_segments'] for w in s['words']]}
           or s['derived']['function_sequence'] != {
               'all': [words[w]['derived']['projections']['function_all'] for w in s['words']],
               'without_NonRel': [words[w]['derived']['projections']['function_without_NonRel'] for w in s['words']],
               'stem': [words[w]['derived']['projections']['function_stem'] for w in s['words']]}]
    check('derived', 'sentence POS / function sequences equal the word projections', not bad, str(bad[:5]))
    v_rows = [r for r in rows if r['location'] != '_' and r['segment'] == 'STEM' and r['pos'] == 'V']
    explicit = sum(1 for r in v_rows if r['verb_form'] != '_')
    vf = [f for w in words.values() if w['segments'] for f in w['derived']['verb_forms']]
    nom = sum(len(w['derived']['nominal_form_annotations']) for w in words.values() if w['segments'])
    nonverb_forms = sum(1 for r in rows if r['location'] != '_' and r['segment'] == 'STEM' and r['pos'] != 'V' and r['verb_form'] != '_')
    check('derived', 'verb forms: one per verb stem; explicit/inferred counts match the source',
          len(vf) == len(v_rows) and sum(f['basis'] == 'explicit' for f in vf) == explicit
          and sum(f['basis'] == 'inferred' for f in vf) == len(v_rows) - explicit,
          f'{len(vf)} vs {len(v_rows)}')
    check('derived', 'Form I is never explicit in the source (so always inferred); non-verb form annotations are kept apart',
          not any(f['value'] == 'I' and f['basis'] == 'explicit' for f in vf) and nom == nonverb_forms
          and all(not w['derived']['is_verb'] for w in words.values() if w['segments'] and w['derived']['nominal_form_annotations']
                  and not w['derived']['verb_forms']))
    info['verb_form_counts'] = collections.OrderedDict(
        (f, {'explicit': sum(1 for x in vf if x['value'] == f and x['basis'] == 'explicit'),
             'inferred': sum(1 for x in vf if x['value'] == f and x['basis'] == 'inferred')})
        for f in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'])
    info['non_verb_segments_with_form_annotation'] = nom

    # ------------------------------------------------------------------ reference coverage
    rd_w, rd_s = WD['reference_data'], SD['reference_data']
    used = lambda col: {r[col] for r in rows if r[col] != '_'}
    miss = {
        'pos': used('pos') - set(rd_s['pos']), 'relations': used('rel_label') - set(rd_s['relations']),
        'constituent_tags': {t for t in used('constituent_label') if t != '-'} - set(rd_s['constituent_tags']),
        'verb_forms': {x.strip('()') for x in used('verb_form')} - set(rd_w['verb_forms']),
        'roots': used('root') - set(rd_w['roots']), 'lemmas': used('lemma') - set(rd_w['lemmas']),
        'case': used('nominal_case') - set(rd_w['features']['NominalCase']['entries']),
        'mood': {x.replace('MOOD:', '') for x in used('verb_mood')} - set(rd_w['verb_moods']),
        'derived_noun': used('derived_nouns') - set(rd_w['features']['DerivedNoun']['entries']),
        'number': used('number') - set(rd_w['features']['Number']['entries']),
        'gender': used('gender') - set(rd_w['features']['Gender']['entries'])}
    miss = {k: sorted(v) for k, v in miss.items() if v}
    check('reference', 'every POS, relation, constituent tag, form, case, mood, number, gender, root, lemma value is defined', not miss, str(miss))
    check('reference', 'feature-guide corrections are recorded (verb-form ordinals, mood descriptions)',
          len(rd_w['corrections']) > 0 and all('source' in c and 'corrected' in c for c in rd_w['corrections']),
          str(len(rd_w['corrections'])))

    # ------------------------------------------------------------------ morphology v0.4 cross-check
    v04 = {}
    with open(os.path.join(D, 'quranic-corpus-morphology-0.4.txt'), encoding='utf-8') as f:
        for line in f:
            if line.startswith('('):
                p = line.rstrip('\r\n').split('\t')
                v04[p[0].strip('()')] = p
    miss_f, pos_diff = [], []
    for wk, seg in seg_by_tid.values():
        p = v04.get(seg['location'])
        if p is None or p[3] != seg.get('features_raw'):
            miss_f.append(seg['location'])
            continue
        if p[2] != seg['pos']:
            pos_diff.append(seg['location'])
    check('cross-check', 'morphology v0.4 has the same 128,219 segments and identical feature strings as the Treebank',
          not miss_f and set(v04) == {s['location'] for _, s in seg_by_tid.values()}, f'{len(miss_f)} differ')
    check('cross-check', 'the Treebank POS re-taggings vs v0.4 are exactly those listed in metadata.source_issues',
          sorted(pos_diff) == sorted(d['segment'] for d in WD['metadata']['source_issues']['segments_pos_differs_from_morphology_v04']['segments']),
          str(len(pos_diff)))
    info['segments_pos_differs_from_morphology_v04'] = len(pos_diff)

    # ------------------------------------------------------------------ informational
    lem_mis = rt_mis = 0
    for seg in (s for _, s in seg_by_tid.values()):
        fr = seg.get('features_raw', '')
        m = re.search(r'LEM:([^|]+)', fr)
        if (m.group(1) if m else None) != (seg['lemma']['bw'] if 'lemma' in seg else None):
            lem_mis += 1
        m = re.search(r'ROOT:([^|]+)', fr)
        if (m.group(1) if m else None) != (seg['root']['bw'] if 'root' in seg else None):
            rt_mis += 1
    info['feature_string_vs_columns'] = {'lemma_mismatch_segments': lem_mis, 'root_mismatch_segments': rt_mis}
    db = collections.Counter()
    for k, w in words.items():
        if 'secondary_db' not in w or not w['segments']:
            continue
        tl = [sg['lemma']['ar'] for sg in w['segments'] if 'lemma' in sg]
        tr = [sg['root']['ar'] for sg in w['segments'] if 'root' in sg]
        d = w['secondary_db']
        if 'lemma' in d:
            db['lemma_db_agrees_with_treebank'] += bool(tl) and d['lemma'][0]['text'] == tl[0]
            db['lemma_db_differs_or_treebank_has_none'] += not (bool(tl) and d['lemma'][0]['text'] == tl[0])
        if 'root' in d:
            db['root_db_agrees_with_treebank'] += bool(tr) and d['root'][0]['text'].replace(' ', '') == tr[0]
            db['root_db_differs_or_treebank_has_none'] += not (bool(tr) and d['root'][0]['text'].replace(' ', '') == tr[0])
    info['secondary_db_vs_treebank_words'] = dict(db)
    info['source_issues'] = WD['metadata']['source_issues']
    info['prefix_only_fragment_sentences'] = len(SD['metadata']['source_issues']['prefix_only_fragment_sentences'])
    info['sentences_crossing_ayah'] = sum(s['span']['crosses_ayah'] for s in sents.values())

    ok = all(r['ok'] for r in results)
    report = {'ok': ok, 'checks': results, 'info': info,
              'files': {fn: {'bytes': os.path.getsize(os.path.join(O, fn)), 'sha256': sha256(os.path.join(O, fn))}
                        for fn in (WORD_FILE, SENT_FILE)}}
    with open(os.path.join(O, 'validation-report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('\n%d/%d checks passed' % (sum(r['ok'] for r in results), len(results)))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
