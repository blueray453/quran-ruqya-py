"""tools/ayahlib.py — shared helpers: source loading, prompt blocks, output validation.

Stdlib only. Used by run_llm.py (prompt building + validation) and collect.py
(range normalisation). Never modifies anything under sources/.
"""
import difflib, glob, json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_ZW = re.compile('[\u200b-\u200f\u202a-\u202e\u2060\ufeff]')
_MAP = str.maketrans({'ٱ': 'ا', 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ى': 'ي', 'ی': 'ي', 'ې': 'ي', 'ئ': 'ي',
                      'ک': 'ك', 'ة': 'ه', 'ہ': 'ه', 'ھ': 'ه', 'ؤ': 'و', 'ء': ''})


def clean_ar(text):
    """Display form of an Arabic word: zero-width/bidi marks removed, whitespace collapsed."""
    return ' '.join(_ZW.sub('', text).split())


def norm_ar(text):
    """Letters only (no vowel/recitation marks, pause signs, tatweel), spelling variants unified."""
    return ''.join(c for c in text.translate(_MAP) if unicodedata.category(c) == 'Lo')


def load_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _t(v):
    return v.get('t') if isinstance(v, dict) else v


class Src:
    """Read-only view of the sources needed to build a prompt."""

    def __init__(self):
        S = os.path.join(ROOT, 'sources')
        self.text = load_json(os.path.join(S, 'text/indopak.json'))
        self.wbw_en = load_json(os.path.join(S, 'wbw/english-wbw-translation.json'))
        self.wbw_bn = load_json(os.path.join(S, 'wbw/bangla-wbw-translation.json'))
        self.tr_en, self.tr_bn = {}, {}
        for p in sorted(glob.glob(os.path.join(S, 'translation', '*.json'))):
            name = os.path.basename(p)
            d = {k: _t(v) for k, v in load_json(p).items()}
            if 'bn-' in name or '-bn-' in name:
                self.tr_bn.update(d)
            else:
                self.tr_en.update(d)
        self.maxkey = {}
        for k in self.text:
            s, a, w = k.split(':')
            self.maxkey[(int(s), int(a))] = max(self.maxkey.get((int(s), int(a)), 0), int(w))

    def n_words(self, s, a):          # real words: last keyed entry is the ayah-end marker
        return self.maxkey[(s, a)] - 1

    def ayahs(self, s):
        return sorted(a for (ss, a) in self.maxkey if ss == s)

    def surahs(self):
        return sorted({s for (s, a) in self.maxkey})

    def align_words(self, s, a):
        """[(token_count, [letter-tokens], display)] per real word, for aligning an Arabic copy."""
        out = []
        for w in range(1, self.n_words(s, a) + 1):
            disp = clean_ar(self.text[f'{s}:{a}:{w}']['text'])
            toks = [norm_ar(t) for t in disp.split() if norm_ar(t)]
            out.append((len(toks), toks, disp))
        return out

    def words(self, s, a):
        out = []
        for w in range(1, self.n_words(s, a) + 1):
            k = f'{s}:{a}:{w}'
            out.append((w, clean_ar(self.text[k]['text']),
                        self.wbw_en.get(k, '[no gloss]'), self.wbw_bn.get(k, '[no gloss]')))
        return out


def ayah_block(src, s, a, bn_wbw=True, prev_context=False):
    """The per-ayah input block (also used to render the few-shot examples)."""
    lines = []
    if prev_context and a > 1 and f'{s}:{a-1}' in src.tr_en:
        lines.append(f'Previous ayah, English reference translation (context only; do not annotate): '
                     f'"{src.tr_en[f"{s}:{a-1}"]}"')
        lines.append('')
    lines.append(f'### Ayah {s}:{a}')
    hdr = 'Words (position, Arabic text, English word gloss' + (', Bangla word gloss):' if bn_wbw else '):')
    lines.append(hdr)
    for w, ar, ge, gb in src.words(s, a):
        lines.append(f'{w} {ar} — {ge}' + (f' — {gb}' if bn_wbw else ''))
    lines.append('')
    lines.append(f'English reference translation: "{src.tr_en[f"{s}:{a}"]}"')
    lines.append(f'Bangla reference translation: "{src.tr_bn[f"{s}:{a}"]}"')
    return '\n'.join(lines)


# ---------------------------------------------------------------- validation
def _has(rng, text):
    return any(any(lo <= ch <= hi for lo, hi in rng) for ch in text)


BENGALI = [('\u0980', '\u09FF')]
ARABIC = [('\u0600', '\u06FF'), ('\u0750', '\u077F'), ('\u08A0', '\u08FF'),
          ('\uFB50', '\uFDFF'), ('\uFE70', '\uFEFF')]


def expand_words(w):
    """[n] -> [n]; [first, last] (inclusive range) -> full list; a full ascending
    contiguous list of 3+ numbers is accepted as is."""
    if not isinstance(w, list) or not w or not all(isinstance(x, int) for x in w):
        raise ValueError(f'bad words {w!r}')
    if len(w) == 1:
        return list(w)
    if len(w) == 2:
        if w[1] < w[0]:
            raise ValueError(f'bad range {w!r}')
        return list(range(w[0], w[1] + 1))
    if w != list(range(w[0], w[0] + len(w))):
        raise ValueError(f'words not contiguous/ascending {w!r}')
    return list(w)


def align_phrase(ar, src_words, start, min_ratio=0.85):
    """Locate a phrase's Arabic copy among the source words, from word `start` (1-based).
    Boundaries come from the copy itself (word count), so the model never does index arithmetic;
    the letters must still match the source (spelling tolerance via min_ratio)."""
    toks = [norm_ar(t) for t in clean_ar(ar).split() if norm_ar(t)]
    if not toks:
        raise ValueError('empty Arabic copy')
    i = start - 1
    if i >= len(src_words):
        raise ValueError('Arabic copy continues past the end of the ayah')
    j, cnt = i, 0
    while j < len(src_words) and cnt < len(toks):
        cnt += src_words[j][0]
        j += 1
    nxt = ' '.join(x[2] for x in src_words[i:i + 3])
    if cnt != len(toks):
        raise ValueError(f"Arabic copy has {len(toks)} word(s) which does not end on a source word boundary "
                         f"(next unconsumed source words: '{nxt}')")
    S = [t for x in src_words[i:j] for t in x[1]]
    sim = [difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() for a, b in zip(S, toks)]
    if min(sim) < 0.75 or sum(sim) / len(sim) < min_ratio:      # token by token, so a shifted copy cannot pass
        raise ValueError(f"Arabic copy '{ar}' does not match the next unconsumed source words "
                         f"'{' '.join(x[2] for x in src_words[i:j])}'")
    return list(range(start, j + 1))


MAX_PHRASE_WORDS = 0   # 0 = no limit (long phrases are allowed when the meaning needs them)


def normalise(clauses, n_words, need_bn=True, max_phrase_words=MAX_PHRASE_WORDS, src_words=None):
    """Validate one ayah's raw clauses (list of list of {words,en,bn}).
    Returns (errors, normalised_clauses) where words are full lists."""
    errs, out, expect = [], [], 1
    if not isinstance(clauses, list) or not clauses:
        return ['no clauses'], []
    for ci, cl in enumerate(clauses):
        if not isinstance(cl, list) or not cl:
            errs.append(f'clause {ci} empty / not a list')
            continue
        ph_out = []
        for pi, ph in enumerate(cl):
            try:
                if isinstance(ph.get('ar'), str) and src_words is not None:
                    w = align_phrase(ph['ar'], src_words, expect)       # preferred: derive positions
                else:
                    w = expand_words(ph.get('words'))                   # legacy: explicit range
            except (ValueError, AttributeError) as e:
                errs.append(f'clause {ci} phrase {pi}: {e}')
                return errs, out          # later phrases would only cascade
            if max_phrase_words and len(w) > max_phrase_words:
                errs.append(f'clause {ci} phrase {pi}: {len(w)} words ({w[0]}-{w[-1]}), maximum is {max_phrase_words}; split it')
            if w[0] != expect:
                errs.append(f'clause {ci} phrase {pi}: starts at word {w[0]}, expected {expect} (gap/overlap)')
            expect = w[-1] + 1
            en, bn = ph.get('en'), ph.get('bn')
            if not isinstance(en, str) or not en.strip():
                errs.append(f'clause {ci} phrase {pi}: empty en')
            elif _has(ARABIC, en) or _has(BENGALI, en):
                errs.append(f'clause {ci} phrase {pi}: en contains Arabic/Bengali script')
            if need_bn:
                if not isinstance(bn, str) or not bn.strip():
                    errs.append(f'clause {ci} phrase {pi}: empty bn')
                elif not _has(BENGALI, bn):
                    errs.append(f'clause {ci} phrase {pi}: bn lacks Bengali script')
                elif _has(ARABIC, bn):
                    errs.append(f'clause {ci} phrase {pi}: bn contains Arabic script')
            ph_out.append({'words': w, 'en': en, 'bn': bn})
        out.append(ph_out)
    if expect != n_words + 1:
        errs.append(f'tiling ends at word {expect - 1}, ayah has {n_words} words')
    return errs, out


def parse_json_object(text):
    t = text.strip()
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', t)
    i, j = t.find('{'), t.rfind('}')
    if i < 0 or j < i:
        raise ValueError('no JSON object in reply')
    return json.loads(t[i:j + 1])
