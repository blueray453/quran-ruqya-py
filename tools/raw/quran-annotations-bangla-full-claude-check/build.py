#!/usr/bin/env python3
"""build.py — regenerate data/ views from the read-only sources + annotations.

Deterministic and offline: sources are read, never modified. For every annotated
surah this writes data/surah-NNN.json, joining:

  - word text + positions      (sources/text, real word numbers 1..N)
  - word-by-word English       (sources/wbw; null for the 3 known-missing keys)
  - whole-ayah translation     (sources/translation, per language)
  - flat Arabic chunk structure (annotations/surah-NNN.json)
  - recitation windows         (optional reciter file; window = first start .. last end)

Bangla overlay: for every annotations/bn/surah-NNN.json this additionally writes
data/bn/surah-NNN.json — a separate overlay keyed by flat chunk ids. Besides
bn_assembled (the ayah's fragments joined in Arabic order) each ayah carries the
two sourced Bangla joins: translation_bn (whole-ayah Bangla reference translation
from sources/translation/) and words[].wbw_bn (per-word Bangla glosses from
sources/wbw/). The base view is unchanged; words, audio timings and English
content are not duplicated into the overlay.

Translations are loaded per language: files under sources/translation/ are
classified by filename hint ('bn-' / '-bn-' -> Bangla, 'en-' / '-en-' -> English),
so the English and Bangla families never overwrite each other's ayah keys.

Recitation fallback for the known extra-segment quirk: extras < 100 ms extend the
nearest real word in time; longer extras are mapped onto unmatched words in time
order; anything left is reported and left null. The dataset always stores
milliseconds — any reciter file with the same segment shape can be joined later.
"""
import argparse, glob, json, os, time

ROOT = os.path.dirname(os.path.abspath(__file__))
KNOWN_MISSING_WBW = {('2', '181', '4'), ('8', '6', '5'), ('13', '37', '9')}


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def n_words(indopak_maxkey, s, a):
    return indopak_maxkey[(str(s), str(a))] - 1  # last keyed word = ayah-end marker


def join_audio(segs, n):
    """Map reciter segments [word_no, start_ms, end_ms] onto real words 1..n."""
    audio, extras = {}, []
    for no, a, b in segs:
        if 1 <= no <= n and no not in audio:
            audio[no] = [a, b]
        else:
            extras.append((no, a, b))
    notes = []
    rest = []
    for no, a, b in sorted(extras, key=lambda t: (t[1], t[2])):
        if b - a < 100 and audio:
            w = min(audio, key=lambda k: abs(audio[k][1] - a))
            audio[w][1] = max(audio[w][1], b)
            notes.append(f'extra segment {no} ({a}-{b} ms, {b - a} ms) merged into word {w}')
        else:
            rest.append((no, a, b))
    remaining = [w for w in range(1, n + 1) if w not in audio]
    if remaining and rest:
        if len(rest) >= len(remaining):
            for w, (no, a, b) in zip(remaining, rest):
                audio[w] = [a, b]
                notes.append(f'extra segment {no} ({a}-{b} ms) mapped onto word {w} by time order')
            rest = rest[len(remaining):]
    for no, a, b in rest:
        notes.append(f'extra segment {no} ({a}-{b} ms) left unmapped')
    return {w: (v[0], v[1]) for w, v in audio.items()}, notes


def load_translations():
    """sources/translation/*.json -> {lang: {surah: {'s:a': text}}} — lang detected
    per file from the filename hint, so the English and Bangla families stay
    separate (a single flat dict would let one language overwrite the other's
    ayah keys)."""
    out = {}
    lang_by_hint = [('bn', ('bn-', '-bn-')), ('en', ('en-', '-en-'))]
    for p in sorted(glob.glob(os.path.join(ROOT, 'sources/translation', '*.json'))):
        name = os.path.basename(p)
        lang = next((l for l, hints in lang_by_hint if any(h in name for h in hints)), 'en')
        data = load_json(p)
        for k, v in data.items():
            s = int(k.split(':')[0])
            out.setdefault(lang, {}).setdefault(s, {})[k] = v.get('t') if isinstance(v, dict) else v
    return out


def _entry_chunks(entry):
    """Return flat chunks from schema 2.0 or flatten a legacy clause file."""
    if 'chunks' in entry:
        return entry['chunks']
    return [phrase for clause in entry.get('clauses', []) for phrase in clause.get('phrases', [])]


def build_view(s, doc, src, wbw, translations, audio_path, audio):
    indopak, maxkey = src['indopak'], src['maxkey']
    tr = translations.get(s, {})
    ayahs, total_fallback_notes = [], []
    for a_str in sorted(doc['ayahs'], key=int):
        a = int(a_str)
        entry = doc['ayahs'][a_str]
        N = n_words(maxkey, s, a)
        waudio, notes = ({}, [])
        if audio:
            segments = audio.get(f'{s}:{a}')
            if segments:
                waudio, notes = join_audio(segments['segments'], N)
        total_fallback_notes += [f'{s}:{a}: {note}' for note in notes]

        words = []
        for w in range(1, N + 1):
            key = f'{s}:{a}:{w}'
            audio_word = waudio.get(w)
            words.append({
                'pos': w,
                'text': indopak[key]['text'],
                'wbw_en': wbw.get(key),
                'audio': {'start_ms': audio_word[0], 'end_ms': audio_word[1]} if audio_word else None,
            })

        chunks = []
        for ci, chunk in enumerate(_entry_chunks(entry), 1):
            positions = chunk['words']
            wins = [waudio[w] for w in positions if w in waudio]
            window = {'start_ms': min(x[0] for x in wins), 'end_ms': max(x[1] for x in wins)} if wins else None
            chunks.append({
                'id': f'{s}:{a}:{ci}',
                'words': positions,
                'en': chunk['en'],
                'audio': window,
            })

        ayah_view = {
            'ayah': a,
            'n_words': N,
            'status': entry['status'],
            'translation_en': tr.get(f'{s}:{a}'),
            'words': words,
            'chunks': chunks,
        }
        # Keep old clause output only when the input annotation is legacy schema 1.0.
        if 'clauses' in entry and 'chunks' not in entry:
            legacy_clauses = []
            chunk_cursor = 0
            for ci, clause in enumerate(entry['clauses'], 1):
                phrases = []
                for pi, phrase in enumerate(clause['phrases'], 1):
                    built_chunk = chunks[chunk_cursor]
                    phrases.append({
                        'id': f'{s}:{a}:{ci}.{pi}', 'words': phrase['words'],
                        'en': phrase['en'], 'audio': built_chunk['audio'],
                    })
                    chunk_cursor += 1
                clause_wins = [waudio[w] for w in clause['words'] if w in waudio]
                legacy_clauses.append({
                    'id': f'{s}:{a}:{ci}', 'words': clause['words'],
                    'en': ' '.join(ph['en'] for ph in phrases),
                    'audio': {'start_ms': min(x[0] for x in clause_wins),
                              'end_ms': max(x[1] for x in clause_wins)} if clause_wins else None,
                    'phrases': phrases,
                })
            ayah_view['clauses'] = legacy_clauses
        ayahs.append(ayah_view)

    n_chunks = sum(len(ay['chunks']) for ay in ayahs)
    n_clauses = sum(len(ay.get('clauses', [])) for ay in ayahs)
    view = {
        'surah': s,
        'generated_by': 'build.py',
        'built_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'provenance': {
            'annotations': f'annotations/surah-{s:03d}.json',
            'text': 'sources/text/indopak.json',
            'wbw': 'sources/wbw/english-wbw-translation.json',
            'translation': 'sources/translation/ (per-surah files)',
            'reciter': os.path.relpath(audio_path, ROOT) if audio_path else None,
            'reciter_fallback_notes': total_fallback_notes,
        },
        'counts': {'ayahs': len(ayahs), 'words': sum(ay['n_words'] for ay in ayahs),
                   'chunks': n_chunks, 'phrases': n_chunks, 'legacy_clauses': n_clauses},
        'ayahs': ayahs,
    }
    return view


def build_bn_view(s, bn_doc, tr_bn, wbw_bn):
    """Join a flat Bangla chunk overlay onto source-word data."""
    ayahs = {}
    total_words = total_chunks = 0
    for a_str in sorted(bn_doc['ayahs'], key=int):
        a = int(a_str)
        entry = bn_doc['ayahs'][a_str]
        chunks_out, all_fragments = [], []
        for ci, chunk in enumerate(_entry_chunks(entry), 1):
            all_fragments.append(chunk['bn'])
            chunks_out.append({'id': f'{s}:{a}:{ci}', 'words': chunk['words'], 'bn': chunk['bn']})
        n = sum(len(chunk['words']) for chunk in _entry_chunks(entry))
        ayah_view = {
            'status': entry['status'],
            'n_words': n,
            'bn_assembled': ' '.join(all_fragments),
            'translation_bn': tr_bn.get(f'{s}:{a}'),
            'words': [{'pos': w, 'wbw_bn': wbw_bn.get(f'{s}:{a}:{w}')} for w in range(1, n + 1)],
            'chunks': chunks_out,
        }
        if 'clauses' in entry and 'chunks' not in entry:
            legacy = []
            cursor = 0
            for ci, clause in enumerate(entry['clauses'], 1):
                phrases = []
                clause_fragments = []
                for pi, phrase in enumerate(clause['phrases'], 1):
                    chunk = chunks_out[cursor]
                    phrases.append({'id': f'{s}:{a}:{ci}.{pi}', 'words': phrase['words'], 'bn': phrase['bn']})
                    clause_fragments.append(phrase['bn'])
                    cursor += 1
                legacy.append({'id': f'{s}:{a}:{ci}', 'words': clause['words'],
                               'bn': ' '.join(clause_fragments), 'phrases': phrases})
            ayah_view['clauses'] = legacy
        ayahs[a_str] = ayah_view
        total_words += n
        total_chunks += len(chunks_out)
    return {
        'surah': s,
        'language': 'bn',
        'generated_by': 'build.py',
        'built_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'provenance': {
            'annotations': f'annotations/bn/surah-{s:03d}.json',
            'base_view': f'data/surah-{s:03d}.json',
            'translation_bn': 'sources/translation/quran-bn-dr-abu-bakr-muhammad-zakaria-simple.json',
            'wbw_bn': 'sources/wbw/bangla-wbw-translation.json',
            'note': ('Flat Bangla chunk overlay: ids and word spans refer to the base view. '
                     'bn_assembled joins the fragments in Arabic order; translation_bn and '
                     'words[].wbw_bn are sourced reference data.'),
        },
        'counts': {'ayahs': len(ayahs), 'words': total_words, 'chunks': total_chunks,
                   'phrases': total_chunks},
        'ayahs': ayahs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--surah', type=int, action='append', help='only these surahs (repeatable)')
    ap.add_argument('--annotations-dir', default=os.path.join(ROOT, 'annotations'), help='annotation input directory')
    ap.add_argument('--out-dir', default=os.path.join(ROOT, 'data'), help='generated data output directory')
    ap.add_argument('--reciter', default=os.path.join(ROOT, 'sources/audio/ar.alafasy.json'))
    ap.add_argument('--no-audio', action='store_true')
    args = ap.parse_args()

    indopak = load_json(os.path.join(ROOT, 'sources/text/indopak.json'))
    wbw = load_json(os.path.join(ROOT, 'sources/wbw/english-wbw-translation.json'))
    wbw_bn = load_json(os.path.join(ROOT, 'sources/wbw/bangla-wbw-translation.json'))
    translations = load_translations()  # {lang: {surah: {'s:a': text}}}
    tr_en, tr_bn = translations.get('en', {}), translations.get('bn', {})
    maxkey = {}
    for k in indopak:
        s, a, w = k.split(':')
        w = int(w)
        if maxkey.get((s, a), 0) < w:
            maxkey[(s, a)] = w
    src = {'indopak': indopak, 'maxkey': maxkey}

    audio, audio_path = None, None
    if not args.no_audio and os.path.exists(args.reciter):
        audio = load_json(args.reciter)
        audio_path = args.reciter

    annotation_dir = os.path.abspath(args.annotations_dir)
    data_dir = os.path.abspath(args.out_dir)
    files = sorted(glob.glob(os.path.join(annotation_dir, 'surah-*.json')))
    os.makedirs(data_dir, exist_ok=True)
    for path in files:
        s = int(os.path.basename(path)[6:9])
        if args.surah and s not in args.surah:
            continue
        doc = load_json(path)
        view = build_view(s, doc, src, wbw, tr_en, audio_path, audio)
        out = os.path.join(data_dir, f'surah-{s:03d}.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(view, f, ensure_ascii=False, indent=2)
        c = view['counts']
        print(f'built {os.path.relpath(out, ROOT)}: {c["ayahs"]} ayahs, {c["words"]} words, '
              f'{c["chunks"]} chunks')
        first = view['ayahs'][0]
        chunk = first['chunks'][0]
        win = chunk['audio']
        print(f'  highlight demo: chunk {chunk["id"]} words {chunk["words"]} -> '
              f'{win["start_ms"]}-{win["end_ms"]} ms' if win else
              f'  highlight demo: chunk {chunk["id"]} words {chunk["words"]} (no audio)')
        if view['provenance']['reciter_fallback_notes']:
            print(f'  fallback notes: {len(view["provenance"]["reciter_fallback_notes"])}')

    bn_files = sorted(glob.glob(os.path.join(annotation_dir, 'bn', 'surah-*.json')))
    if bn_files:
        os.makedirs(os.path.join(data_dir, 'bn'), exist_ok=True)
    for path in bn_files:
        s = int(os.path.basename(path)[6:9])
        if args.surah and s not in args.surah:
            continue
        bn_doc = load_json(path)
        view = build_bn_view(s, bn_doc, tr_bn.get(s, {}), wbw_bn)
        out = os.path.join(data_dir, 'bn', f'surah-{s:03d}.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(view, f, ensure_ascii=False, indent=2)
        c = view['counts']
        print(f'built {os.path.relpath(out, ROOT)}: {c["ayahs"]} ayahs, {c["words"]} words, '
              f'{c["chunks"]} chunks (Bangla overlay)')
        first = view['ayahs'][next(iter(view['ayahs']))]
        chunk = first['chunks'][0]
        print(f'  bn demo: chunk {chunk["id"]} -> {chunk["bn"]!r}')


if __name__ == '__main__':
    main()
