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

Phrases are SMALL, and a clause is almost always made of several of them. Measured on the
reviewed Al-Mulk prototype: on average 1.6 Arabic words per phrase (59% of phrases are a
single word, 29% two, 10% three, 2% four) and 2.5 phrases per clause. Fewer than 1 clause
in 10 consists of a single phrase.

- NEVER write a whole clause as one phrase unless the clause itself is only one or two
  words. A clause of 4-6 words normally has 2-4 phrases.
- Default to 1-2 Arabic words per phrase. Use 3 for a tight unit (a preposition with its
  noun, an iḍāfa pair, a verb with its pronoun and object). Use 4 occasionally. Use 5 or
  more ONLY when the words cannot be split without the English fragments losing their
  meaning; if a split reads naturally, split.
- Split wherever English can stand on its own: subject from predicate, verb from object,
  "and"+verb ("and made") from the noun group that follows, a prepositional phrase from
  the verb before it, an adverb or condition from what it modifies, and every item of a list.
- Think of the phrases as the pieces a learner reads one at a time: each piece is short,
  makes sense alone, and the pieces joined in order read as natural English.

Right granularity (67:19, first clause) — NOT one long phrase:
"Have they not seen" | "the birds" | "above them," | "spreading their wings" | "and folding them in?"

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

(Hand-edited Al-Mulk prototype, ayahs 67:15, 19, 21, 23, 28 and 30. They are not independent
test cases for a pilot on Surah 67; ayahs 67:1-14 are clean tests.)

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

### Example 2 — 67:19

Input:

```
### Ayah 67:19
Words (position, Arabic text, English word gloss, Bangla word gloss):
1 اَوَلَمۡ — Do not — কি নাই
2 يَرَوۡا — they see — তারা দেখে
3 اِلَى — [to] — প্রতি
4 الطَّيۡرِ — the birds — পাখিগুলির
5 فَوۡقَهُمۡ — above them — তাদের উপরে
6 صٰٓفّٰتٍ — spreading (their wings) — পাখা বিস্তার করে
7 وَّيَقۡبِضۡنَؕ ۘ — and folding — ও গুটিয়ে নেয়
8 مَا — Not — না
9 يُمۡسِكُهُنَّ — holds them — তাদের ধরে ধরে (অন্য কেউ)
10 اِلَّا — except — ছাড়া
11 الرَّحۡمٰنُؕ — the Most Gracious — দয়াবান
12 اِنَّهٗ — Indeed, He — তিনি নিশ্চয়
13 بِكُلِّ — (is) of every — সব উপর
14 شَىۡءٍۢ — thing — কিছুর
15 بَصِيۡرٌ — All-Seer — দৃষ্টিবান

English reference translation: "Do they not see the birds above them with wings outspread and [sometimes] folded in? None holds them [aloft] except the Most Merciful. Indeed He is, of all things, Seeing."
Bangla reference translation: "তারা কি লক্ষ্য করে না তাদের উপরে পাখিদের প্রতি, যারা পাখা বিস্তার করে ও সংকুচিত করে? দয়াময় আল্লাহই তাদেরকে স্থির রাখেন। নিশ্চয় তিনি সবকিছুর সম্যক দ্রষ্টা।"
```

Output:

```json
{"67:19":[[{"ar":"اَوَلَمۡ يَرَوۡا","en":"Have they not seen","bn":"তারা কি লক্ষ্য করে না"},{"ar":"اِلَى الطَّيۡرِ","en":"the birds","bn":"পাখিদের প্রতি"},{"ar":"فَوۡقَهُمۡ","en":"above them,","bn":"তাদের উপরে,"},{"ar":"صٰٓفّٰتٍ","en":"spreading their wings","bn":"পাখা বিস্তার করে"},{"ar":"وَّيَقۡبِضۡنَؕ ۘ","en":"and folding them in?","bn":"ও গুটিয়ে নেয়?"}],[{"ar":"مَا يُمۡسِكُهُنَّ","en":"None holds them up","bn":"কেউ তাদেরকে ধরে রাখে না"},{"ar":"اِلَّا الرَّحۡمٰنُؕ","en":"except the Most Merciful.","bn":"রহমান ছাড়া।"}],[{"ar":"اِنَّهٗ","en":"Indeed, He is","bn":"নিশ্চয় তিনি"},{"ar":"بِكُلِّ شَىۡءٍۢ بَصِيۡرٌ","en":"All-Seeing over everything.","bn":"সবকিছুর সম্যক দ্রষ্টা।"}]]}
```

### Example 3 — 67:21

Input:

```
### Ayah 67:21
Words (position, Arabic text, English word gloss, Bangla word gloss):
1 اَمَّنۡ — Who is — কে অথবা আছে
2 هٰذَا — this — এমন
3 الَّذِىۡ — the one — যে
4 يَرۡزُقُكُمۡ — to provide you — তোমাদের রিযক দেবে
5 اِنۡ — if — যদি
6 اَمۡسَكَ — He withheld — তিনি বন্ধ করেন
7 رِزۡقَهٗ ۚ — His provision — তার রিযক
8 بَلۡ — Nay — বরং
9 لَّجُّوۡا — they persist — তারা অবিচল
10 فِىۡ — in — মধ্যে
11 عُتُوٍّ — pride — খোদাদ্রোহিতার
12 وَّنُفُوۡرٍ — and aversion — এবং সত্য পরিহারে

English reference translation: "Or who is it that could provide for you if He withheld His provision? But they have persisted in insolence and aversion."
Bangla reference translation: "এমন কে আছে, যে তোমাদেরকে রিযিক দান করবে, যদি তিনি তাঁর রিযিক বন্ধ করে দেন? বরং তারা অবাধ্যতা ও সত্য বিমুখতায় অবিচল রয়েছে।"
```

Output:

```json
{"67:21":[[{"ar":"اَمَّنۡ هٰذَا الَّذِىۡ","en":"Or who is this one who","bn":"অথবা এমন কে আছে"},{"ar":"يَرۡزُقُكُمۡ","en":"could provide for you","bn":"যে তোমাদেরকে রিযিক দান করবে"}],[{"ar":"اِنۡ","en":"if","bn":"যদি"},{"ar":"اَمۡسَكَ","en":"He withheld","bn":"তিনি বন্ধ করে দেন"},{"ar":"رِزۡقَهٗ ۚ","en":"His provision?","bn":"তাঁর রিযিক?"}],[{"ar":"بَلۡ لَّجُّوۡا","en":"Rather, they persist","bn":"বরং তারা অবিচল"},{"ar":"فِىۡ عُتُوٍّ","en":"in arrogance","bn":"অবাধ্যতায়"},{"ar":"وَّنُفُوۡرٍ","en":"and aversion.","bn":"ও সত্য বিমুখতায়।"}]]}
```

### Example 4 — 67:23

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

### Example 5 — 67:28

Input:

```
### Ayah 67:28
Words (position, Arabic text, English word gloss, Bangla word gloss):
1 قُلۡ — Say — বল
2 اَرَءَيۡتُمۡ — Have you seen — "তোমরা চিন্তা কি করেছ
3 اِنۡ — if — যদি
4 اَهۡلَـكَنِىَ — destroys me — আমাকে ধ্বংস করেন
5 اللّٰهُ — Allah — আল্লাহ
6 وَمَنۡ — and whoever — এবং যারা
7 مَّعِىَ — (is) with me — আমার সাথে
8 اَوۡ — or — অথবা
9 رَحِمَنَا ۙ — has mercy upon us — আমাদের প্রতি দয়া করেন
10 فَمَنۡ — then who — কে কিন্তু
11 يُّجِيۡرُ — (can) protect — আশ্রয় দেবে
12 الۡكٰفِرِيۡنَ — the disbelievers — অস্বীকার কারীদের
13 مِنۡ — from — থেকে
14 عَذَابٍ — a punishment — আযাব
15 اَلِيۡمٍ — painful — অত্যন্ত পীড়াদায়ক"

English reference translation: "Say, [O Muḥammad], "Have you considered: whether Allāh should cause my death and those with me or have mercy upon us, who can protect the disbelievers from a painful punishment?""
Bangla reference translation: "বলুন, ‘তোমরা আমাকে জানাও--- যদি আল্লাহ আমাকে ও আমার সঙ্গীদেরকে ধ্বংস করেন অথবা আমাদের প্রতি দয়া প্রদর্শন করেন, তবে কাফিরদেরকে কে রক্ষা করবে যন্ত্রণাদায়ক শাস্তি হতে?"
```

Output:

```json
{"67:28":[[{"ar":"قُلۡ","en":"Say,","bn":"বলুন,"},{"ar":"اَرَءَيۡتُمۡ","en":"“Have you considered:","bn":"‘তোমরা ভেবে দেখেছ কি:"}],[{"ar":"اِنۡ","en":"if","bn":"যদি"},{"ar":"اَهۡلَـكَنِىَ اللّٰهُ","en":"Allah were to destroy me","bn":"আল্লাহ আমাকে ধ্বংস করেন"},{"ar":"وَمَنۡ مَّعِىَ","en":"and those with me,","bn":"এবং আমার সঙ্গীদেরকে,"}],[{"ar":"اَوۡ","en":"or","bn":"অথবা"},{"ar":"رَحِمَنَا ۙ","en":"have mercy on us,","bn":"আমাদের প্রতি দয়া করেন,"}],[{"ar":"فَمَنۡ","en":"who then","bn":"তাহলে কে"},{"ar":"يُّجِيۡرُ","en":"can protect","bn":"রক্ষা করবে"},{"ar":"الۡكٰفِرِيۡنَ","en":"the disbelievers","bn":"কাফিরদেরকে"},{"ar":"مِنۡ عَذَابٍ اَلِيۡمٍ","en":"from a painful punishment?”","bn":"যন্ত্রণাদায়ক শাস্তি থেকে?’"}]]}
```

### Example 6 — 67:30

Input:

```
### Ayah 67:30
Words (position, Arabic text, English word gloss, Bangla word gloss):
1 قُلۡ — Say — বলো
2 اَرَءَيۡتُمۡ — Have you seen — "তোমরা ভেবে কি দেখেছ
3 اِنۡ — if — যদি
4 اَصۡبَحَ — becomes — হয়ে যায়
5 مَآؤُكُمۡ — your water — তোমাদের পানি
6 غَوۡرًا — sunken — ভূগর্ভস্থ
7 فَمَنۡ — then who — কে তবে
8 يَّاۡتِيۡكُمۡ — could bring you — তোমাদের কাছে আনবে
9 بِمَآءٍ — water — পানি
10 مَّعِيۡنٍ — flowing — প্রবহমান"

English reference translation: "Say, "Have you considered: if your water was to become sunken [into the earth], then who could bring you flowing water?""
Bangla reference translation: "বলুন, ‘তোমরা আমাকে জানাও, যদি পানি ভূগর্ভে তোমাদের নাগালের বাইরে চলে যায়, তখন কে তোমাদেরকে এনে দেবে প্ৰবাহমান পানি?’"
```

Output:

```json
{"67:30":[[{"ar":"قُلۡ","en":"Say,","bn":"বলুন,"},{"ar":"اَرَءَيۡتُمۡ","en":"“Have you considered:","bn":"‘তোমরা ভেবে দেখেছ কি:"}],[{"ar":"اِنۡ","en":"if","bn":"যদি"},{"ar":"اَصۡبَحَ مَآؤُكُمۡ غَوۡرًا","en":"your water were to sink away,","bn":"তোমাদের পানি ভূগর্ভে চলে যায়,"}],[{"ar":"فَمَنۡ","en":"who then","bn":"তাহলে কে"},{"ar":"يَّاۡتِيۡكُمۡ","en":"could bring you","bn":"এনে দেবে তোমাদেরকে"},{"ar":"بِمَآءٍ مَّعِيۡنٍ","en":"flowing water?”","bn":"প্রবাহমান পানি?’"}]]}
```
