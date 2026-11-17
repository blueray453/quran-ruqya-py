"""Step 3: does using the lemma / stem / root databases change the analysis?

Reads   results/indopak-nastaleeq-wbw-normalized.json, data/word-{lemma,stem,root}.db, data/ayah-{lemma,stem,root}.db
Writes  results/representation-comparison.csv   coverage under six definitions of "the same word"
        results/db-audit.json                   over-merging audit and database consistency checks

Representations compared (same units, same coverage definition as analyze.py):
  normalized (before restoring 2 words), normalized, exact diacritics,
  stem (DB), lemma (DB), root (DB). Words without a database label keep their normalized spelling.
"""
import argparse, collections, csv, json, os, sqlite3, unicodedata

ap = argparse.ArgumentParser()
ap.add_argument('--data-dir', default='data'); ap.add_argument('--results-dir', default='results')
a = ap.parse_args()
D, R = a.data_dir, a.results_dir
normed = json.load(open(os.path.join(R, 'indopak-nastaleeq-wbw-normalized.json'), encoding='utf-8'))

def q(db, sql):
    c = sqlite3.connect('file:' + os.path.join(D, db) + '?mode=ro', uri=True); return c.execute(sql).fetchall()
stem_loc = {l: (i, t) for l, i, t in q('word-stem.db', 'select w.word_location,s.id,s.text from stem_words w join stems s on s.id=w.stem_id')}
lem_loc = {l: (i, t) for l, i, t in q('word-lemma.db', 'select w.word_location,s.id,s.text from lemma_words w join lemmas s on s.id=w.lemma_id')}
rt_loc = {l: (i, t) for l, i, t in q('word-root.db', 'select w.word_location,s.id,s.arabic_trilateral from root_words w join roots s on s.id=w.root_id')}

verses = collections.OrderedDict()
for e in sorted(normed.values(), key=lambda x: (x['surah'], x['ayah'], x['word'])):
    loc = f"{e['surah']}:{e['ayah']}:{e['word']}"
    verses.setdefault(f"{e['surah']}:{e['ayah']}", [])
    if e['normalized']:
        verses[f"{e['surah']}:{e['ayah']}"].append(dict(loc=loc, restored='restored_from' in e, exact=e['exact'],
            norm=e['normalized'], stem=stem_loc.get(loc), lemma=lem_loc.get(loc), root=rt_loc.get(loc)))
toks = [t for v in verses.values() for t in v]

def seqs(fn, skip_restored=False):
    return [[fn(t) for t in v if not (skip_restored and t['restored'])] for v in verses.values()]

rows = []
def report(name, S):
    N = sum(map(len, S)); cnt = collections.Counter(t for s in S for t in s)
    hap = sum(1 for v in cnt.values() if v == 1)
    cp = [bytearray(len(s)) for s in S]; rep_ph = 0; k = 2
    while True:
        d = collections.defaultdict(list)
        for vi, s in enumerate(S):
            for i in range(len(s) - k + 1): d[tuple(s[i:i + k])].append((vi, i))
        rep = [p for p in d.values() if len(p) >= 2]
        if not rep: break
        rep_ph += len(rep)
        for p in rep:
            for vi, i in p:
                for j in range(k): cp[vi][i + j] = 1
        k += 1
    r = dict(representation=name, tokens=N, distinct_types=len(cnt), once_only_types=hap,
             pct_types_once=round(100 * hap / len(cnt), 1),
             coverage_words_and_phrases_pct=round(100 * (N - hap) / N, 2),
             coverage_phrases_only_pct=round(100 * sum(sum(c) for c in cp) / N, 2),
             repeated_phrase_types=rep_ph, longest_phrase=k - 1)
    rows.append(r); print(r)

report('normalized spelling (before restoring the 2 glyph words)', seqs(lambda t: t['norm'], True))
report('normalized spelling (main analysis)', seqs(lambda t: t['norm']))
report('exact spelling with diacritics', seqs(lambda t: t['exact']))
report('stem (database; spelling fallback)', seqs(lambda t: ('s', t['stem'][0]) if t['stem'] else ('x', t['norm'])))
report('lemma (database; spelling fallback)', seqs(lambda t: ('l', t['lemma'][0]) if t['lemma'] else ('x', t['norm'])))
report('root (database; spelling fallback for rootless words)', seqs(lambda t: ('r', t['root'][0]) if t['root'] else ('x', t['norm'])))
with open(os.path.join(R, 'representation-comparison.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# ---------- audit
audit = {}
audit['tokens'] = len(toks)
audit['labelled_tokens'] = {k: sum(1 for t in toks if t[k]) for k in ('stem', 'lemma', 'root')}
by_norm = collections.defaultdict(collections.Counter)
for t in toks: by_norm[t['norm']][t['exact']] += 1
multi = {k: c for k, c in by_norm.items() if len(c) > 1}
audit['normalized_types'] = len(by_norm)
audit['types_merging_multiple_exact_forms'] = len(multi)
audit['tokens_in_those_types'] = sum(sum(c.values()) for c in multi.values())
audit['examples_exact_forms'] = [(k, sum(c.values()), dict(c.most_common(4)))
                                 for k, c in sorted(multi.items(), key=lambda x: -sum(x[1].values()))[:8]]
lem_by = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
for t in toks:
    if t['lemma']: lem_by[t['norm']][t['lemma'][0]][t['lemma'][1]] += 1
hom = {k: v for k, v in lem_by.items() if len(v) > 1}
audit['types_mapping_to_multiple_lemmas'] = len(hom)
audit['tokens_in_those_lemma_types'] = sum(sum(sum(c.values()) for c in v.values()) for v in hom.values())
audit['examples_lemmas'] = [(k, {list(c)[0]: sum(c.values()) for c in v.values()})
                            for k, v in sorted(hom.items(), key=lambda x: -sum(sum(c.values()) for c in x[1].values()))[:6]]
mn = collections.Counter((t['exact'], t['lemma'][1] if t['lemma'] else None) for t in toks if t['norm'] == 'من')
audit['word_lemma_db_man_vs_min'] = [(list(k), v) for k, v in mn.most_common(8)]

def detail(db, table, pick, fmt=lambda x: x):
    rows_ = dict(q(db, f'select verse_key,text from {table}'))
    res = dict(verses_absent=0, identical=0, same_count_different_items=0, different_token_count=0)
    for k, v in verses.items():
        mine = [fmt(pick(t)) for t in v if pick(t)]
        if k not in rows_: res['verses_absent'] += 1; continue
        theirs = rows_[k].split()
        if mine == theirs: res['identical'] += 1
        elif len(mine) == len(theirs): res['same_count_different_items'] += 1
        else: res['different_token_count'] += 1
    return res
audit['ayah_vs_word_database_consistency'] = {
    'lemma': detail('ayah-lemma.db', 'lemmas', lambda t: t['lemma'][1] if t['lemma'] else None),
    'stem': detail('ayah-stem.db', 'stems', lambda t: t['stem'][1] if t['stem'] else None),
    'root': detail('ayah-root.db', 'roots', lambda t: t['root'][1].replace(' ', '') if t['root'] else None)}
# database locations that are not real words in our file (verse-end markers etc.)
real = {t['loc'] for t in toks}
audit['db_locations_not_real_words'] = {'lemma': len(set(lem_loc) - real), 'root': len(set(rt_loc) - real), 'stem': len(set(stem_loc) - real)}
audit['real_words_missing_from_db'] = {'lemma': len(real - set(lem_loc)), 'root': len(real - set(rt_loc)), 'stem': len(real - set(stem_loc))}
json.dump(audit, open(os.path.join(R, 'db-audit.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(audit, ensure_ascii=False, indent=1)[:3500])
