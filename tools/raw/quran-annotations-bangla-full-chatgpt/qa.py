#!/usr/bin/env python3
"""Validate flat chunk annotations, Bangla overlays, and pinned source integrity.

Schema 2.0 (`chunks[]`) is the current format. Schema 1.0 (`clauses[].phrases[]`) remains
readable for legacy annotations. New annotations have no clause-size or clause-boundary QA.
"""
import argparse
import glob
import hashlib
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
from ayahlib import terminology_flags  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
KNOWN_MISSING_WBW = {('2', '181', '4'), ('8', '6', '5'), ('13', '37', '9')}
KNOWN_MISSING_WBW_BN = {('2', '181', '4'), ('8', '6', '5'), ('13', '37', '9')}
STATUS_ENUM = {'auto', 'needs_human', 'reviewed'}
LEGACY_BASELINE_67 = (333, 213, 86)
FLAT_BASELINE_67 = (333, 213)
BASELINE_ON = True


def is_bengali(ch):
    return '\u0980' <= ch <= '\u09FF'


def is_arabic_script(ch):
    return ('\u0600' <= ch <= '\u06FF' or '\u0750' <= ch <= '\u077F'
            or '\u08A0' <= ch <= '\u08FF' or '\uFB50' <= ch <= '\uFDFF'
            or '\uFE70' <= ch <= '\uFEFF')


class Report:
    def __init__(self):
        self.lines, self.fails, self.warns = [], 0, 0

    def ok(self, message): self.lines.append(('PASS', message))
    def fail(self, message): self.lines.append(('FAIL', message)); self.fails += 1
    def warn(self, message): self.lines.append(('WARN', message)); self.warns += 1
    def info(self, message): self.lines.append(('INFO', message))

    def dump(self):
        for tag, message in self.lines:
            print(f'{tag:>4}  {message}')
        print(f'\nsummary: {self.fails} FAIL, {self.warns} WARN, '
              f'{sum(1 for tag, _ in self.lines if tag == "PASS")} PASS')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def parse_lock(path):
    """Minimal parser for the exact YAML subset in sources.lock.yaml."""
    families, current = [], None
    for line in open(path, encoding='utf-8'):
        value = line.rstrip('\n')
        if value.startswith('  - id: '):
            current = {'id': value[len('  - id: '):], 'files': []}
            families.append(current)
        elif value.startswith('      - path: ') and current is not None:
            current['files'].append({'path': value[len('      - path: '):], 'sha256': None})
        elif value.startswith('        sha256: ') and current is not None and current['files']:
            current['files'][-1]['sha256'] = value[len('        sha256: '):]
    return families


def load_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


class Sources:
    def __init__(self):
        self.indopak = load_json(os.path.join(ROOT, 'sources/text/indopak.json'))
        self.wbw = load_json(os.path.join(ROOT, 'sources/wbw/english-wbw-translation.json'))
        self.wbw_bn = load_json(os.path.join(ROOT, 'sources/wbw/bangla-wbw-translation.json'))
        self.translation_bn = None
        for path in sorted(glob.glob(os.path.join(ROOT, 'sources/translation', '*.json'))):
            name = os.path.basename(path)
            if 'bn-' in name or '-bn-' in name:
                data = load_json(path)
                self.translation_bn = {k: (v.get('t') if isinstance(v, dict) else v) for k, v in data.items()}
                break
        self.audio = {}
        audio_path = os.path.join(ROOT, 'sources/audio/ar.alafasy.json')
        if os.path.exists(audio_path):
            self.audio = load_json(audio_path)
        self.maxkey, self.ayahs_of, self.chunk_ends = {}, {}, {}
        for key in self.indopak:
            surah, ayah, word = key.split(':')
            word = int(word)
            self.maxkey[(surah, ayah)] = max(self.maxkey.get((surah, ayah), 0), word)
            self.ayahs_of.setdefault(int(surah), set()).add(int(ayah))
        chunker_path = os.path.join(ROOT, 'sources/chunker/quranic-treebank-0.4-chunks.tsv')
        if os.path.exists(chunker_path):
            with open(chunker_path, encoding='utf-8') as fh:
                next(fh, None)
                for line in fh:
                    cols = line.rstrip('\n').split('\t')
                    if len(cols) < 9:
                        continue
                    surah, ayah, token = int(cols[0]), int(cols[1]), int(cols[2])
                    if cols[8] == '1':
                        self.chunk_ends.setdefault((surah, ayah), []).append(token)

    def n_words(self, surah, ayah):
        return self.maxkey[(str(surah), str(ayah))] - 1

    def n_ayahs(self, surah):
        return len(self.ayahs_of[int(surah)])


def iter_chunks(entry):
    if 'chunks' in entry:
        return entry['chunks']
    return [phrase for clause in entry.get('clauses', []) for phrase in clause.get('phrases', [])]


def validate_span(rep, key, label, words, expected=None):
    if not isinstance(words, list) or not words or not all(isinstance(w, int) for w in words):
        rep.fail(f'{key} {label}: empty/invalid word positions {words!r}')
        return []
    if words != list(range(words[0], words[-1] + 1)):
        rep.fail(f'{key} {label}: word list is not contiguous: {words}')
    if expected is not None and words[0] != expected:
        rep.fail(f'{key} {label}: starts at word {words[0]}, expected {expected} (gap/overlap/reorder)')
    return words


def validate_english_doc(rep, surah, doc, src):
    if doc.get('surah') != surah:
        rep.fail(f'surah {surah}: file header says surah={doc.get("surah")}')
    schema = doc.get('schema_version')
    convention = doc.get('conventions_version')
    if (schema, convention) not in {('1.0', '2.2'), ('2.0', '3.0'), ('2.0', '4.0') }:
        rep.fail(f'surah {surah}: unsupported schema/conventions versions {schema}/{convention}')
    if not isinstance(doc.get('provenance'), dict):
        rep.fail(f'surah {surah}: provenance block missing')

    annotated = {int(key) for key in doc.get('ayahs', {})}
    missing = sorted(set(range(1, src.n_ayahs(surah) + 1)) - annotated)
    if missing:
        rep.warn(f'surah {surah}: {len(missing)}/{src.n_ayahs(surah)} ayah(s) not annotated yet (e.g. {missing[:8]})')
    else:
        rep.ok(f'surah {surah}: all {src.n_ayahs(surah)} ayahs annotated')

    total_words = total_chunks = total_clauses = 0
    size_dist = Counter()
    flat = schema == '2.0'
    for ayah in sorted(annotated):
        key = f'{surah}:{ayah}'
        entry = doc['ayahs'][str(ayah)]
        if entry.get('status') not in STATUS_ENUM:
            rep.fail(f'{key}: bad status {entry.get("status")!r}')
        n = src.n_words(surah, ayah)
        chunks = iter_chunks(entry)
        expected = 1
        covered = []
        for ci, chunk in enumerate(chunks, 1):
            words = validate_span(rep, key, f'chunk {ci}', chunk.get('words'), expected)
            if words:
                expected = words[-1] + 1
                covered.extend(words)
                size_dist[len(words)] += 1
            if not isinstance(chunk.get('en'), str) or not chunk['en'].strip():
                rep.fail(f'{key} chunk {ci}: empty en fragment')
            else:
                for issue in terminology_flags(chunk.get('en'), None):
                    rep.fail(f'{key} chunk {ci}: {issue}')
            if 'bn' in chunk:
                rep.fail(f'{key} chunk {ci}: bn slot inside English annotation; Bangla must live in annotations/bn/')
        if covered != list(range(1, n + 1)):
            rep.fail(f'{key}: chunks do not tile words 1..{n} in order (covered {len(covered)} positions)')
        total_words += n
        total_chunks += len(chunks)
        if not flat:
            total_clauses += len(entry.get('clauses', []))
        if not chunks:
            rep.fail(f'{key}: no chunks')

        segs = src.audio.get(key)
        if segs:
            nums = sorted(seg[0] for seg in segs['segments'])
            if nums != list(range(1, n + 1)):
                rep.info(f'{key}: recitation has {len(nums) - n} extra segment(s) beyond words 1..{n} (known quirk)')
        missing_gloss = [w for w in range(1, n + 1)
                         if f'{surah}:{ayah}:{w}' not in src.wbw
                         and (str(surah), str(ayah), str(w)) not in KNOWN_MISSING_WBW]
        if missing_gloss:
            rep.fail(f'{key}: English wbw gloss missing for word(s) {missing_gloss} (not in known-missing list)')

        if flat and (surah, ayah) in src.chunk_ends:
            ends = set(src.chunk_ends[(surah, ayah)])
            chunk_ends = {c['words'][-1] for c in chunks if c.get('words')}
            inside = sorted(e for e in ends if e not in chunk_ends and any(
                c['words'][0] <= e < c['words'][-1] for c in chunks if c.get('words')))
            rep.info(f'{key}: chunker boundary diagnostic — {len(ends & chunk_ends)}/{len(ends)} '
                     f'treebank ends coincide with annotation chunk ends; {len(inside)} fall inside an annotation chunk '
                     '(diagnostic only; not a pass/fail fence)')
        elif not flat:
            # Legacy contract only: chunker ends were historically checked against clause ends.
            clause_ends = {cl['words'][-1] for cl in entry.get('clauses', []) if cl.get('words')}
            ends = set(src.chunk_ends.get((surah, ayah), []))
            bad = sorted(ends - clause_ends)
            if bad:
                rep.fail(f'{key}: legacy chunker boundary at word(s) {bad} is not a clause end')

    large = {words: count for words, count in size_dist.items() if words > 4}
    if large:
        share = sum(large.values()) / max(1, total_chunks)
        rep.warn(f'surah {surah}: {share:.1%} of chunks exceed 4 words; inspect these rather than splitting mechanically: {large}')

    provenance = doc.get('provenance', {})
    if surah == 67 and BASELINE_ON and provenance.get('generator') == 'prototype-replay':
        if flat:
            got = (total_words, total_chunks)
            if got == FLAT_BASELINE_67:
                rep.ok(f'surah 67 flat prototype replay: {got[0]} words / {got[1]} chunks')
            else:
                rep.fail(f'surah 67 flat prototype replay mismatch: {got} != {FLAT_BASELINE_67}')
        else:
            got = (total_words, total_chunks, total_clauses)
            if got == LEGACY_BASELINE_67:
                rep.ok(f'surah 67 legacy prototype replay: {got[0]} words / {got[1]} phrases / {got[2]} clauses')
            else:
                rep.fail(f'surah 67 legacy prototype replay mismatch: {got} != {LEGACY_BASELINE_67}')


def validate_bangla_doc(rep, surah, bn_doc, en_doc, src):
    if bn_doc.get('surah') != surah:
        rep.fail(f'bn surah {surah}: file header says surah={bn_doc.get("surah")}')
    if bn_doc.get('language') != 'bn':
        rep.fail(f'bn surah {surah}: language must be "bn", got {bn_doc.get("language")!r}')
    schema = bn_doc.get('schema_version')
    if (schema, bn_doc.get('conventions_version')) not in {('1.0', '2.2'), ('2.0', '3.0'), ('2.0', '4.0')}:
        rep.fail(f'bn surah {surah}: unsupported schema/conventions version')
    if not isinstance(bn_doc.get('provenance'), dict):
        rep.fail(f'bn surah {surah}: provenance block missing')
    if en_doc is None:
        rep.fail(f'bn surah {surah}: overlay exists but no English annotation to mirror')
        return
    en_ayahs = {int(key) for key in en_doc.get('ayahs', {})}
    bn_ayahs = {int(key) for key in bn_doc.get('ayahs', {})}
    extra, missing = sorted(bn_ayahs - en_ayahs), sorted(en_ayahs - bn_ayahs)
    if extra:
        rep.fail(f'bn surah {surah}: overlay ayahs {extra} are absent from English file')
    if missing:
        rep.warn(f'bn surah {surah}: {len(missing)}/{len(en_ayahs)} English ayah(s) have no Bangla overlay (e.g. {missing[:8]})')

    missing_wbw_bn, missing_translation_bn = [], []
    for ayah in sorted(bn_ayahs & en_ayahs):
        key = f'{surah}:{ayah}'
        bn_entry, en_entry = bn_doc['ayahs'][str(ayah)], en_doc['ayahs'][str(ayah)]
        if bn_entry.get('status') not in STATUS_ENUM:
            rep.fail(f'bn {key}: bad status {bn_entry.get("status")!r}')
        bn_chunks, en_chunks = iter_chunks(bn_entry), iter_chunks(en_entry)
        if len(bn_chunks) != len(en_chunks):
            rep.fail(f'bn {key}: {len(bn_chunks)} chunks vs {len(en_chunks)} in English; re-segmentation is forbidden')
            continue
        for i, (bn_chunk, en_chunk) in enumerate(zip(bn_chunks, en_chunks), 1):
            if bn_chunk.get('words') != en_chunk.get('words'):
                rep.fail(f'bn {key} chunk {i}: word span differs from English file')
            if 'en' in bn_chunk:
                rep.fail(f'bn {key} chunk {i}: en content leaked into Bangla overlay')
            fragment = bn_chunk.get('bn')
            if not isinstance(fragment, str) or not fragment.strip():
                rep.fail(f'bn {key} chunk {i}: empty Bangla fragment')
                continue
            if not any(is_bengali(ch) for ch in fragment):
                rep.fail(f'bn {key} chunk {i}: no Bengali script in {fragment!r}')
            if any(is_arabic_script(ch) for ch in fragment):
                rep.fail(f'bn {key} chunk {i}: Arabic script in Bangla fragment {fragment!r}')
            for issue in terminology_flags('', fragment):
                rep.fail(f'bn {key} chunk {i}: {issue}')
            if any(ch.isascii() and ch.isalpha() for ch in fragment):
                rep.warn(f'bn {key} chunk {i}: ASCII letters in Bangla fragment {fragment!r}')
        n = src.n_words(surah, ayah)
        missing_wbw_bn.extend(f'{key}:{w}' for w in range(1, n + 1)
                              if f'{key}:{w}' not in src.wbw_bn
                              and (str(surah), str(ayah), str(w)) not in KNOWN_MISSING_WBW_BN)
        if src.translation_bn is not None and key not in src.translation_bn:
            missing_translation_bn.append(key)
    if missing_wbw_bn:
        rep.fail(f'bn surah {surah}: Bangla wbw gloss missing for {missing_wbw_bn[:8]}')
    elif bn_ayahs & en_ayahs:
        rep.ok(f'bn surah {surah}: Bangla wbw coverage complete (known-missing positions excluded)')
    if missing_translation_bn:
        rep.warn(f'bn surah {surah}: Bangla reference translation missing for {missing_translation_bn[:8]}')
    elif src.translation_bn is None:
        rep.info(f'bn surah {surah}: no Bangla translation source loaded; reference join skipped')

    if surah == 67 and BASELINE_ON and bn_doc.get('provenance', {}).get('generator') == 'prototype-replay' and not missing:
        en_flat = en_doc.get('schema_version') == '2.0'
        if en_flat:
            got = (sum(src.n_words(surah, a) for a in bn_ayahs), sum(len(iter_chunks(bn_doc['ayahs'][str(a)])) for a in bn_ayahs))
            if got != FLAT_BASELINE_67:
                rep.fail(f'bn surah 67 flat prototype overlay mismatch: {got} != {FLAT_BASELINE_67}')
            else:
                rep.ok(f'bn surah 67 flat overlay mirrors {got[0]} words / {got[1]} chunks')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--surah', type=int, action='append', help='only these surahs (repeatable)')
    parser.add_argument('--annotations-dir', default=os.path.join(ROOT, 'annotations'))
    parser.add_argument('--no-baseline', action='store_true', help='skip prototype baseline replay checks')
    args = parser.parse_args()
    global BASELINE_ON
    BASELINE_ON = not args.no_baseline
    annotation_dir = os.path.abspath(args.annotations_dir)
    report = Report()

    lock_path = os.path.join(ROOT, 'sources.lock.yaml')
    if not os.path.exists(lock_path):
        report.fail('sources.lock.yaml missing')
    else:
        bad = []
        families = parse_lock(lock_path)
        for family in families:
            for item in family['files']:
                path = os.path.join(ROOT, item['path'])
                if not os.path.exists(path):
                    bad.append(f'{item["path"]} (missing)')
                elif sha256(path) != item['sha256']:
                    bad.append(f'{item["path"]} (hash mismatch)')
        if bad:
            report.fail(f'source integrity: {len(bad)} pinned file(s) deviate: {bad[:5]}')
        else:
            report.ok(f'source integrity: all {sum(len(f["files"]) for f in families)} pinned files match sha256')

    sources = Sources()
    english_docs = {}
    files = sorted(glob.glob(os.path.join(annotation_dir, 'surah-*.json')))
    if not files:
        report.fail(f'no surah-*.json files found in {annotation_dir}')
    for path in files:
        surah = int(os.path.basename(path)[6:9])
        if args.surah and surah not in args.surah:
            continue
        doc = load_json(path)
        english_docs[surah] = doc
        validate_english_doc(report, surah, doc, sources)

    bn_files = sorted(glob.glob(os.path.join(annotation_dir, 'bn', 'surah-*.json')))
    for path in bn_files:
        surah = int(os.path.basename(path)[6:9])
        if args.surah and surah not in args.surah:
            continue
        validate_bangla_doc(report, surah, load_json(path), english_docs.get(surah), sources)
    if not bn_files:
        report.info('no Bangla overlay files found — English-only annotations')
    report.info('New schema uses flat Arabic chunks; no clause-size target or clause-boundary fence is applied.')
    report.dump()
    sys.exit(1 if report.fails else 0)


if __name__ == '__main__':
    main()
