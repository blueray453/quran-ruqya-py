"""Step 1: normalize the word-by-word Quran text.

Reads  data/indopak-nastaleeq-wbw.json  (and cross-checks data/indopak-nastaleeq.json)
Writes results/indopak-nastaleeq-wbw-normalized.json

Normalization keeps only base Arabic letters (U+0621-U+064A, without tatweel) so that
diacritics, pause/waqf marks, small signs and private-use glyphs are ignored, and
unifies letter variants (Indo-Pak kaf/yeh/heh forms, alef and hamza seats).
Entries that normalize to an empty string (verse-end markers and two stray glyphs)
are kept in the file with normalized == "" and are ignored by the analysis.
"""
import argparse, json, os, unicodedata, collections

MAP = {'ک':'ك','ڪ':'ك','ی':'ي','ى':'ي','ې':'ي','ے':'ي','ۍ':'ي','ٮ':'ي',
       'ٱ':'ا','أ':'ا','إ':'ا','آ':'ا','ؤ':'و','ئ':'ي','ہ':'ه','ھ':'ه','ۃ':'ة','ں':'ن'}

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', default='data')
    ap.add_argument('--results-dir', default='results')
    a = ap.parse_args()
    os.makedirs(a.results_dir, exist_ok=True)
    wbw = json.load(open(os.path.join(a.data_dir, 'indopak-nastaleeq-wbw.json'), encoding='utf-8'))
    verse_file = json.load(open(os.path.join(a.data_dir, 'indopak-nastaleeq.json'), encoding='utf-8'))
    entries = sorted(wbw.values(), key=lambda x: (int(x['surah']), int(x['ayah']), int(x['word'])))

    dropped = collections.Counter()
    normed, empty = {}, 0
    for e in entries:
        n = normalize(e['text'], dropped)
        empty += not n
        normed[e['location']] = {'id': e['id'], 'surah': int(e['surah']), 'ayah': int(e['ayah']),
                                 'word': int(e['word']), 'text': e['text'], 'normalized': n}

    # cross-check: wbw words joined with spaces must reproduce the verse file text
    by_verse = collections.defaultdict(list)
    for e in entries:
        by_verse[(int(e['surah']), int(e['ayah']))].append(e['text'])
    assert len(by_verse) == 6236
    mismatches = sum(1 for k, v in verse_file.items()
                     if ' '.join(by_verse[(int(v['surah']), int(v['ayah']))]) != v['text'])
    print(f'entries: {len(entries)}  empty after normalization: {empty}  '
          f'real words: {len(entries) - empty}  verse-text mismatches: {mismatches}')
    print('letters dropped by normalization:', dict(dropped))

    path = os.path.join(a.results_dir, 'indopak-nastaleeq-wbw-normalized.json')
    json.dump(normed, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('wrote', path)

if __name__ == '__main__':
    main()
