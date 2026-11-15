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

    def source_trace(self, s, a):
        """Return the exact numbered Arabic source words and per-word glosses for an ayah."""
        return [
            {'position': w, 'arabic': ar, 'en_wbw': ge, 'bn_wbw': gb}
            for w, ar, ge, gb in self.words(s, a)
        ]

    def ayah_references(self, s, a):
        key = f'{s}:{a}'
        return {
            'en_reference': self.tr_en.get(key),
            'bn_reference': self.tr_bn.get(key),
        }


# Bangla address register of a reference translation (singular addressee / imperatives)
RESPECTFUL = re.compile(r'আপনি|আপনার|আপনাকে|বলুন|ফেরান|দেখুন')
PLAIN = re.compile(r'(?<![\u0980-\u09FF])(?:তুমি|তোমার|তোমাকে|বল|ফিরাও|দেখো)(?![\u0980-\u09FF])')


def register_line(bn_reference):
    resp, plain = bool(RESPECTFUL.search(bn_reference)), bool(PLAIN.search(bn_reference))
    if resp and not plain:
        return ('Bangla address register (taken from the reference): RESPECTFUL - use আপনি / আপনার / আপনাকে and '
                'respectful imperatives (“বলুন” for “Say”, never “বল” or “তুমি”).')
    if plain and not resp:
        return ('Bangla address register (taken from the reference): PLAIN - use তুমি / তোমার / তোমাকে and plain '
                'imperatives (“বল” for “Say”), never আপনি.')
    return None


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
    reg = register_line(src.tr_bn[f'{s}:{a}'])
    if reg:
        lines.append(reg)
    return '\n'.join(lines)


# ---------------------------------------------------------------- meaning heuristics
_STOP = set('the and with from that this those these them they their there which what when where whom whose have '
            'been being were will shall would could should your you his her him she its our not for upon into onto '
            'over under than then also only very more most any all some such other another each every thing'.split())


def _ctoks(text):
    return {w[:4] for w in re.findall(r'[a-z]{4,}', text.lower()) if w not in _STOP}


def meaning_flags(gloss, chunks):
    """Heuristic candidates for dropped / moved / doubled meaning in flat chunks.

    gloss: {word position: English word-by-word gloss}; chunks: ordered
    [{words: [...], en: ...}, ...]. These flags are review hints, not hard linguistic rules.
    """
    own = [set().union(*[_ctoks(gloss.get(w, '')) for w in p['words']]) for p in chunks]
    en = [_ctoks(p.get('en', '')) for p in chunks]
    out = []
    for i, p in enumerate(chunks):
        span = f"words {p['words'][0]}-{p['words'][-1]}"
        if own[i] and not en[i]:
            out.append(f'dropped? {span} "{p.get("en", "")}" carries none of the meaning of its words')
        for j in (i - 1, i + 1):
            if 0 <= j < len(chunks) and (en[i] & own[j]) - own[i]:
                out.append(f'moved/doubled? {span} "{p.get("en", "")}" contains meaning of the neighbouring chunk '
                           f'"{chunks[j].get("en", "")}" (words {chunks[j]["words"][0]}-{chunks[j]["words"][-1]})')
    return list(dict.fromkeys(out))


# ---------------------------------------------------------------- validation
def _has(rng, text):
    return any(any(lo <= ch <= hi for lo, hi in rng) for ch in text)


# Typographic marks that models keep emitting (” “ ’ ‘ – — … …, no-break and
# zero-width characters). Stored annotation text must be plain; these are
# normalised at ingest so every downstream artifact (raw, merges, build, qa)
# stays clean. Bangla-specific punctuation (। ঁ etc.) is untouched.
_PLAIN_MAP = {ord(c): r for c, r in (
    ('\u2018', "'"), ('\u2019', "'"), ('\u201a', ','), ('\u201b', "'"),
    ('\u201c', '"'), ('\u201d', '"'), ('\u201e', '"'), ('\u201f', '"'),
    ('\u2032', "'"), ('\u2033', '"'),
    ('\u2012', '-'), ('\u2013', '-'), ('\u2014', '-'), ('\u2015', '-'),
    ('\u2026', '...'),
    ('\u00a0', ' '), ('\u2007', ' '), ('\u202f', ' '),
    ('\u200b', ''), ('\u200c', ''), ('\u200d', ''), ('\ufeff', ''),
)}


def plain_text(s):
    """Replace typographic quotes/dashes/ellipsis and invisible marks with plain ASCII."""
    return s.translate(_PLAIN_MAP) if isinstance(s, str) else s


BENGALI = [('\u0980', '\u09FF')]
ARABIC = [('\u0600', '\u06FF'), ('\u0750', '\u077F'), ('\u08A0', '\u08FF'),
          ('\uFB50', '\uFDFF'), ('\uFE70', '\uFEFF')]

# The project's preferred English/Bangla religious terminology. These are hard output rules,
# not style suggestions, because the user explicitly requires Islamic terms grounded in Arabic.
FORBIDDEN_EN_TERMS = re.compile(r"\b(?:god|gods|lord|lords|lordship|deity|deities)\b", re.I)
FORBIDDEN_BN_TERMS = re.compile(r"ঈশ্বর|প্রভু|খোদা")

# High-confidence syntactic warning patterns only. These produce review hints, never hard QA
# failures; Arabic word-position coverage remains the structural source of truth.
_STANDALONE_DEPENDENTS = {
    'if', 'when', 'and', 'or', 'then', 'of', 'to', 'from', 'for', 'with', 'in', 'on',
    'at', 'by', 'that', 'who', 'which', 'because', 'although', 'unless', 'after', 'before',
}
_TRAILING_DEPENDENTS = {
    'if', 'when', 'of', 'to', 'from', 'for', 'with', 'that', 'because', 'although',
    'unless', 'and', 'or',
}


def terminology_flags(en, bn=None):
    """Return user-preference terminology violations for translation fragments."""
    out = []
    if isinstance(en, str):
        hits = sorted({m.group(0) for m in FORBIDDEN_EN_TERMS.finditer(en)}, key=str.lower)
        if hits:
            out.append('English uses prohibited generic religious term(s): ' + ', '.join(hits)
                       + '; use Allah / Rabb / ilah according to the Arabic source')
    if isinstance(bn, str):
        hits = sorted(set(FORBIDDEN_BN_TERMS.findall(bn)))
        if hits:
            out.append('Bangla uses prohibited religious term(s): ' + ', '.join(hits)
                       + '; use আল্লাহ / রব / ইলাহ according to the Arabic source')
    return out


def syntactic_review_flags(chunks):
    """Conservative hints for potentially broken phrase fragments.

    This intentionally avoids word-by-word gloss overlap: that older heuristic falsely marked
    many context-dependent fragments as dropped meaning. Every item here is a review candidate,
    not a claim of semantic error.
    """
    out = []
    for i, chunk in enumerate(chunks):
        text = re.sub(r"^[\W_]+|[\W_]+$", '', (chunk.get('en') or '').strip().lower())
        tokens = re.findall(r"[a-z]+(?:['’][a-z]+)?", text)
        span = chunk.get('words') or []
        label = f"chunk {i + 1} words {span[0]}-{span[-1]}" if span else f'chunk {i + 1}'
        standalone = len(tokens) == 1 and tokens[0] in _STANDALONE_DEPENDENTS
        if standalone:
            out.append(f'{label}: standalone dependent/function word {tokens[0]!r}; check whether it belongs with the smallest required neighbouring unit')
        elif tokens and tokens[-1] in _TRAILING_DEPENDENTS:
            out.append(f'{label}: fragment ends with dependent word {tokens[-1]!r}; check boundary with next chunk')
        if re.search(r"\b(?:then )?if is\b|\bso that if (?:errs|is)\b", text):
            out.append(f'{label}: likely broken conditional construction; review subject/predicate grouping')
        # Only flag lexical linking verbs whose complement is predictably missing. Generic
        # copular endings such as "Blessed is" can be valid in an Arabic-aligned fragment.
        if re.search(r"\b(?:becomes?|became|seems?|remains?)\s*$", text):
            out.append(f'{label}: fragment ends with a linking verb; check whether its required complement was split off')
    return list(dict.fromkeys(out))



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


MAX_PHRASE_WORDS = 0   # soft review guidance is preferred; do not hard-split valid Arabic units


def normalise(chunks, n_words, need_bn=True, max_phrase_words=MAX_PHRASE_WORDS, src_words=None):
    """Validate one ayah's flat list of {words,en,bn} chunks (legacy {ar,en,bn} accepted).

    New model output supplies 1-based source-word ranges. Returns
    (errors, [{words: [...], en: ..., bn: ...}, ...]). `max_phrase_words` remains as an
    optional strict fence for callers that explicitly request it; the normal pipeline uses 0.
    """
    errs, out, expect = [], [], 1
    if not isinstance(chunks, list) or not chunks:
        return ['no chunks (expected a non-empty flat list)'], []
    for ci, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            errs.append(f'chunk {ci + 1}: expected an object')
            return errs, out
        try:
            if isinstance(chunk.get('words'), list):
                # New contract: model returns source positions, not a copied Arabic string.
                # This avoids orthographic/diacritic transcription errors entirely.
                w = expand_words(chunk['words'])
            elif src_words is not None:
                # Backward compatibility for older raw replies that used `ar` copies.
                if not isinstance(chunk.get('ar'), str) or not chunk['ar'].strip():
                    raise ValueError('missing `words` positions (new contract) or legacy Arabic copy in `ar`')
                w = align_phrase(chunk['ar'], src_words, expect)
                exact_source = ' '.join(src_words[pos - 1][2] for pos in w)
                if clean_ar(chunk['ar']) != exact_source:
                    raise ValueError(f'legacy Arabic copy is not exact for words {w[0]}-{w[-1]}; '
                                     f'copy source spelling and marks exactly: {exact_source!r}')
            else:
                w = expand_words(chunk.get('words'))
            if w[0] < 1 or w[-1] > n_words:
                raise ValueError(f'word range {w[0]}-{w[-1]} is outside ayah bounds 1-{n_words}')
        except (ValueError, AttributeError) as e:
            errs.append(f'chunk {ci + 1}: {e}')
            return errs, out
        if max_phrase_words and len(w) > max_phrase_words:
            errs.append(f'chunk {ci + 1}: {len(w)} words ({w[0]}-{w[-1]}), maximum is {max_phrase_words}; review/split if linguistically valid')
        if w[0] != expect:
            errs.append(f'chunk {ci + 1}: starts at word {w[0]}, expected {expect} (gap/overlap/reordering)')
        expect = w[-1] + 1
        en, bn = plain_text(chunk.get('en')), plain_text(chunk.get('bn'))
        if not isinstance(en, str) or not en.strip():
            errs.append(f'chunk {ci + 1}: empty en')
        elif _has(ARABIC, en) or _has(BENGALI, en):
            errs.append(f'chunk {ci + 1}: en contains Arabic/Bengali script')
        if need_bn:
            if not isinstance(bn, str) or not bn.strip():
                errs.append(f'chunk {ci + 1}: empty bn')
            elif not _has(BENGALI, bn):
                errs.append(f'chunk {ci + 1}: bn lacks Bengali script')
            elif _has(ARABIC, bn):
                errs.append(f'chunk {ci + 1}: bn contains Arabic script')
        for term_issue in terminology_flags(en if isinstance(en, str) else '',
                                            bn if need_bn and isinstance(bn, str) else None):
            errs.append(f'chunk {ci + 1}: {term_issue}')
        out.append({'words': w, 'en': en, 'bn': bn})
    if expect != n_words + 1:
        errs.append(f'tiling ends at word {expect - 1}, ayah has {n_words} words')
    return errs, out


def repair_json_text(t):
    """Conservative repairs for known LLM JSON slips; applied ONLY when a strict parse of the
    first object fails. (1) An unquoted scalar string value after a key — seen live in
    luna_schema_smoke 67:12: `"en": unseen,` -> `"en": "unseen",`; (2) trailing commas before
    } or ]. Numbers, true/false/null and already-quoted values are never touched. If the
    repaired text still fails to parse, the original JSONDecodeError is what the caller sees."""
    not_scalar = re.compile(r'^(true|false|null|[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)$')

    def _quote(m):
        key, sep, val, tail = m.group(1), m.group(2), m.group(3).strip(), m.group(4)
        if not_scalar.match(val) or val.startswith('"'):
            return m.group(0)
        return f'{key}{sep}"{val}"{tail}'

    t = re.sub(r'("[A-Za-z0-9_:-]+")(\s*:\s*)([^"\{\[\]\d\-tfn\s][^"\{\[\]\n]*?)(\s*([,\}\]]))',
               _quote, t)
    return re.sub(r',\s*([}\]])', r'\1', t)


last_parse_used_repair = False


def parse_json_object(text, keys=None):
    """First/last top-level JSON object in a reply. Tolerates fences, text around it and several objects in a
    row ("Extra data"): the last object containing all of `keys` wins. A truncated or broken object still
    raises the original JSONDecodeError (so retry hints can mention it). If the first object fails a strict
    parse, one conservative repair pass (repair_json_text) is attempted first; when it succeeds,
    `last_parse_used_repair` is True afterwards so callers can log the repair."""
    global last_parse_used_repair
    last_parse_used_repair = False
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    dec, objs, i = json.JSONDecoder(), [], 0
    while True:
        i = t.find('{', i)
        if i < 0:
            break
        try:
            obj, end = dec.raw_decode(t, i)
        except json.JSONDecodeError as first_err:
            if objs:
                break
            try:
                obj, end = dec.raw_decode(repair_json_text(t[i:]), 0)
            except json.JSONDecodeError:
                raise first_err from None
            end += i
            last_parse_used_repair = True
        if isinstance(obj, dict):
            objs.append(obj)
        i = end
    if not objs:
        raise ValueError('no JSON object in reply')
    if keys:
        full = [o for o in objs if all(k in o for k in keys)]
        if full:
            return full[-1]
    return max(objs, key=lambda o: len(json.dumps(o)))
