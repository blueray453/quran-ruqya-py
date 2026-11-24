"""Helpers shared by the table-building stages (05-10). Everything is computed from the two JSON layers only
(through grammar_data); nothing reads the Treebank or any other source file.
"""
import collections
import csv
import hashlib
import json
import os
import re

import grammar_data as G

CONTENT_POS = {'N', 'V', 'ADJ', 'PN'}
_TRAIL = re.compile('[\\s.,;:!?"\u201c\u201d\u200b\u200e\u200f]+$')
_LEAD = re.compile('^[\\s"\u201c\u201d\u200b\u200e\u200f]+')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def surah(key):
    return int(key.split(':')[0])


def ayah_key(key):
    return key.rsplit(':', 1)[0]


def clean_gloss(g):
    """Gloss as given in the notes, with surrounding whitespace, trailing punctuation and wrapping quotes removed."""
    return _TRAIL.sub('', _LEAD.sub('', g))


def top_glosses(counter, n=3):
    return ' | '.join('%s (%d)' % (g, c) for g, c in counter.most_common(n))


def first_gloss(counter):
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if counter else None


def most_common(counter):
    """Most common key; ties broken alphabetically so output is deterministic."""
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if counter else None


def segments(out_dir=G.OUT):
    """(word key, word record, segment) for every segment in Quran order."""
    for k, w in G.words(out_dir).items():
        for s in w['segments']:
            yield k, w, s


def stems(word):
    return [s for s in word['segments'] if s['type'] == 'STEM']


class Table:
    """Writes CSVs (UTF-8 with BOM, like the original project) and remembers row counts for the stage report."""

    def __init__(self, folder, stage, out_dir=G.OUT):
        self.dir = os.path.join(out_dir, folder)
        os.makedirs(self.dir, exist_ok=True)
        self.folder, self.stage, self.out_dir = folder, stage, out_dir
        self.files = collections.OrderedDict()

    def write(self, name, header, rows):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(header)
            n = 0
            for r in rows:
                w.writerow(['' if v is None else v for v in r])
                n += 1
        self.files[name] = {'rows': n, 'columns': len(header)}
        return n

    def finish(self, extra=None):
        rep = {'stage': self.stage, 'source_policy': 'computed from the two JSON layers only',
               'input_sha256': {fn: sha256(os.path.join(self.out_dir, fn)) for fn in (G.WORD_FILE, G.SENT_FILE)},
               'files': self.files}
        if extra:
            rep.update(extra)
        with open(os.path.join(self.dir, 'tables-report-%s.json' % self.stage), 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        for n, v in self.files.items():
            print('  %-58s %7d rows' % (self.folder + '/' + n, v['rows']))
        return rep


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


class Stats:
    """Counts of one item plus where and how it occurs (first location, surah spread, glosses, POS mix)."""
    __slots__ = ('count', 'pos', 'gloss', 'surahs', 'first', 'text', 'extra')

    def __init__(self):
        self.count = 0
        self.pos = collections.Counter()
        self.gloss = collections.Counter()
        self.surahs = set()
        self.first = None
        self.text = None
        self.extra = collections.Counter()

    def add(self, key, word, seg):
        self.count += 1
        self.pos[seg['pos']] += 1
        if 'gloss' in seg:
            self.gloss[clean_gloss(seg['gloss'])] += 1
        self.surahs.add(surah(key))
        if self.first is None:
            self.first, self.text = key, word['text_indopak']


class SyntaxIndex:
    """Joins word segments with their sentence-layer nodes (relation, head, dependents)."""

    def __init__(self, out_dir=G.OUT):
        self.W, self.S = G.words(out_dir), G.sentences(out_dir)
        self.seg = {}
        for k, w in self.W.items():
            for s in w['segments']:
                self.seg[(k, s['location'])] = s

    def node(self, seg):
        r = seg['syntax_ref']
        return self.S[str(r['sentence_id'])]['nodes'][r['token_id']], str(r['sentence_id'])

    def head_node(self, sid, node):
        return self.S[sid]['nodes'][node['head']]

    def dependents(self, sid, node):
        return [d for d in self.S[sid]['nodes'] if d['head'] == node['token_id'] and d['token_id'] != node['token_id']]

    def seg_of(self, node):
        """Word segment of a (non-implicit) node, or None."""
        return self.seg.get((node['word'], node['segment'])) if node.get('word') else None

    def label(self, node):
        """Lemma (Buckwalter) of a node's segment, else '<POS>' (implicit nodes use their morphology)."""
        s = self.seg_of(node)
        if s is None:
            m = node.get('morphology', {})
            return m.get('lemma', {}).get('bw') or '<%s>' % m.get('pos', '?')
        return s.get('lemma', {}).get('bw') or '<%s>' % s['pos']

    def label_ar(self, node):
        s = self.seg_of(node)
        m = s if s is not None else node.get('morphology', {})
        return m.get('lemma', {}).get('ar') or m.get('text_uthmani')


def verb_form_by_segment(word):
    return {v['segment']: v['value'] for v in word['derived']['verb_forms']}


def derived_type_by_segment(word):
    return {d['segment']: d['type'] for d in word['derived']['derived_nouns']}


def pgn(s):
    """Person-gender-number label such as 3MS (gender blank when the notes give none)."""
    return '%s%s%s' % (s.get('person', ''), s.get('gender', ''), s.get('number', ''))


def prep_id(seg):
    """Identity of a preposition segment: its lemma (e.g. fiY) or, for attached prefixes, its prefix tag (e.g. bi+)."""
    return seg.get('lemma', {}).get('bw') or seg.get('prefix') or seg.get('suffix') or '<P>'


def greedy_cover(units, universe):
    """Lazy greedy set cover (same method as the original memorization order). units: list of (cost, [item ids]); items are
    ints < universe. Efficiency = newly covered items / cost; ties go to the earlier unit. Returns
    [(unit index, newly covered, cumulative covered, cumulative cost)]."""
    import heapq
    cov = bytearray(universe)
    gain = lambda j: sum(1 for i in units[j][1] if not cov[i])
    heap = [(-gain(j) / units[j][0], j) for j in range(len(units))]
    heapq.heapify(heap)
    sel, cum, cost = [], 0, 0
    while heap:
        _, j = heapq.heappop(heap)
        gn = gain(j)
        if gn == 0:
            continue
        eff = gn / units[j][0]
        if heap and eff < -heap[0][0] - 1e-12:
            heapq.heappush(heap, (-eff, j))
            continue
        for i in units[j][1]:
            cov[i] = 1
        cum += gn
        cost += units[j][0]
        sel.append((j, gn, cum, cost))
    return sel
