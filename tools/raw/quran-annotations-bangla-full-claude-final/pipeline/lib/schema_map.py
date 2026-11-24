"""Shared mapping between Quranic.csv (Treebank) columns and the two JSON annotation layers.

Both build_grammar.py (CSV -> JSON) and validate.py (JSON -> CSV round trip) import this module,
so the column placement is defined in exactly one place.

Placement rule (every Treebank row is stored exactly once per layer that owns its columns):
  * MORPHOLOGY columns  -> word file, inside `segments[]`   (real rows)
                           sentence file, inside `nodes[].morphology` (implicit rows only)
  * SYNTAX columns      -> sentence file, on `nodes[]`      (all rows)
  * POINTER columns     -> both (tid, sentence_id, token_id, location)

Null policy: a source value of "_" means "no value". The JSON key is simply ABSENT in that case.
Two exceptions are documented in docs/SCHEMA.md: lemma_ar / root_ar hold the placeholder "ـ"
(tatweel) whenever lemma / root is absent; this is re-created on round trip, not stored.
"""
import csv
import re

LOC_RE = re.compile(r'^\((\d+):(\d+):(\d+):(\d+)\)$')
PLACEHOLDER_AR = 'ـ'           # tatweel used by the source in lemma_ar / root_ar when there is no lemma / root

# csv column -> json key, for plain string morphology fields (order = output order)
SEG_MAP = [
    ('segment', 'type'),
    ('uthmani_token', 'text_uthmani'),
    ('uthmani_unicode', 'uthmani_bw'),
    ('imlaai_token', 'text_imlaai'),
    ('imlaai_unicode', 'imlaai_bw'),
    ('phonetic', 'phonetic'),
    ('trans', 'gloss'),
    ('pos', 'pos'),
    ('pos_ar', 'pos_ar'),
    ('features', 'features_raw'),
    ('verb_form', 'verb_form_raw'),
    ('prefix', 'prefix'),
    ('suffix', 'suffix'),
    ('verb_aspect', 'aspect'),
    ('nominal_state', 'state'),
    ('verb_mood', 'mood'),
    ('special_group', 'special_group'),
    ('nominal_case', 'case'),
    ('derived_nouns', 'derived_noun'),
    ('verb_voice', 'voice'),
    ('person', 'person'),
    ('gender', 'gender'),
    ('number', 'number'),
]
# csv column -> json key, for syntax fields on a sentence node
SYN_MAP = [
    ('rel_label', 'rel'),
    ('rel_label_ar', 'rel_ar'),
    ('is_constituent', 'is_constituent'),
    ('constituents_loc', 'constituents_loc'),
    ('constituents', 'constituents_text'),
    ('constituent_label', 'constituent_label'),
]
LEMMA_COLS = (('lemma', 'lemma_ar', 'lemma'), ('root', 'root_ar', 'root'))


def read_treebank(path):
    """Return (header, rows) where rows are dicts of all 43 columns as strings."""
    with open(path, encoding='utf-16', newline='') as f:
        rd = csv.reader(f, delimiter='\t')
        header = next(rd)
        rows = []
        for r in rd:
            if len(r) != len(header):
                raise ValueError(f'bad column count {len(r)} != {len(header)} near tid {r[:1]}')
            rows.append(dict(zip(header, r)))
    return header, rows


def read_tsv16(path):
    with open(path, encoding='utf-16', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def parse_loc(loc):
    m = LOC_RE.match(loc)
    return tuple(int(x) for x in m.groups()) if m else None


def val(x):
    return None if x == '_' else x


def build_morph(row):
    """Morphology fields of one Treebank row as a dict (absent key == source '_')."""
    out = {}
    for col, key in SEG_MAP:
        v = val(row[col])
        if v is not None:
            out[key] = v
    for bw, ar, key in LEMMA_COLS:
        if row[bw] != '_':
            out[key] = {'bw': row[bw], 'ar': val(row[ar])}
        elif row[ar] != PLACEHOLDER_AR:                  # never happens in the supplied data; kept lossless anyway
            out[key + '_ar_orphan'] = row[ar]
    return out


def build_syntax(row):
    out = {'head': int(row['ref_token_id'])}
    for col, key in SYN_MAP:
        v = val(row[col])
        if v is not None:
            out[key] = v
    return out


def morph_to_cols(m):
    cols = {}
    for col, key in SEG_MAP:
        cols[col] = m.get(key, '_')
    for bw, ar, key in LEMMA_COLS:
        o = m.get(key)
        if o is None:
            cols[bw] = '_'
            cols[ar] = m.get(key + '_ar_orphan', PLACEHOLDER_AR)
        else:
            cols[bw] = o['bw']
            cols[ar] = o['ar'] if o['ar'] is not None else '_'
    return cols


def syntax_to_cols(n):
    cols = {'ref_token_id': str(n['head'])}
    for col, key in SYN_MAP:
        cols[col] = n.get(key, '_')
    return cols
