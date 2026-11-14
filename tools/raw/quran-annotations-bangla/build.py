#!/usr/bin/env python3
"""build.py — regenerate data/ views from the read-only sources + annotations.

Deterministic and offline: sources are read, never modified. For every annotated
surah this writes data/surah-NNN.json, joining:

  - word text + positions      (sources/text, real word numbers 1..N)
  - word-by-word English       (sources/wbw; null for the 3 known-missing keys)
  - whole-ayah translation     (sources/translation, per language)
  - clause/phrase structure    (annotations/surah-NNN.json)
  - recitation windows         (optional reciter file; window = first start .. last end)

Bangla overlay: for every annotations/bn/surah-NNN.json this additionally writes
data/bn/surah-NNN.json — a separate overlay keyed by clause/phrase ids. Besides
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
            segs = audio.get(f'{s}:{a}')
            if segs:
                waudio, notes = join_audio(segs['segments'], N)
        total_fallback_notes += [f'{s}:{a}: {x}' for x in notes]

        words = []
        for w in range(1, N + 1):
            k = f'{s}:{a}:{w}'
            aw = waudio.get(w)
            words.append({
                'pos': w,
                'text': indopak[k]['text'],
                'wbw_en': wbw.get(k),
                'audio': {'start_ms': aw[0], 'end_ms': aw[1]} if aw else None,
            })

        clauses = []
        for ci, cl in enumerate(entry['clauses'], 1):
            cid = f'{s}:{a}:{ci}'
            phrases = []
            for pi, ph in enumerate(cl['phrases'], 1):
                pw = ph['words']
                wins = [waudio[w] for w in pw if w in waudio]
                win = {'start_ms': min(x[0] for x in wins), 'end_ms': max(x[1] for x in wins)} if wins else None
                phrases.append({
                    'id': f'{cid}.{pi}',
                    'words': pw,
                    'en': ph['en'],
                    'audio': win,
                })
            wins = [waudio[w] for w in cl['words'] if w in waudio]
            clauses.append({
                'id': cid,
                'words': cl['words'],
                'en': ' '.join(ph['en'] for ph in phrases),
                'audio': {'start_ms': min(x[0] for x in wins), 'end_ms': max(x[1] for x in wins)} if wins else None,
                'phrases': phrases,
            })

        ayahs.append({
            'ayah': a,
            'n_words': N,
            'status': entry['status'],
            'translation_en': tr.get(f'{s}:{a}'),
            'words': words,
            'clauses': clauses,
        })

    n_phrases = sum(len(c['phrases']) for ay in ayahs for c in ay['clauses'])
    n_clauses = sum(len(ay['clauses']) for ay in ayahs)
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
                   'clauses': n_clauses, 'phrases': n_phrases},
        'ayahs': ayahs,
    }
    return view


def build_bn_view(s, bn_doc, tr_bn, wbw_bn):
    """Bangla overlay view: join bn fragments onto the ids of the base view, plus
    the two sourced Bangla joins: tr_bn ({'s:a': text} — whole-ayah reference
    translation, may be absent for a surah) and wbw_bn ({'s:a:w': gloss} — per-word
    glosses, real word numbers 1..N; the ayah-end marker key is never used)."""
    ayahs = {}
    tot_w = tot_p = tot_c = 0
    for a_str in sorted(bn_doc['ayahs'], key=int):
        a = int(a_str)
        entry = bn_doc['ayahs'][a_str]
        clauses_out, all_frags = [], []
        for ci, cl in enumerate(entry['clauses'], 1):
            cid = f'{s}:{a}:{ci}'
            frags, phrases_out = [], []
            for pi, ph in enumerate(cl['phrases'], 1):
                frags.append(ph['bn'])
                phrases_out.append({'id': f'{cid}.{pi}', 'words': ph['words'], 'bn': ph['bn']})
            clauses_out.append({'id': cid, 'words': cl['words'], 'bn': ' '.join(frags),
                                'phrases': phrases_out})
            all_frags += frags
            tot_p += len(phrases_out)
        n = sum(len(c['words']) for c in entry['clauses'])
        ayahs[a_str] = {
            'status': entry['status'],
            'n_words': n,
            'bn_assembled': ' '.join(all_frags),
            'translation_bn': tr_bn.get(f'{s}:{a}'),
            'words': [{'pos': w, 'wbw_bn': wbw_bn.get(f'{s}:{a}:{w}')} for w in range(1, n + 1)],
            'clauses': clauses_out,
        }
        tot_c += len(clauses_out)
        tot_w += n
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
            'note': ('Bangla overlay: ids and word spans refer to the base view; words, '
                     'audio timings and English content are not duplicated here. '
                     'bn_assembled is the ayah\'s fragments joined in Arabic order '
                     '(draft reading, not a sourced translation). translation_bn is the '
                     'sourced whole-ayah Bangla reference translation (null if the '
                     'translation source does not cover the surah yet) and words[].wbw_bn '
                     'are the sourced per-word Bangla glosses, both joined at build time.'),
        },
        'counts': {'ayahs': len(ayahs), 'words': tot_w, 'clauses': tot_c, 'phrases': tot_p},
        'ayahs': ayahs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--surah', type=int, action='append', help='only these surahs (repeatable)')
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

    files = sorted(glob.glob(os.path.join(ROOT, 'annotations', 'surah-*.json')))
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    for path in files:
        s = int(os.path.basename(path)[6:9])
        if args.surah and s not in args.surah:
            continue
        doc = load_json(path)
        view = build_view(s, doc, src, wbw, tr_en, audio_path, audio)
        out = os.path.join(ROOT, 'data', f'surah-{s:03d}.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(view, f, ensure_ascii=False, indent=2)
        c = view['counts']
        print(f'built {os.path.relpath(out, ROOT)}: {c["ayahs"]} ayahs, {c["words"]} words, '
              f'{c["clauses"]} clauses, {c["phrases"]} phrases')
        first = view['ayahs'][0]
        ph = first['clauses'][0]['phrases'][0]
        win = ph['audio']
        print(f'  highlight demo: phrase {ph["id"]} words {ph["words"]} -> '
              f'{win["start_ms"]}-{win["end_ms"]} ms')
        if view['provenance']['reciter_fallback_notes']:
            print(f'  fallback notes: {len(view["provenance"]["reciter_fallback_notes"])}')

    bn_files = sorted(glob.glob(os.path.join(ROOT, 'annotations', 'bn', 'surah-*.json')))
    if bn_files:
        os.makedirs(os.path.join(ROOT, 'data', 'bn'), exist_ok=True)
    for path in bn_files:
        s = int(os.path.basename(path)[6:9])
        if args.surah and s not in args.surah:
            continue
        bn_doc = load_json(path)
        view = build_bn_view(s, bn_doc, tr_bn.get(s, {}), wbw_bn)
        out = os.path.join(ROOT, 'data', 'bn', f'surah-{s:03d}.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(view, f, ensure_ascii=False, indent=2)
        c = view['counts']
        print(f'built {os.path.relpath(out, ROOT)}: {c["ayahs"]} ayahs, {c["words"]} words, '
              f'{c["clauses"]} clauses, {c["phrases"]} phrases (overlay)')
        first = view['ayahs'][next(iter(view['ayahs']))]
        ph = first['clauses'][0]['phrases'][0]
        print(f'  bn demo: phrase {ph["id"]} -> {ph["bn"]!r}')


if __name__ == '__main__':
    main()
