# Annotation conventions (v2.2)

## Task

You receive one or more Quran ayahs as numbered Arabic words, each with word-by-word (wbw)
glosses in English and Bangla, plus a reference translation of the whole ayah in each
language. Split each ayah into **clauses** and **phrases** and write, for every phrase,
**one English fragment and one Bangla fragment** that translate the same word span.

## Definitions

- **Phrase** — the smallest run of consecutive Arabic words that forms a natural,
  meaningful English unit. It is not a word-by-word gloss. Keep together what only
  makes sense together: a preposition with its noun, a possessive (iḍāfa) construction,
  a verb with its attached pronoun, a fixed expression.
- **Clause** — a consecutive run of phrases that forms one predication event: a
  statement, a condition, a result, a relative clause, a question, a command, or a
  quoted speech act. Decide by meaning, not by length.
- **Tiling** — phrases cover the clause's words exactly once, in order, with no gaps
  or overlaps; clauses tile the ayah the same way.

## How to decide boundaries

Decide only by meaning and by what reads naturally in English. Do not treat any
particular particle, conjunction or punctuation mark as an automatic boundary. The
English fragments of an ayah, joined with single spaces in Arabic order, must read
as natural English. If a boundary cannot read naturally in English, the words belong
in one phrase.

## Phrase size (important)

Phrases are SMALL. In the reviewed Al-Mulk prototype about 59% of phrases are a single
Arabic word, 29% are two words, 10% are three, and 2% are four.

- Default to 1-2 Arabic words per phrase. Use 3 for a tight unit (a preposition with its
  noun, an iḍāfa pair, a verb with its pronoun and object). Use 4 occasionally. Use 5 or
  more ONLY when the words cannot be split without the English fragments losing their
  meaning; if a split reads naturally, split.
- Split wherever English can stand on its own: subject from predicate, verb from object,
  "and"+verb ("and made") from the noun group that follows, a prepositional phrase from
  the verb before it, and every item of a list.
- Think of the phrases as the pieces a learner reads one at a time: each piece is short,
  makes sense alone, and the pieces joined in order read as natural English.

Example of the right granularity (67:2, words 5-8) — NOT one long phrase:
"to test you" | "as to which of you" | "is best in deed,"

## Faithfulness to the span

- A fragment translates ONLY the Arabic words in its own span. Never pull the meaning
  of a neighbouring phrase into it, and never say the same thing twice (e.g. do not put
  "any flaw" in one phrase and then "any fault" in the next for the same words).
- Every Arabic word must be represented in exactly one fragment.
- A clause is never just an object or modifier that completes the previous clause;
  keep such words inside that clause.

## Order

Phrases always follow Arabic word order; never reorder phrases relative to each
other. Inside ONE phrase you may reorder words when English needs it. The English
fragment of a phrase must be independently meaningful.

## English style

- Capitalise at the start of a sentence only. Put punctuation (, . ; : ? !) at the
  end of the phrase it follows.
- Quotation marks: outer “ ” and inner ‘ ’. If speech opened in an earlier ayah is
  still open, do not re-open it; if speech continues past this ayah, leave it open.
- "Allah" for الله; "the Most Merciful" for الرحمن; capitalise pronouns that refer
  to Allah ("He", "His", "Him").
- Use the word glosses and the reference translation as hints only. Do not copy them
  mechanically.

## Bangla style

- Bangla script only. No Arabic script and no romanisation inside fragments.
- The Bangla fragment translates exactly the same word span as the English fragment of
  the same phrase: the segmentation is decided once, from the Arabic, and both
  languages follow it. Do not move meaning into a neighbouring phrase.
- Fragments follow Arabic word order. Joined with single spaces, an ayah's fragments
  must read as natural Bangla; each fragment must be independently meaningful.
- Put the end-punctuation of the unit on the fragment that closes it; use “।” for a
  sentence-final full stop, keep “,” “?” “!”.
- Address register: copy the register of the Bangla reference translation of that ayah.
  If it addresses the listener with আপনি / আপনার / আপনাকে, use those; if it uses
  তুমি / তোমার / তোমাকে, use those; plural forms likewise follow the reference
  (তোমরা / তোমাদের, আপনারা, …). Decide per ayah from its reference translation and
  never mix registers inside an ayah.
- Respectful honorific pronouns for Allah (তিনি, যিনি, তাঁর, তাঁকে); “আল্লাহ” for الله.
- Use the Bangla word glosses and the Bangla reference translation as hints only;
  render the meaning, do not copy gloss strings mechanically.

## Quotation continuity

When an input shows the previous ayah's English reference translation, it is context
only: use it to see whether speech is already open (then do not re-open the quotation
mark) and never annotate it. Inside a request with several ayahs, earlier ayahs serve
the same purpose for later ones.

## Output contract

Return ONLY one JSON object, no prose, no code fences — one key per requested ayah
("surah:ayah"). The value is a list of clauses; a clause is a list of phrases; a phrase
is an object `{"ar": "...", "en": "...", "bn": "..."}`:

- `ar` — the phrase's Arabic words, **copied exactly from the input words** (same spelling
  and marks, in the same order, separated by single spaces). Do not write word numbers.
- `en` — the English fragment. `bn` — the Bangla fragment.

Read in order, the `ar` copies of all phrases of an ayah reproduce the whole ayah exactly
once: every word appears in exactly one phrase; none is skipped, repeated or reordered;
and no phrase crosses a clause. Positions are derived from your copies afterwards.

## Worked examples

(Hand-edited Al-Mulk prototype. Ayahs 67:9, 67:15 and 67:23 appear here, so they are
not independent test cases for a pilot on Surah 67.)

### Example 1 — 67:15

Input:

```
### Ayah 67:15
Words (position, Arabic text, English word gloss, Bangla word gloss):
1 هُوَ — He — তিনিই
2 الَّذِىۡ — (is) the One Who — যিনি
3 جَعَلَ — made — বানিয়েছেন
4 لَـكُمُ — for you — তোমাদের জন্য
5 الۡاَرۡضَ — the earth — ভূতলকে
6 ذَلُوۡلًا — subservient — অধীন
7 فَامۡشُوۡا — so walk — তোমরা অতঃপর চল
8 فِىۡ — in — উপর
9 مَنَاكِبِهَا — (the) paths thereof — তার বক্ষের
10 وَكُلُوۡا — and eat — এবং তোমরা খাও
11 مِنۡ — of — হতে
12 رِّزۡقِهٖؕ — His provision — তার রিযক
13 وَاِلَيۡهِ — and to Him — এবং তাঁরই দিকে
14 النُّشُوۡرُ — (is) the Resurrection — পুনরুত্থান

English reference translation: "It is He who made the earth tame for you - so walk among its slopes and eat of His provision - and to Him is the resurrection."
Bangla reference translation: "তিনিই তো তোমাদের জন্য যমীনকে সুগম করে দিয়েছেন; অতএব তোমরা এর দিক-দিগন্তে বিচরণ কর এবং তাঁর দেয়া রিযিক থেকে তোমরা আহার কর; আর পুনরুত্থান তো তাঁরই কাছে।"
```

Output:

```json
{"67:15":[[{"ar":"هُوَ الَّذِىۡ","en":"He is the One who","bn":"তিনিই যিনি"}],[{"ar":"جَعَلَ","en":"made","bn":"বানিয়েছেন"},{"ar":"لَـكُمُ الۡاَرۡضَ ذَلُوۡلًا","en":"the earth manageable for you,","bn":"তোমাদের জন্য যমীনকে সুগম,"}],[{"ar":"فَامۡشُوۡا","en":"so walk","bn":"অতএব তোমরা বিচরণ কর"},{"ar":"فِىۡ مَنَاكِبِهَا","en":"through its regions","bn":"এর দিক-দিগন্তে"}],[{"ar":"وَكُلُوۡا","en":"and eat","bn":"এবং তোমরা আহার কর"},{"ar":"مِنۡ رِّزۡقِهٖؕ","en":"from His provision;","bn":"তাঁর দেয়া রিযিক থেকে;"}],[{"ar":"وَاِلَيۡهِ","en":"and to Him","bn":"আর তাঁরই কাছে"},{"ar":"النُّشُوۡرُ","en":"is the resurrection.","bn":"পুনরুত্থান।"}]]}
```

### Example 2 — 67:23

Input:

```
### Ayah 67:23
Words (position, Arabic text, English word gloss, Bangla word gloss):
1 قُلۡ — Say — বল
2 هُوَ — He — "তিনিই
3 الَّذِىۡۤ — (is) the One Who — যিনি
4 اَنۡشَاَكُمۡ — produced you — তোমাদের সৃষ্টি করেছেন
5 وَجَعَلَ — and made — এবং দিয়েছেন
6 لَـكُمُ — for you — তোমাদের জন্য
7 السَّمۡعَ — the hearing — শ্রবণশক্তি
8 وَالۡاَبۡصَارَ — and the vision — ও দৃষ্টিশক্তি
9 وَ الۡاَفۡـــِٕدَةَ ؕ — and the feelings — এবং অন্তঃকরণ
10 قَلِيۡلًا — Little — কমই
11 مَّا — (is) what — যা
12 تَشۡكُرُوۡنَ — you give thanks — তোমরা শোকর কর"

English reference translation: "Say, "It is He who has produced you and made for you hearing and vision and hearts [i.e., intellect]; little are you grateful.""
Bangla reference translation: "বলুন, ‘তিনিই তোমাদেরকে সৃষ্টি করেছেন এবং তোমাদেরকে দিয়েছেন শ্রবণশক্তি, দৃষ্টিশক্তি ও অন্তঃকরণ। তোমরা খুব অল্পই কৃতজ্ঞতা প্রকাশ কর।’"
```

Output:

```json
{"67:23":[[{"ar":"قُلۡ","en":"Say,","bn":"বলুন,"},{"ar":"هُوَ الَّذِىۡۤ","en":"“He is the One who","bn":"‘তিনিই যিনি"},{"ar":"اَنۡشَاَكُمۡ","en":"created you","bn":"তোমাদেরকে সৃষ্টি করেছেন"}],[{"ar":"وَجَعَلَ","en":"and made","bn":"এবং দিয়েছেন"},{"ar":"لَـكُمُ","en":"for you","bn":"তোমাদের জন্য"},{"ar":"السَّمۡعَ","en":"hearing,","bn":"শ্রবণশক্তি,"},{"ar":"وَالۡاَبۡصَارَ","en":"sight,","bn":"দৃষ্টিশক্তি"},{"ar":"وَ الۡاَفۡـــِٕدَةَ ؕ","en":"and hearts;","bn":"ও অন্তঃকরণ;"}],[{"ar":"قَلِيۡلًا مَّا","en":"how little","bn":"খুব অল্পই"},{"ar":"تَشۡكُرُوۡنَ","en":"you give thanks!”","bn":"তোমরা কৃতজ্ঞতা প্রকাশ কর।’"}]]}
```

### Example 3 — 67:9

Input:

```
### Ayah 67:9
Words (position, Arabic text, English word gloss, Bangla word gloss):
1 قَالُوۡا — They will say — তারা বলবে
2 بَلٰى — Yes — "হ্যাঁ
3 قَدۡ — indeed — অবশ্যই
4 جَآءَنَا — came to us — এসেছিল আমাদের (কাছে)
5 نَذِيۡرٌ ۙ — a warner — সতর্ককারী
6 فَكَذَّبۡنَا — but we denied — তবে আমরা মিথ্যারোপ করেছিলাম
7 وَقُلۡنَا — and we said — এবং আমরা বলে ছিলাম
8 مَا — Not — "নাই
9 نَزَّلَ — has sent down — নাযিল করেন
10 اللّٰهُ — Allah — আল্লাহ্‌
11 مِنۡ — any — কোন
12 شَىۡءٍ ۖۚ — thing — কিছু
13 اِنۡ — Not — নও
14 اَنۡتُمۡ — you (are) — তোমরা
15 اِلَّا — but — এছাড়া
16 فِىۡ — in — মধ্যে
17 ضَلٰلٍ — error — গুমরাহীর
18 كَبِيۡرٍ — great — বড়"

English reference translation: "They will say, "Yes, a warner had come to us, but we denied and said, 'Allāh has not sent down anything. You are not but in great error.'""
Bangla reference translation: "তারা বলবে, ‘হ্যাঁ, অবশ্যই আমাদের কাছে সতর্ককারী এসেছিল, তখন আমরা মিথ্যারোপ করেছিলাম এবং বলেছিলাম, ‘আল্লাহ কিছুই নাযিল করেননি, তোমরা তো মহাবিভ্রান্তিতে রয়েছ।’"
```

Output:

```json
{"67:9":[[{"ar":"قَالُوۡا","en":"They will say,","bn":"তারা বলবে,"},{"ar":"بَلٰى","en":"“Yes,","bn":"‘হ্যাঁ,"}],[{"ar":"قَدۡ جَآءَنَا نَذِيۡرٌ ۙ","en":"a warner did come to us,","bn":"অবশ্যই আমাদের কাছে সতর্ককারী এসেছিল,"}],[{"ar":"فَكَذَّبۡنَا","en":"but we denied","bn":"তখন আমরা মিথ্যারোপ করেছিলাম"},{"ar":"وَقُلۡنَا","en":"and said,","bn":"এবং বলেছিলাম,"}],[{"ar":"مَا نَزَّلَ اللّٰهُ","en":"‘Allah has not sent down","bn":"“আল্লাহ নাযিল করেননি"},{"ar":"مِنۡ شَىۡءٍ ۖۚ","en":"anything.","bn":"কিছুই,"}],[{"ar":"اِنۡ اَنۡتُمۡ اِلَّا","en":"You are only","bn":"তোমরা কেবল"},{"ar":"فِىۡ ضَلٰلٍ كَبِيۡرٍ","en":"in great error.’”","bn":"মহাবিভ্রান্তিতে রয়েছ।”’"}]]}
```
