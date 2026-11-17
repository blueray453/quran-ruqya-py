"""Step 1: build the normalized word-by-word file.

Reads   data/indopak-nastaleeq-wbw.json   word-by-word text (key = surah:ayah:word)
        data/indopak-nastaleeq.json       verse text (cross-check only)
        data/word-stem.db                 used ONLY to restore two words stored as glyphs
Writes  results/indopak-nastaleeq-wbw-normalized.json

Each entry gets two matching forms:
  normalized  base Arabic letters only (diacritics, pause marks, small signs removed; letter
              variants unified). Used for the main analysis.
  exact       diacritics kept, pause marks removed, letter variants unified, NFC. Used for the
              strict (exact-spelling) sensitivity analysis.

Two entries (18:19:34 and 73:20:8) are real words that the Nastaleeq file stores as a single
private-use glyph. They are restored from word-stem.db (flagged "restored_from"). Verse-end
markers stay in the file with normalized == "" and are ignored by the analysis.
"""
import argparse, json, os, sqlite3, unicodedata, collections

MAP = {'ک':'ك','ڪ':'ك','ی':'ي','ى':'ي','ې':'ي','ے':'ي','ۍ':'ي','ٮ':'ي',
       'ٱ':'ا','أ':'ا','إ':'ا','آ':'ا','ؤ':'و','ئ':'ي','ہ':'ه','ھ':'ه','ۃ':'ة','ں':'ن'}
PAUSE = set('\u0615\u06d6\u06d7\u06d8\u06d9\u06da\u06db')
ZW = ' \u200b\u200c\u200d\u200e\u200f\ufeff\u2002\u2003\u00a0'

def normalize(text, dropped=None):
    out = []
    for ch in text:
        c = MAP.get(ch, ch)
        if '\u0621' <= c <= '\u064a' and c != '\u0640':
            out.append(c)
        elif dropped is not None and unicodedata.category(ch) in ('Lo', 'Lm') \
                and not (0xE000 <= ord(ch) <= 0xF8FF) and ch != '\u0640':
            dropped[ch] += 1
    return ''.join(out)

def exact(text):
    out = []
    for ch in text:
        if ch in PAUSE or ch in ZW or ch == '\u0640' or 0xE000 <= ord(ch) <= 0xF8FF:
            continue
        out.append(MAP.get(ch, ch))
    return unicodedata.normalize('NFC', ''.join(out))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', default='data')
    ap.add_argument('--results-dir', default='results')
    a = ap.parse_args()
    os.makedirs(a.results_dir, exist_ok=True)
    wbw = json.load(open(os.path.join(a.data_dir, 'indopak-nastaleeq-wbw.json'), encoding='utf-8'))
    verse_file = json.load(open(os.path.join(a.data_dir, 'indopak-nastaleeq.json'), encoding='utf-8'))
    db = sqlite3.connect('file:' + os.path.join(a.data_dir, 'word-stem.db') + '?mode=ro', uri=True)
    stem_text = dict(db.execute('select w.word_location, s.text from stem_words w join stems s on s.id = w.stem_id'))
    entries = sorted(wbw.values(), key=lambda x: (int(x['surah']), int(x['ayah']), int(x['word'])))

    dropped = collections.Counter()
    normed, restored = {}, []
    for e in entries:
        loc = e['location']
        n = normalize(e['text'], dropped)
        rec = {'id': e['id'], 'surah': int(e['surah']), 'ayah': int(e['ayah']), 'word': int(e['word']),
               'text': e['text'], 'normalized': n, 'exact': exact(e['text']) if n else ''}
        if not n and loc in stem_text:          # a real word stored as a private-use glyph
            rec['normalized'] = normalize(stem_text[loc])
            rec['exact'] = exact(stem_text[loc])
            rec['restored_from'] = 'word-stem.db'
            restored.append(loc)
        normed[loc] = rec
    assert len(restored) == 2, restored
    empty = sum(1 for r in normed.values() if not r['normalized'])
    by_verse = collections.defaultdict(list)
    for e in entries:
        by_verse[(int(e['surah']), int(e['ayah']))].append(e['text'])
    assert len(by_verse) == 6236 and empty == 6236
    mism = sum(1 for v in verse_file.values()
               if ' '.join(by_verse[(int(v['surah']), int(v['ayah']))]) != v['text'])
    print(f'entries: {len(entries)}  verse-end markers (empty): {empty}  '
          f'real words: {len(entries) - empty}  verse-text mismatches: {mism}')
    print('words restored from word-stem.db:', restored)
    print('letters dropped by normalization:', dict(dropped))
    path = os.path.join(a.results_dir, 'indopak-nastaleeq-wbw-normalized.json')
    json.dump(normed, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('wrote', path)

if __name__ == '__main__':
    main()
