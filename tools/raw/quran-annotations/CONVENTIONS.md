# Annotation conventions (v2.0)

## Task

You receive one Quran ayah as numbered Arabic words, each with a word-by-word (wbw)
English gloss, plus one reference translation of the whole ayah. Split the ayah into
**clauses** and **phrases** and write **one English fragment per phrase**.

## Definitions

- **Phrase** — the smallest run of consecutive Arabic words that forms a natural,
  meaningful English unit. It is not a word-by-word gloss. Keep together what only
  makes sense together: a preposition with its noun, a possessive (iḍāfa) construction,
  a verb with its attached pronoun, a fixed expression.
- **Clause** — a consecutive run of phrases that forms one predication event: a
  statement, a condition, a result, a relative clause, a question, a command, or a
  quoted speech act. Decide by meaning, not by length.
- **Tiling** — phrases cover the clause's words exactly once, in order, with no gaps
  or overlaps; clauses tile the ayah the same way. Word numbers are the 1-based
  positions given in the input.

## How to decide boundaries

Decide only by meaning and by what reads naturally in English. Do not treat any
particular particle, conjunction or punctuation mark as an automatic boundary. The
English fragments of an ayah, joined with single spaces in Arabic order, must read
as natural English. If a boundary cannot read naturally in English, the words belong
in one phrase.

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

## Output contract

Return ONLY one JSON object, no prose, no code fences — one key per requested ayah
("surah:ayah"). The value is a list of clauses; a clause is a list of phrases; a
phrase is an object {"words": [...], "en": "..."} where "words" is the contiguous,
ascending list of the phrase's word positions and "en" is the English fragment.

## Worked examples

(Drafts from Al-Mulk; replace with reviewed examples after the pilot.)
### Example 1 — 67:15

Input words (position, Arabic text, word-by-word gloss):

```
1 هُوَ — He
2 الَّذِىۡ — (is) the One Who
3 جَعَلَ — made
4 لَـكُمُ — for you
5 الۡاَرۡضَ — the earth
6 ذَلُوۡلًا — subservient
7 فَامۡشُوۡا — so walk
8 فِىۡ — in
9 مَنَاكِبِهَا — (the) paths thereof
10 وَكُلُوۡا — and eat
11 مِنۡ — of
12 رِّزۡقِهٖ​ؕ — His provision
13 وَاِلَيۡهِ — and to Him
14 النُّشُوۡرُ‏ — (is) the Resurrection
```

Whole-ayah reference translation (Sahih International): "It is He who made the earth tame for you - so walk among its slopes and eat of His provision - and to Him is the resurrection."

Output:

```json
{"67:15":[[{"words":[1,2],"en":"He is the One who"}],[{"words":[3],"en":"made"},{"words":[4,6],"en":"the earth manageable for you,"}],[{"words":[7],"en":"so walk"},{"words":[8,9],"en":"through its regions"}],[{"words":[10],"en":"and eat"},{"words":[11,12],"en":"from His provision;"}],[{"words":[13],"en":"and to Him"},{"words":[14],"en":"is the resurrection."}]]}
```
### Example 2 — 67:23

Input words (position, Arabic text, word-by-word gloss):

```
1 قُلۡ — Say
2 هُوَ — He
3 الَّذِىۡۤ — (is) the One Who
4 اَنۡشَاَكُمۡ — produced you
5 وَجَعَلَ — and made
6 لَـكُمُ — for you
7 السَّمۡعَ — the hearing
8 وَالۡاَبۡصَارَ — and the vision
9 وَ الۡاَفۡـــِٕدَةَ ​ ؕ — and the feelings
10 قَلِيۡلًا — Little
11 مَّا — (is) what
12 تَشۡكُرُوۡنَ‏ — you give thanks
```

Whole-ayah reference translation (Sahih International): "Say, "It is He who has produced you and made for you hearing and vision and hearts [i.e., intellect]; little are you grateful.""

Output:

```json
{"67:23":[[{"words":[1],"en":"Say,"},{"words":[2,3],"en":"“He is the One who"},{"words":[4],"en":"created you"}],[{"words":[5],"en":"and made"},{"words":[6],"en":"for you"},{"words":[7],"en":"hearing,"},{"words":[8],"en":"sight,"},{"words":[9],"en":"and hearts;"}],[{"words":[10,11],"en":"how little"},{"words":[12],"en":"you give thanks!”"}]]}
```
### Example 3 — 67:9

Input words (position, Arabic text, word-by-word gloss):

```
1 قَالُوۡا — They will say
2 بَلٰى — Yes
3 قَدۡ — indeed
4 جَآءَنَا — came to us
5 نَذِيۡرٌ  ۙ — a warner
6 فَكَذَّبۡنَا — but we denied
7 وَقُلۡنَا — and we said
8 مَا — Not
9 نَزَّلَ — has sent down
10 اللّٰهُ — Allah
11 مِنۡ — any
12 شَىۡءٍ ۖۚ — thing
13 اِنۡ — Not
14 اَنۡتُمۡ — you (are)
15 اِلَّا — but
16 فِىۡ — in
17 ضَلٰلٍ — error
18 كَبِيۡرٍ‏ — great
```

Whole-ayah reference translation (Sahih International): "They will say, "Yes, a warner had come to us, but we denied and said, 'Allāh has not sent down anything. You are not but in great error.'""

Output:

```json
{"67:9":[[{"words":[1],"en":"They will say,"},{"words":[2],"en":"“Yes,"}],[{"words":[3,5],"en":"a warner did come to us,"}],[{"words":[6],"en":"but we denied"},{"words":[7],"en":"and said,"}],[{"words":[8,10],"en":"‘Allah has not sent down"},{"words":[11,12],"en":"anything."}],[{"words":[13,15],"en":"You are only"},{"words":[16,18],"en":"in great error.’”"}]]}
```
