#!/usr/bin/env python3
"""Generate the grammar equivalents of quran-phrases.csv, FROM THE TWO JSON LAYERS ONLY.

Reads  output/indopak-nastaleeq-wbw-grammar-normalized.json
       output/indopak-nastaleeq-sentence-grammar-normalized.json
Writes output/sequences/
   quran-pos-sequences.csv                       repeated POS sequences          (ids P00001...)
   quran-function-sequences.csv                  repeated syntactic-function sequences (ids F00001...)
   (and, in output/memorization-order/, the learning orders: one table per minimum length 1, 2, 3, 5)
   quran-greedy-order-pos-<variant>.csv          learning order for POS sequences
   quran-greedy-order-function-<variant>.csv     learning order for function sequences
   quran-pos-sequences-annotation.json           every unit with exact occurrence locations
   quran-function-sequences-annotation.json
   sequence-analysis-report.json                 parameters, input hashes, coverage, greedy checkpoints, checks

The CSVs are written from the annotation JSON records, which are computed from the sentence layer: nothing is read
from the Treebank or any other source file. POS and function sequences are separate analyses and never mixed.

Usage: python3 pipeline/04_generate_csv.py [--pos-projection pos_all_segments] [--function-projection function_without_NonRel]
                                          [--min-count 2] [--greedy-min-lens 1,2,3,5] [--no-verify]
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import sequence_engine as E

WORD_FILE = 'indopak-nastaleeq-wbw-grammar-normalized.json'
SENT_FILE = 'indopak-nastaleeq-sentence-grammar-normalized.json'
POS_PROJ = {'pos_stem': ('pos_sequence', 'stem'), 'pos_all_segments': ('pos_sequence', 'all_segments')}
FUN_PROJ = {'function_all': ('function_sequence', 'all'), 'function_without_NonRel': ('function_sequence', 'without_NonRel'),
            'function_stem': ('function_sequence', 'stem')}
CHECKPOINTS = (10, 50, 100, 500, 1000, 5000)


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def sentence_sequences(sents, group, key):
    """One label list per sentence that owns written words, in sentence-id order, plus the position index."""
    seqs, word_index, sentence_index = [], [], []
    for sid in sorted(sents, key=int):
        s = sents[sid]
        if not s['words']:
            continue                      # prefix-only fragment: owns no written word
        labels = s['derived'][group][key]
        assert len(labels) == len(s['words'])
        seqs.append(labels)
        word_index.extend(s['words'])
        sentence_index.extend([int(sid)] * len(s['words']))
    return seqs, word_index, sentence_index


def build_annotation(kind, prefix, projection, units, word_index, sentence_index, texts, meta):
    """Annotation records (the source of the CSV) for one analysis."""
    recs = []
    for idx, u in enumerate(units, 1):
        n, starts, alone = u['length'], u['starts'], u['alone']
        ex = next((s for s, a in zip(starts, alone) if a), starts[0])           # first stand-alone occurrence, else first
        recs.append({
            'id': f'{prefix}{idx:05d}', 'length': n, 'sequence': list(u['labels']),
            'total_count': len(starts), 'stand_alone_count': sum(alone), 'inside_longer_count': len(starts) - sum(alone),
            'sentences_total': len({sentence_index[s] for s in starts}),
            'sentences_stand_alone': len({sentence_index[s] for s, a in zip(starts, alone) if a}),
            'example': {'sentence_id': sentence_index[ex], 'start_word': word_index[ex], 'end_word': word_index[ex + n - 1],
                        'text_nastaleeq': ' '.join(texts[w] for w in word_index[ex:ex + n])},
            'occurrences': starts,
            'stand_alone_occurrences': [s for s, a in zip(starts, alone) if a]})
    return {'metadata': dict(meta, kind=kind, projection=projection, units=len(recs)),
            'word_index': word_index, 'sentence_index': sentence_index, 'units': recs}


VARIANTS = {1: 'labels-and-sequences', 2: 'sequences-only', 3: 'sequences-3plus', 5: 'sequences-5plus'}


def write_sequence_csv(ann, path):
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['id', 'length', 'total_count', 'stand_alone_count', 'inside_longer_count', 'sentences_total',
                    'sentences_stand_alone', 'sequence', 'example_sentence_id', 'example_start_word', 'example_end_word',
                    'example_text_nastaleeq'])
        for r in ann['units']:
            e = r['example']
            w.writerow([r['id'], r['length'], r['total_count'], r['stand_alone_count'], r['inside_longer_count'],
                        r['sentences_total'], r['sentences_stand_alone'], ' '.join(r['sequence']), e['sentence_id'],
                        e['start_word'], e['end_word'], e['text_nastaleeq']])


def write_greedy(ann, path, total_quran, min_len):
    """Memorization order: greedy set cover (identical to the original algorithm) over units of at least min_len words."""
    recs = ann['units']
    sel = E.greedy([{'length': r['length'], 'starts': r['occurrences']} for r in recs], min_len)
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['rank', 'id', 'sequence', 'words_in_unit', 'total_count', 'new_words_covered', 'cumulative_words_covered',
                    'cumulative_pct_of_quran', 'cumulative_words_to_learn', 'example_text_nastaleeq'])
        for rk, (j, gn, cm, cs) in enumerate(sel, 1):
            r = recs[j]
            w.writerow([rk, r['id'], ' '.join(r['sequence']), r['length'], r['total_count'], gn, cm,
                        round(100 * cm / total_quran, 2), cs, r['example']['text_nastaleeq']])
    return sel


def verify(kind, ann, seqs, sample=150, seed=7):
    """Independent brute-force check of a random sample of units (plus the most frequent and the longest)."""
    toks, end, sent_of = [], [], []
    for si, s in enumerate(seqs):
        base = len(toks)
        toks.extend(s)
        end.extend([base + len(s) - 1] * len(s))
        sent_of.extend([si] * len(s))
    recs = ann['units']
    rng = random.Random(seed)
    pick = set(rng.sample(range(len(recs)), min(sample, len(recs)))) | {0, 1, 2, max(range(len(recs)), key=lambda j: recs[j]['length'])}
    need = collections.defaultdict(list)
    for j in pick:
        need[recs[j]['length'] + 1].append(j)
    longer = {}
    for m in need:                                   # all (m)-grams of the corpus, counted naively
        c = collections.Counter()
        for i in range(len(toks)):
            if i + m - 1 <= end[i]:
                c[tuple(toks[i:i + m])] += 1
        longer[m] = c
    bad = []
    for j in sorted(pick):
        r = recs[j]
        n, seq = r['length'], tuple(r['sequence'])
        occ = [i for i in range(len(toks)) if i + n - 1 <= end[i] and tuple(toks[i:i + n]) == seq]
        alone = []
        for i in occ:
            rep = lambda k: k >= 0 and k + n <= end[k] and longer[n + 1][tuple(toks[k:k + n + 1])] >= 2
            alone.append(not rep(i) and not rep(i - 1))
        if (occ != r['occurrences'] or [i for i, a in zip(occ, alone) if a] != r['stand_alone_occurrences']
                or r['total_count'] != r['stand_alone_count'] + r['inside_longer_count']):
            bad.append(r['id'])
    return len(pick), bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='output')
    ap.add_argument('--pos-projection', default='pos_all_segments', choices=list(POS_PROJ))
    ap.add_argument('--function-projection', default='function_without_NonRel', choices=list(FUN_PROJ))
    ap.add_argument('--min-count', type=int, default=2)
    ap.add_argument('--greedy-min-lens', default='1,2,3,5',
                    help='comma-separated minimum unit lengths; one memorization-order table per value (1 = identical to the original '
                         'words-and-phrases algorithm)')
    ap.add_argument('--no-verify', action='store_true')
    a = ap.parse_args()
    src_w, src_s = os.path.join(a.out_dir, WORD_FILE), os.path.join(a.out_dir, SENT_FILE)
    with open(src_w, encoding='utf-8') as f:
        words = json.load(f)['words']
    with open(src_s, encoding='utf-8') as f:
        sents = json.load(f)['sentences']
    texts = {k: w['text_indopak'] for k, w in words.items()}
    total_quran = len(words)                          # 77,432 written words (the 3 unannotated words can never be covered)
    out = os.path.join(a.out_dir, 'sequences')
    mem = os.path.join(a.out_dir, 'memorization-order')
    os.makedirs(out, exist_ok=True)
    os.makedirs(mem, exist_ok=True)
    meta = {'source_layers': {WORD_FILE: sha256(src_w), SENT_FILE: sha256(src_s)},
            'source_policy': 'computed from the two JSON layers only',
            'definition': 'consecutive complete written words inside one sentence (never across a sentence boundary); kept when '
                          f'occurring >= {a.min_count} times; stand_alone = occurrence not inside a longer repeated sequence '
                          '(total = stand_alone + inside_longer)',
            'min_count': a.min_count, 'greedy_min_lens': a.greedy_min_lens, 'total_quran_words': total_quran,
            'occurrence_encoding': 'occurrences / stand_alone_occurrences are start positions into word_index; a unit of length n '
                                   'covers word_index[s : s+n]; sentence_index[s] is its sentence id'}
    report = {'parameters': {'pos_projection': a.pos_projection, 'function_projection': a.function_projection,
                             'min_count': a.min_count, 'greedy_min_lens': a.greedy_min_lens},
              'input_sha256': meta['source_layers'], 'analyses': {}, 'checks': []}
    for kind, prefix, proj, table, seq_name, greedy_name in (
            ('pos', 'P', a.pos_projection, POS_PROJ, 'quran-pos-sequences', 'quran-greedy-order-pos-'),
            ('function', 'F', a.function_projection, FUN_PROJ, 'quran-function-sequences', 'quran-greedy-order-function-')):
        group, key = table[proj]
        seqs, word_index, sentence_index = sentence_sequences(sents, group, key)
        units, _, _ = E.find_repeated(seqs, a.min_count)
        ann = build_annotation(kind, prefix, proj, units, word_index, sentence_index, texts, meta)
        with open(os.path.join(out, seq_name + '-annotation.json'), 'w', encoding='utf-8') as f:
            json.dump(ann, f, ensure_ascii=False, separators=(',', ':'))
        write_sequence_csv(ann, os.path.join(out, seq_name + '.csv'))
        greedy_info = {}
        for ml in [int(x) for x in a.greedy_min_lens.split(',')]:
            fn = '%s%s.csv' % (greedy_name, VARIANTS.get(ml, 'sequences-%dplus' % ml))
            sel = write_greedy(ann, os.path.join(mem, fn), total_quran, ml)
            greedy_info[fn] = {'min_unit_length': ml, 'units_selected': len(sel), 'final_pct_of_quran': round(100 * sel[-1][2] / total_quran, 2),
                               'checkpoints': [{'units': n, 'words_to_learn': sel[n - 1][3], 'pct_of_quran': round(100 * sel[n - 1][2] / total_quran, 2)}
                                               for n in CHECKPOINTS if n <= len(sel)]}
        cov = E.coverage_by_min_length(units, len(word_index))
        by_len = collections.Counter(u['length'] for u in units)
        info = {'projection': proj, 'distinct_labels': len({l for s in seqs for l in s}), 'sentences_used': len(seqs),
                'word_positions': len(word_index), 'repeated_units': len(units), 'longest_unit': max(by_len),
                'units_never_stand_alone': sum(1 for r in ann['units'] if r['stand_alone_count'] == 0),
                'coverage_pct_by_min_length': {str(k): round(100 * v, 2) for k, v in cov.items()},
                'greedy': greedy_info}
        report['analyses'][kind] = info
        ok = all(r['total_count'] == len(r['occurrences']) >= a.min_count
                 and r['total_count'] == r['stand_alone_count'] + r['inside_longer_count'] for r in ann['units'])
        report['checks'].append({'check': f'{kind}: total = stand_alone + inside_longer, every unit occurs >= {a.min_count} times', 'ok': ok})
        # CSV <-> annotation JSON agreement
        with open(os.path.join(out, seq_name + '.csv'), encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        ok = (len(rows) == len(ann['units']) and all(
            r['id'] == u['id'] and int(r['total_count']) == u['total_count'] and int(r['stand_alone_count']) == u['stand_alone_count']
            and r['sequence'] == ' '.join(u['sequence']) for r, u in zip(rows, ann['units'])))
        report['checks'].append({'check': f'{kind}: CSV rows agree with the annotation JSON', 'ok': ok})
        if not a.no_verify:
            n, bad = verify(kind, ann, seqs)
            report['checks'].append({'check': f'{kind}: {n} units re-counted by brute force (occurrences and stand-alone flags)',
                                     'ok': not bad, 'detail': bad[:5]})
        print(f'{kind:9} {proj:26} units {len(units):6}  longest {max(by_len):3}  memorization-order variants: '
              + ', '.join('%s=%d units' % (v['min_unit_length'], v['units_selected']) for v in greedy_info.values()))
    report['files'] = {d + '/' + fn: os.path.getsize(os.path.join(p_, fn)) for d, p_ in (('sequences', out), ('memorization-order', mem))
                       for fn in sorted(os.listdir(p_)) if fn != 'sequence-analysis-report.json' and (d == 'sequences' or fn.startswith(('quran-greedy-order-pos-', 'quran-greedy-order-function-')))}
    with open(os.path.join(out, 'sequence-analysis-report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    for c in report['checks']:
        print(('PASS ' if c['ok'] else 'FAIL ') + c['check'])
    for fn, sz in report['files'].items():
        print('  %-52s %8.2f MB' % (fn, sz / 1e6))
    sys.exit(0 if all(c['ok'] for c in report['checks']) else 1)


if __name__ == '__main__':
    main()
