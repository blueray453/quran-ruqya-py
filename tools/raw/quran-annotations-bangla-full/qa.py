#!/usr/bin/env python3
"""qa.py — hard fences and cross-checks for the annotation layer.

Runs on every annotated surah found in annotations/:

  0. sources.lock.yaml integrity: every pinned file matches its sha256.
  1. Annotation file sanity: schema fields present, status enum valid.
  2. Ayah completeness per surah (missing ayahs are warned, not failed).
  3. Per ayah (hard fences):
       - clauses tile words 1..N exactly (N = real word count from the text source;
         keyed_max == real_max + 1 because the ayah-end marker is the last key)
       - phrases tile every clause exactly
       - every phrase has a non-empty English fragment
       - wbw gloss present for every real word (except the 3 known-missing keys)
  4. Surah 67 baseline replay: totals must be exactly 333 words / 213 phrases / 86 clauses.
  5. Chunker cross-check: chunk_end boundaries (where present) must lie on clause
     boundaries — never extra, never cutting a phrase.
  6. Recitation alignment: segments must cover words 1..N; extras are the known quirk
     (reported, handled by build.py's fallback).
  7. File separation: the English file must never carry a "bn" slot (Bangla lives in
     annotations/bn/ as a separate overlay file, never in the same file).
  8. Bangla overlay files (annotations/bn/surah-*.json): language header, structural
     identity with the English file (same ayah keys, same clause/phrase word spans —
     the bn pass is gloss-only and never re-segments), non-empty Bangla fragments,
     Bengali script in / Arabic script out, and the surah 67 bn baseline replay.
  9. Bangla wbw coverage: for every overlaid ayah and every real word 1..N, the
     Bangla wbw source must hold the gloss key — except the keys listed in
     KNOWN_MISSING_WBW_BN (initialized from the whole-Quran coverage check; the
     Bangla source is missing exactly the same 3 positions as the English one).
  10. translation_bn completeness (WARN, not FAIL — the translation source may be
     adopted incrementally): when the bn translation source is loaded, every
     overlaid ayah must have its "s:a" key there; otherwise the overlay view's
     translation_bn would be null.

Planned fence (not implemented here): EQTB clause starts ~= annotation clause starts.
See README.md.

Exit code 1 if any FAIL.
"""
import argparse, glob, hashlib, json, os, sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
KNOWN_MISSING_WBW = {('2', '181', '4'), ('8', '6', '5'), ('13', '37', '9')}
# Whole-Quran coverage check against sources/wbw/bangla-wbw-translation.json:
# the Bangla wbw source is missing exactly the same 3 real word positions as the
# English source (plus the 2:181 ayah-end marker key, which is never looked up).
KNOWN_MISSING_WBW_BN = {('2', '181', '4'), ('8', '6', '5'), ('13', '37', '9')}
BASELINE_67 = (333, 213, 86)
STATUS_ENUM = {'auto', 'needs_human', 'reviewed'}
CONVENTIONS_VERSION = '2.1'


def is_bengali(ch):
    return '\u0980' <= ch <= '\u09FF'


def is_arabic_script(ch):
    return ('\u0600' <= ch <= '\u06FF' or '\u0750' <= ch <= '\u077F'
            or '\u08A0' <= ch <= '\u08FF' or '\uFB50' <= ch <= '\uFDFF'
            or '\uFE70' <= ch <= '\uFEFF')


class Report:
    def __init__(self):
        self.lines, self.fails, self.warns = [], 0, 0

    def ok(self, m):   self.lines.append(('PASS', m))
    def fail(self, m): self.lines.append(('FAIL', m)); self.fails += 1
    def warn(self, m): self.lines.append(('WARN', m)); self.warns += 1
    def info(self, m): self.lines.append(('INFO', m))

    def dump(self):
        for tag, m in self.lines:
            print(f'{tag:>4}  {m}')
        print()
        print(f'summary: {self.fails} FAIL, {self.warns} WARN, '
              f'{sum(1 for t, _ in self.lines if t == "PASS")} PASS')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def parse_lock(path):
    """Minimal parser for the exact YAML subset emitted into sources.lock.yaml."""
    fams, cur = [], None
    for line in open(path, encoding='utf-8'):
        s = line.rstrip('\n')
        if s.startswith('  - id: '):
            cur = {'id': s[len('  - id: '):], 'files': []}
            fams.append(cur)
        elif s.startswith('      - path: ') and cur is not None:
            cur['files'].append({'path': s[len('      - path: '):], 'sha256': None})
        elif s.startswith('        sha256: ') and cur is not None and cur['files']:
            cur['files'][-1]['sha256'] = s[len('        sha256: '):]
    return fams


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


class Sources:
    def __init__(self):
        self.indopak = load_json(os.path.join(ROOT, 'sources/text/indopak.json'))
        self.wbw = load_json(os.path.join(ROOT, 'sources/wbw/english-wbw-translation.json'))
        self.wbw_bn = load_json(os.path.join(ROOT, 'sources/wbw/bangla-wbw-translation.json'))
        # bn translation source: detected by filename hint, same scheme as build.py's
        # load_translations(); None when the family is not adopted yet.
        self.translation_bn = None
        for p in sorted(glob.glob(os.path.join(ROOT, 'sources/translation', '*.json'))):
            name = os.path.basename(p)
            if 'bn-' in name or '-bn-' in name:
                data = load_json(p)
                self.translation_bn = {k: (v.get('t') if isinstance(v, dict) else v)
                                       for k, v in data.items()}
                break
        ap = os.path.join(ROOT, 'sources/audio/ar.alafasy.json')
        self.audio = load_json(ap) if os.path.exists(ap) else {}
        # keyed counts per surah/ayah (indopak: includes the ayah-end marker as last key)
        self.maxkey = {}
        self.ayahs_of = {}
        for k in self.indopak:
            s, a, w = k.split(':')
            w = int(w)
            if self.maxkey.get((s, a), 0) < w:
                self.maxkey[(s, a)] = w
            self.ayahs_of.setdefault(int(s), set()).add(int(a))
        # chunker chunk_end boundaries: {(chapter, verse): [token numbers]}
        self.chunk_ends = {}
        cpath = os.path.join(ROOT, 'sources/chunker/quranic-treebank-0.4-chunks.tsv')
        if os.path.exists(cpath):
            with open(cpath, encoding='utf-8') as f:
                next(f)
                for line in f:
                    c = line.rstrip('\n').split('\t')
                    if len(c) < 9:
                        continue
                    ch, ve, tok = int(c[0]), int(c[1]), int(c[2])
                    if c[8] == '1':
                        self.chunk_ends.setdefault((ch, ve), []).append(tok)

    def n_words(self, s, a):
        """Real word count: last keyed word is the ayah-end marker."""
        return self.maxkey[(str(s), str(a))] - 1

    def n_ayahs(self, s):
        return len(self.ayahs_of[int(s)])


def qa_surah(rep, s, doc, src):
    if doc.get('surah') != s:
        rep.fail(f'surah {s}: file header says surah={doc.get("surah")}')
    if doc.get('schema_version') != '1.0':
        rep.fail(f'surah {s}: unknown schema_version {doc.get("schema_version")}')
    if doc.get('conventions_version') != CONVENTIONS_VERSION:
        rep.fail(f'surah {s}: unknown conventions_version {doc.get("conventions_version")}')
    if not isinstance(doc.get('provenance'), dict):
        rep.fail(f'surah {s}: provenance block missing')

    n_ayahs = src.n_ayahs(s)
    annotated = {int(k) for k in doc.get('ayahs', {})}
    missing = sorted(set(range(1, n_ayahs + 1)) - annotated)
    if missing:
        rep.warn(f'surah {s}: {len(missing)}/{n_ayahs} ayah(s) not annotated yet '
                 f'(e.g. {missing[:8]})')
    else:
        rep.ok(f'surah {s}: all {n_ayahs} ayahs annotated')

    tot_w = tot_p = tot_c = 0
    size_dist = Counter()
    for a in sorted(annotated):
        entry = doc['ayahs'][str(a)]
        if entry.get('status') not in STATUS_ENUM:
            rep.fail(f'{s}:{a}: bad status {entry.get("status")!r}')
        N = src.n_words(s, a)
        covered, clause_ends = [], set()
        for ci, cl in enumerate(entry.get('clauses', []), 1):
            cw = cl.get('words', [])
            if cw != list(range(min(cw), max(cw) + 1)):
                rep.fail(f'{s}:{a} clause {ci}: word list not contiguous: {cw}')
            covered += cw
            clause_ends.add(max(cw))
            pw = []
            for pi, ph in enumerate(cl.get('phrases', []), 1):
                pwc = ph.get('words', [])
                if pwc != list(range(min(pwc), max(pwc) + 1)):
                    rep.fail(f'{s}:{a} clause {ci} phrase {pi}: not contiguous: {pwc}')
                if not isinstance(ph.get('en'), str) or not ph['en'].strip():
                    rep.fail(f'{s}:{a} clause {ci} phrase {pi}: empty en fragment')
                if 'bn' in ph:
                    rep.fail(f'{s}:{a} clause {ci} phrase {pi}: bn slot inside the English '
                             f'annotation file (Bangla must live in annotations/bn/)')
                pw += pwc
                size_dist[len(pwc)] += 1
                tot_p += 1
            if sorted(pw) != sorted(cw):
                rep.fail(f'{s}:{a} clause {ci}: phrases do not tile the clause')
        if sorted(covered) != list(range(1, N + 1)):
            rep.fail(f'{s}:{a}: clauses do not tile words 1..{N}')
        tot_c += len(entry.get('clauses', []))
        tot_w += N

        segs = src.audio.get(f'{s}:{a}')
        if segs:
            nums = sorted(seg[0] for seg in segs['segments'])
            if nums != list(range(1, N + 1)):
                rep.info(f'{s}:{a}: recitation has {len(nums) - N} extra segment(s) beyond words 1..{N} '
                         f'(known quirk; fallback applied at build time)')
        miss_gloss = [w for w in range(1, N + 1)
                      if f'{s}:{a}:{w}' not in src.wbw
                      and (str(s), str(a), str(w)) not in KNOWN_MISSING_WBW]
        if miss_gloss:
            rep.fail(f'{s}:{a}: wbw gloss missing for word(s) {miss_gloss} (not in known-missing list)')

    big = sorted(w for w, c in size_dist.items() if w > 3)
    if big:
        share = sum(size_dist[w] for w in big) / max(1, tot_p)
        rep.warn(f'surah {s}: {share:.1%} of phrases are >3 words (baseline is ~2%); sizes {dict((w, size_dist[w]) for w in big)}')

    # chunker cross-check: chunk_end tokens must land on clause boundaries
    checked = violated = 0
    for (ch, ve), ends in src.chunk_ends.items():
        if ch != s or str(ve) not in doc.get('ayahs', {}):
            continue
        ce = set()
        for cl in doc['ayahs'][str(ve)]['clauses']:
            ce.add(max(cl['words']))
        checked += 1
        bad = [e for e in ends if e not in ce]
        if bad:
            violated += 1
            rep.fail(f'{s}:{ve}: chunker boundary at word(s) {bad} cuts a clause/phrase')
    if checked:
        if violated == 0:
            rep.ok(f'surah {s}: chunker boundaries are a subset of clause boundaries '
                   f'({checked} ayahs cross-checked)')
    else:
        rep.info(f'surah {s}: no chunker coverage for annotated ayahs')

    if s == 67:
        got = (tot_w, tot_p, tot_c)
        if got == BASELINE_67:
            rep.ok(f'surah 67 baseline replay: {got[0]} words / {got[1]} phrases / {got[2]} clauses')
        else:
            rep.fail(f'surah 67 baseline replay MISMATCH: {got} != {BASELINE_67}')


def qa_surah_bn(rep, s, bn_doc, en_doc, src):
    """Fences for a Bangla overlay file: separate by design, structurally identical."""
    if bn_doc.get('surah') != s:
        rep.fail(f'bn surah {s}: file header says surah={bn_doc.get("surah")}')
    if bn_doc.get('language') != 'bn':
        rep.fail(f'bn surah {s}: language must be "bn", got {bn_doc.get("language")!r}')
    if bn_doc.get('schema_version') != '1.0':
        rep.fail(f'bn surah {s}: unknown schema_version {bn_doc.get("schema_version")}')
    if bn_doc.get('conventions_version') != CONVENTIONS_VERSION:
        rep.fail(f'bn surah {s}: unknown conventions_version {bn_doc.get("conventions_version")}')
    if not isinstance(bn_doc.get('provenance'), dict):
        rep.fail(f'bn surah {s}: provenance block missing')
    if en_doc is None:
        rep.fail(f'bn surah {s}: overlay exists but no English annotation to mirror')
        return

    en_ayahs = {int(k) for k in en_doc.get('ayahs', {})}
    bn_ayahs = {int(k) for k in bn_doc.get('ayahs', {})}
    extra = sorted(bn_ayahs - en_ayahs)
    if extra:
        rep.fail(f'bn surah {s}: overlay annotates ayah(s) {extra} absent from the English file '
                 f'(the bn pass is gloss-only and cannot create ayahs)')
    missing = sorted(en_ayahs - bn_ayahs)
    if missing:
        rep.warn(f'bn surah {s}: {len(missing)}/{len(en_ayahs)} English-annotated ayah(s) have '
                 f'no bn overlay yet (e.g. {missing[:8]})')

    tot_w = tot_p = tot_c = 0
    miss_wbw_bn, miss_tr_bn = [], []
    for a in sorted(bn_ayahs & en_ayahs):
        bn_entry = bn_doc['ayahs'][str(a)]
        en_entry = en_doc['ayahs'][str(a)]
        if bn_entry.get('status') not in STATUS_ENUM:
            rep.fail(f'bn {s}:{a}: bad status {bn_entry.get("status")!r}')
        bn_cls, en_cls = bn_entry.get('clauses', []), en_entry.get('clauses', [])
        if len(bn_cls) != len(en_cls):
            rep.fail(f'bn {s}:{a}: {len(bn_cls)} clauses vs {len(en_cls)} in the English file '
                     f'(re-segmentation is forbidden)')
            continue
        for ci, (bcl, ecl) in enumerate(zip(bn_cls, en_cls), 1):
            if bcl.get('words') != ecl.get('words'):
                rep.fail(f'bn {s}:{a} clause {ci}: clause word span differs from the English file')
                continue
            bphs, ephs = bcl.get('phrases', []), ecl.get('phrases', [])
            if len(bphs) != len(ephs):
                rep.fail(f'bn {s}:{a} clause {ci}: {len(bphs)} phrases vs {len(ephs)} in the English file')
                continue
            for pi, (bph, eph) in enumerate(zip(bphs, ephs), 1):
                if bph.get('words') != eph.get('words'):
                    rep.fail(f'bn {s}:{a} clause {ci} phrase {pi}: phrase word span differs from the English file')
                if 'en' in bph:
                    rep.fail(f'bn {s}:{a} clause {ci} phrase {pi}: en content leaked into the bn overlay')
                frag = bph.get('bn')
                if not isinstance(frag, str) or not frag.strip():
                    rep.fail(f'bn {s}:{a} clause {ci} phrase {pi}: empty bn fragment')
                    continue
                if not any(is_bengali(c) for c in frag):
                    rep.fail(f'bn {s}:{a} clause {ci} phrase {pi}: no Bengali script in fragment {frag!r}')
                if any(is_arabic_script(c) for c in frag):
                    rep.fail(f'bn {s}:{a} clause {ci} phrase {pi}: Arabic script in bn fragment {frag!r}')
                if any(c.isascii() and c.isalpha() for c in frag):
                    rep.warn(f'bn {s}:{a} clause {ci} phrase {pi}: ASCII letters in bn fragment {frag!r}')
            tot_p += len(bphs)
            tot_w += len(bcl['words'])
        tot_c += len(bn_cls)

        N = src.n_words(s, a)
        miss_gloss_bn = [w for w in range(1, N + 1)
                         if f'{s}:{a}:{w}' not in src.wbw_bn
                         and (str(s), str(a), str(w)) not in KNOWN_MISSING_WBW_BN]
        if miss_gloss_bn:
            miss_wbw_bn.extend(f'{s}:{a}:{w}' for w in miss_gloss_bn)
        if src.translation_bn is not None and f'{s}:{a}' not in src.translation_bn:
            miss_tr_bn.append(f'{s}:{a}')

    if miss_wbw_bn:
        rep.fail(f'bn surah {s}: wbw_bn gloss missing for word(s) {miss_wbw_bn[:8]}'
                 f'{" ..." if len(miss_wbw_bn) > 8 else ""} (not in KNOWN_MISSING_WBW_BN)')
    elif bn_ayahs & en_ayahs:
        rep.ok(f'bn surah {s}: wbw_bn coverage complete for all {len(bn_ayahs & en_ayahs)} '
               f'overlaid ayahs ({len(KNOWN_MISSING_WBW_BN)} known-missing keys excluded)')
    if miss_tr_bn:
        rep.warn(f'bn surah {s}: bn translation source lacks key(s) {miss_tr_bn[:8]}'
                 f'{" ..." if len(miss_tr_bn) > 8 else ""} — translation_bn would be null '
                 f'in the overlay view')
    elif bn_ayahs & en_ayahs and src.translation_bn is not None:
        rep.ok(f'bn surah {s}: bn translation source covers all {len(bn_ayahs & en_ayahs)} '
               f'overlaid ayahs')
    elif src.translation_bn is None:
        rep.info(f'bn surah {s}: no bn translation source loaded; translation_bn joins skipped')

    if s == 67 and not missing:
        got = (tot_w, tot_p, tot_c)
        if got == BASELINE_67:
            rep.ok(f'bn surah 67 baseline replay: {got[0]} words / {got[1]} phrases / {got[2]} clauses '
                   f'(mirrors the English file)')
        else:
            rep.fail(f'bn surah 67 baseline replay MISMATCH: {got} != {BASELINE_67}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--surah', type=int, action='append', help='only these surahs (repeatable)')
    args = ap.parse_args()

    rep = Report()

    lock_path = os.path.join(ROOT, 'sources.lock.yaml')
    if not os.path.exists(lock_path):
        rep.fail('sources.lock.yaml missing')
    else:
        bad = []
        fams = parse_lock(lock_path)
        for fam in fams:
            for f in fam['files']:
                p = os.path.join(ROOT, f['path'])
                if not os.path.exists(p):
                    bad.append(f'{f["path"]} (missing)')
                elif sha256(p) != f['sha256']:
                    bad.append(f'{f["path"]} (hash mismatch)')
        if bad:
            rep.fail(f'source integrity: {len(bad)} file(s) deviate from the lock: {bad[:5]}')
        else:
            rep.ok(f'source integrity: all {sum(len(f["files"]) for f in fams)} pinned files match sha256')

    src = Sources()
    pattern = os.path.join(ROOT, 'annotations', 'surah-*.json')
    files = sorted(glob.glob(pattern))
    if not files:
        rep.fail('no annotations/surah-*.json files found')
    en_docs = {}
    for path in files:
        s = int(os.path.basename(path)[6:9])
        if args.surah and s not in args.surah:
            continue
        en_docs[s] = load_json(path)
        qa_surah(rep, s, en_docs[s], src)

    bn_files = sorted(glob.glob(os.path.join(ROOT, 'annotations', 'bn', 'surah-*.json')))
    for path in bn_files:
        s = int(os.path.basename(path)[6:9])
        if args.surah and s not in args.surah:
            continue
        qa_surah_bn(rep, s, load_json(path), en_docs.get(s), src)
    if not bn_files:
        rep.info('no Bangla overlay files (annotations/bn/) found — English-only run')

    rep.info('planned fence (not implemented here): EQTB clause starts ~= annotation clause starts; '
             'waqf marks -> clause starts. See README.md.')
    rep.dump()
    sys.exit(1 if rep.fails else 0)


if __name__ == '__main__':
    main()
