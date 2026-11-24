"""Read-only accessors over the two canonical JSON layers, shared by queries/ and pipeline/05_analysis.py.

Nothing here touches the Treebank or any other source file: everything comes from
output/indopak-nastaleeq-wbw-grammar-normalized.json and output/indopak-nastaleeq-sentence-grammar-normalized.json.
"""
import collections
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'output')
WORD_FILE = 'indopak-nastaleeq-wbw-grammar-normalized.json'
SENT_FILE = 'indopak-nastaleeq-sentence-grammar-normalized.json'
NOT_PARTICLES = {'N', 'PN', 'V', 'ADJ', 'PRON', 'DEM', 'REL', 'T', 'LOC'}
_cache = {}


def load(out_dir=OUT):
    """(word layer, sentence layer) as loaded JSON documents (cached)."""
    if out_dir not in _cache:
        def j(fn):
            with open(os.path.join(out_dir, fn), encoding='utf-8') as f:
                return json.load(f)
        _cache[out_dir] = (j(WORD_FILE), j(SENT_FILE))
    return _cache[out_dir]


def words(out_dir=OUT):
    return load(out_dir)[0]['words']


def sentences(out_dir=OUT):
    return load(out_dir)[1]['sentences']


def node_pos(n):
    return n.get('pos') or n.get('morphology', {}).get('pos')


def word_text(key, out_dir=OUT):
    return words(out_dir)[key]['text_indopak']


def sentence_of_word(key, out_dir=OUT):
    return sentences(out_dir)[str(words(out_dir)[key]['sentence_id'])]


def syntax_of_word(key, out_dir=OUT):
    """For every segment of the word: its relation, head (word / POS) and dependents, joined from the sentence layer."""
    W, S = words(out_dir), sentences(out_dir)
    out = []
    for seg in W[key]['segments']:
        sid, tok = seg['syntax_ref']['sentence_id'], seg['syntax_ref']['token_id']
        nodes = S[str(sid)]['nodes']
        n = nodes[tok]
        head = nodes[n['head']]
        deps = [d for d in nodes if d['head'] == tok and d['token_id'] != tok]
        out.append({'segment': seg['location'], 'sentence_id': sid, 'token_id': tok, 'rel': n['rel'], 'rel_ar': n.get('rel_ar'),
                    'head_token': n['head'], 'head_is_self': n['head'] == tok, 'head_word': head.get('word'),
                    'head_pos': node_pos(head), 'head_implicit': head['implicit'],
                    'dependents': [{'token_id': d['token_id'], 'word': d.get('word'), 'rel': d['rel'], 'pos': node_pos(d),
                                    'implicit': d['implicit']} for d in deps]})
    return out


def find(out_dir=OUT, root=None, lemma=None, pos=None, text=None, function=None):
    """Word keys matching ALL given criteria. root/lemma are Buckwalter as in the Treebank; text is searched in the
    normalized spelling; function is a relation label contained in the word's function_all projection."""
    hits = []
    for k, w in words(out_dir).items():
        segs = w['segments']
        if root and not any(s.get('root', {}).get('bw') == root for s in segs):
            continue
        if lemma and not any(s.get('lemma', {}).get('bw') == lemma for s in segs):
            continue
        if pos and not any(s['pos'] == pos for s in segs):
            continue
        if text and text not in w['text_normalized']:
            continue
        if function and (not segs or function not in w['derived']['projections']['function_all'].split('+')):
            continue
        hits.append(k)
    return hits


def verb_form_table(out_dir=OUT):
    """rows[form] = {explicit, inferred, roots, lemmas, words}; root_forms[root] = {form: occurrences}."""
    W = load(out_dir)[0]
    rows = collections.OrderedDict((f, {'explicit': 0, 'inferred': 0, 'roots': set(), 'lemmas': set(), 'words': []})
                                   for f in W['reference_data']['verb_forms'])
    root_forms = collections.defaultdict(collections.Counter)
    for k, w in W['words'].items():
        for vf in w['derived'].get('verb_forms', []):
            seg = next(s for s in w['segments'] if s['location'] == vf['segment'])
            r = rows[vf['value']]
            r[vf['basis']] += 1
            r['words'].append(k)
            if 'root' in seg:
                r['roots'].add(seg['root']['bw'])
                root_forms[seg['root']['bw']][vf['value']] += 1
            if 'lemma' in seg:
                r['lemmas'].add(seg['lemma']['bw'])
    return rows, root_forms


def derived_noun_table(out_dir=OUT):
    t = collections.OrderedDict()
    for k, w in words(out_dir).items():
        for d in w['derived'].get('derived_nouns', []):
            seg = next(s for s in w['segments'] if s['location'] == d['segment'])
            r = t.setdefault(d['type'], {'count': 0, 'by_pos': collections.Counter(), 'roots': set(), 'lemmas': set()})
            r['count'] += 1
            r['by_pos'][d['pos']] += 1
            if 'root' in seg:
                r['roots'].add(seg['root']['bw'])
            if 'lemma' in seg:
                r['lemmas'].add(seg['lemma']['bw'])
    return t


# (case, relation, head POS or None) -> explanation. DERIVED reading of original annotations, never a source annotation.
CASE_RULES = [
    ('GEN', 'gen', 'P', 'genitive because it is the object of the preposition {head}'),
    ('GEN', 'Poss', None, 'genitive as the second term (possessor) of an idafa; the first term is {head}'),
    ('GEN', 'Adj', None, 'genitive by agreement with the noun it describes, {head}'),
    ('GEN', 'conj', None, 'genitive by agreement with the word it is coordinated with, {head}'),
    ('ACC', 'Obj', 'V', 'accusative as the object of the verb {head}'),
    ('ACC', 'Adj', None, 'accusative by agreement with the noun it describes, {head}'),
    ('ACC', 'conj', None, 'accusative by agreement with the word it is coordinated with, {head}'),
    ('ACC', 'subj<<in>>', None, 'accusative as the subject (ism) of inna or one of its sisters'),
    ('ACC', 'pred <<kan>>', None, 'accusative as the predicate (khabar) of kana or one of its sisters'),
    ('NOM', 'Subj', 'V', 'nominative as the subject of the verb {head}'),
    ('NOM', 'Pass', 'V', 'nominative as the subject of the passive verb {head}'),
    ('NOM', 'Pred', None, 'nominative as the predicate (khabar) of a nominal sentence'),
    ('NOM', 'root', None, 'nominative as the head of a nominal sentence'),
    ('NOM', 'Adj', None, 'nominative by agreement with the noun it describes, {head}'),
    ('NOM', 'conj', None, 'nominative by agreement with the word it is coordinated with, {head}'),
    ('NOM', 'pred<<in>>', None, 'nominative as the predicate (khabar) of inna or one of its sisters'),
    ('NOM', 'subj <<kan>>', None, 'nominative as the subject (ism) of kana or one of its sisters'),
]


def case_explanation(case, rel, head_pos, head_word_text):
    for c, r, hp, text in CASE_RULES:
        if c == case and r == rel and (hp is None or hp == head_pos):
            return text.format(head=head_word_text or '(implicit element)')
    return None


def source_issue_lists(out_dir=OUT):
    """Complete lists of every irregularity found in the source data, computed from the two layers."""
    W, S = load(out_dir)
    ws, ss = W['words'], S['sentences']
    meta_w, meta_s = W['metadata'], S['metadata']
    split = []
    for k, w in ws.items():
        sids = sorted({sg['syntax_ref']['sentence_id'] for sg in w['segments']})
        if len(sids) > 1:
            split.append({'word': k, 'text_indopak': w['text_indopak'], 'assigned_sentence': w['sentence_id'],
                          'segment_sentences': {sg['location']: sg['syntax_ref']['sentence_id'] for sg in w['segments']}})
    crossing = [{'sentence_id': int(i), 'first_word': s['span']['first_word'], 'last_word': s['span']['last_word'],
                 'ayahs': s['span']['ayahs'], 'ayah_count': len(s['span']['ayahs']), 'word_count': s['derived']['word_count']}
                for i, s in ss.items() if s['span']['crosses_ayah']]
    return {
        'merged_treebank_words': meta_w['word_alignment']['merged_treebank_words'],
        'words_split_across_sentences': split,
        'sentences_crossing_ayah': crossing,
        'prefix_only_fragment_sentences': [{'sentence_id': i, 'nodes': [
            {'word': n['word'], 'implicit': n['implicit'],
             'text_uthmani': n['morphology']['text_uthmani'] if n['implicit'] else
             next(sg['text_uthmani'] for sg in ws[n['word']]['segments'] if sg['location'] == n['segment']),
             'pos': node_pos(n)} for n in ss[str(i)]['nodes']]} for i in meta_s['source_issues']['prefix_only_fragment_sentences']],
        'text_normalized_incomplete': meta_w['source_issues']['text_normalized_incomplete']['words'],
        'segments_pos_differs_from_morphology_v04': meta_w['source_issues']['segments_pos_differs_from_morphology_v04']['segments'],
        'words_absent_in_treebank': meta_w['words_absent_in_treebank'],
    }
