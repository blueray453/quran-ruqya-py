# Study and linguist tables: what each one is, how to read it, how to study with it

This guide covers every table in the folders `memorization-order/`, `phrases/`, `sequences/`, `lexicon/`, `syntax/` and `reading/` inside `output/`. The verb and counting tables in `analysis/` are covered in `verb-and-counting-tables-guide.md`.

Every number and example here comes from the tables themselves. All tables are built from the two grammar files and are checked automatically (53 checks) every time the project is rebuilt.

---

## 1. Where things are

| Folder | What it holds |
|---|---|
| `output/memorization-order/` | every "what to learn first" list (vocabulary, roots, verbs, ayahs, surahs, Arabic phrases, grammar patterns) |
| `output/phrases/` | repeated Arabic words and phrases, with exact locations |
| `output/sequences/` | repeated grammar patterns (word types and sentence roles) |
| `output/lexicon/` | dictionary-level tables: root families, written forms, conjugations, pronouns, prefixes, particles, rare words |
| `output/syntax/` | sentence-level tables: cases, verb usage, prepositions, possessive phrases, adjectives, particles, unwritten elements |
| `output/reading/` | one row per surah and one per ayah, showing how hard the vocabulary is |
| `output/analysis/` | verb and counting tables, and the lists of irregularities in the source |

**Opening a table.** Double-click the `.csv` file. If the Arabic looks garbled, use **Data → From Text/CSV** in Excel and choose **UTF-8**. Click the heading row and use **Data → Filter** to sort and filter.

**Two kinds of text columns.** Arabic columns end in `_ar` or are called `text_indopak` (your IndoPak text). Columns ending in `_bw` give the same thing in English letters, so you can type it on a keyboard. `jEl` is ج ع ل.

---

## 2. Memorization-order tables ("learn this first")

### 2.1 How they work

Each list starts with the item that gives you the most new recognition for the least learning effort, then the next best, and so on. A word that is already covered is never counted again. Read each list from the top and stop whenever you like.

The columns you will meet in almost every list:

| Column | Meaning |
|---|---|
| `rank` | the order to learn it in |
| `new_…_covered` | what this step adds that earlier steps didn't |
| `cumulative_…` | the running total so far |
| `cumulative_pct_of_…` | the running total as a share of everything |
| `cumulative_words_to_learn` (or `…_to_read`) | the study effort so far |

### 2.2 Arabic words and phrases (`memorization-order/`)

These lists come from the repeated Arabic words and phrases in section 3. A phrase counts only when its words are consecutive inside one verse.

| File | What is ranked | Rows |
|---|---|---|
| `quran-greedy-order-words-and-phrases.csv` | single words and phrases together (the original list) | 6,001 |
| `quran-greedy-order-phrases-only.csv` | phrases of two or more words | 7,109 |
| `quran-greedy-order-words-only.csv` | single words | 6,095 |
| `quran-greedy-order-phrases-3plus.csv` | phrases of three or more words | 3,939 |
| the same four in `exact-diacritics/` | the same, matching words with their exact vowel marks | 6,751 / 6,661 / 6,895 / 3,627 |

How much of the Quran you can recognise (share of its 77,432 words):

| Learn this much | Words and phrases | Words only | Phrases only | Phrases 3+ |
|---|---|---|---|---|
| first 10 units | 16.07% | 16.07% | 3.41% | 1.98% |
| first 100 units | 38.12% | 38.12% | 12.11% (200 words) | 7.13% (304 words) |
| first 1,000 units | 66.58% | 66.58% | 32.78% (2,019 words) | 22.47% (3,197 words) |
| everything in the list | 88.90% (6,095 words) | 88.90% | 64.65% (14,854 words) | 41.79% (12,930 words) |

**How to read it.** In the words-and-phrases list, 100 units are 100 words, and together they cover 38.12% of the Quran. A phrase list shows `cumulative_words_to_learn` larger than the number of units, because each phrase has several words.

**Use.** To build vocabulary, follow the words list. To learn recurring phrases (for example `وَجٰهَدُوْا فِیْ سَبِیْلِ اللّٰهِ`), follow the phrases list.

### 2.3 Grammar patterns (`memorization-order/`)

These lists rank repeating grammar patterns. A pattern is a row of consecutive words described either by their word types (POS) or by their roles in the sentence (function). Eight lists exist, four per kind:

| Variant | Includes | POS patterns reach | Function patterns reach |
|---|---|---|---|
| `…-labels-and-sequences.csv` | single labels and longer patterns | 286 units, 99.91% | 454 units, 99.71% |
| `…-sequences-only.csv` | patterns of two or more words | 1,870 units, 98.42% | 2,454 units, 97.61% |
| `…-sequences-3plus.csv` (recommended) | patterns of three or more words | 4,902 units, 90.00% | 5,110 units, 87.14% |
| `…-sequences-5plus.csv` | patterns of five or more words | 2,520 units, 34.16% | 2,268 units, 31.89% |

The files are named `quran-greedy-order-pos-…` and `quran-greedy-order-function-…`.

**Which to use.** With only a few hundred possible labels, nearly every short pattern repeats, so the first list is just "the most common word types" (the first 10 POS labels already cover 63.09%). The three-plus lists are the useful ones: for POS, learning 100 patterns (300 words) covers 31.18% of the Quran; for roles, 29.71%.

### 2.4 Vocabulary (`memorization-order/`)

| File | What is ranked | Rows |
|---|---|---|
| `quran-greedy-order-lemmas.csv` | every dictionary word, most frequent first | 4,832 |
| `quran-greedy-order-lemmas-content-words.csv` | the same without particles (nouns, verbs, adjectives, names) | 4,740 |
| `quran-greedy-order-roots.csv` | roots, ordered by occurrences per word you must learn | 1,642 |
| `quran-greedy-order-verbs.csv` | verbs (dictionary word + form), most frequent first | 1,475 |
| `quran-greedy-order-ayahs.csv` | ayahs to read first so as to meet the most new words per word read | 2,361 |
| `quran-greedy-order-surahs.csv` | the same, one surah at a time | 113 |

**Dictionary words** (share of all dictionary-word occurrences):

| First N words | All words | Content words only |
|---|---|---|
| 50 | 47.52% | 23.98% |
| 100 | 57.53% | 30.74% |
| 500 | 80.84% | 50.18% |
| 1,000 | 88.94% | 57.41% |
| 2,000 | 94.95% | 63.03% |

**Roots.** The list is ordered by `occurrences_per_word` (the occurrences divided by the number of different words you need to learn for that root). The first entries are `اله` (2,851 occurrences from 3 words), `كون` (1,390 from 3 words), `ارض` (461 from 1 word), `يوم` (405 from 1 word). The first 100 roots (429 words) cover 52.5% of root occurrences, 300 roots (1,401 words) cover 79.49%, and 500 roots (2,259 words) cover 89.62%. All 1,642 roots need 4,657 words.

**Verbs.** The first 10 verbs cover 29.03% of all verbs (7.26% of the Quran's words), the first 100 cover 64.36% (16.09%), and the first 500 cover 91.00% (22.75%).

**Ayahs.** Here the question is: which ayahs should I read to meet every dictionary word at least once, with as little reading as possible? Each ayah is scored by the number of new dictionary words it adds per word it contains.
* The first ayahs are 78:1, 20:93, 20:4, 1:1 and 1:4.
* The first 100 ayahs (319 words to read) introduce 6.66% of the dictionary words, 500 ayahs (2,136 words) introduce 30.28%, 1,000 ayahs (5,878 words) 54.78% and 2,000 ayahs (20,082 words) 91.62%.
* Meeting every one of the 4,832 dictionary words takes 2,361 ayahs (29,949 words, about 39% of the Quran).

**Surahs.** The same idea at surah level. The first surahs in the list are 95, 105, 111, 91, 108 and 80. The first 10 surahs (380 words) introduce 5.28% of the dictionary words, the first 20 (1,263 words) 12.87%, and the first 50 (8,902 words) 42.05%.

**Use.** Work down the dictionary-word lists to decide what to memorise. Use the ayah list as a reading plan, not as a memorisation order. Use the root list to learn words by family.

---

## 3. Arabic word and phrase tables (`phrases/`)

These tables reproduce the original phrase analysis of the project exactly, from the word layer. A **unit** is one word or several consecutive words inside a single verse that occurs at least twice.

| File | Contents | Rows |
|---|---|---|
| `quran-phrases.csv` | every repeated word and phrase | 31,283 (6,095 words and 25,188 phrases) |
| `quran-phrases-annotation.json` | the exact locations of every occurrence | |
| `quran-coverage-by-surah.csv` | per surah: how much of it consists of repeated words and phrases | 114 |
| `summary.json` | the headline numbers | |
| `exact-diacritics/…` | the same, matching words with their exact vowel marks | 30,450 units |

**Columns of `quran-phrases.csv`.**

| Column | Meaning |
|---|---|
| `id` | `U00001`, `U00002`, ... ordered by frequency, then length |
| `type` | `word` or `phrase` |
| `word_count`, `char_count_with_spaces`, `letter_count` | the size of the unit |
| `total_count` | how many times it occurs |
| `stand_alone_count` | how many of those are not part of a longer repeated unit |
| `phrase_normalized` | the unit in plain letters (the form used for matching) |
| `phrase_nastaleeq` | the unit as it is written in your IndoPak text |
| `verses_total`, `verses_stand_alone` | the verses of all occurrences and of the stand-alone ones, separated by `\|` |

**How to read it.** `مِنْ` occurs 2,763 times, of which 208 are stand-alone. `وَجٰهَدُوْا فِیْ سَبِیْلِ اللّٰهِ` (four words) occurs 3 times (2:218, 8:74, 9:20), once stand-alone.

**Headline numbers.** The longest repeated phrase has 24 words. 88.9% of the Quran's words (68,837) lie inside at least one repeated word or phrase. Counting only phrases of two or more words it is 64.65% (50,057). 2,263 verses are covered entirely, 3,357 verses are at least 90% covered, and 6,058 are at least half covered.

**`quran-coverage-by-surah.csv`** gives, for each surah, the words, the covered words and the percentage, once counting words and phrases and once counting phrases only. A surah with a high phrases-only percentage is built from repeated material and is easier to memorise.

---

## 4. Grammar pattern tables (`sequences/`)

| File | Contents | Rows |
|---|---|---|
| `quran-pos-sequences.csv` | repeated patterns of word types | 22,734 |
| `quran-function-sequences.csv` | repeated patterns of sentence roles | 22,509 |
| `…-annotation.json`, `sequence-analysis-report.json` | the locations behind them and the settings used | |

Read them as described in `plain-language-guide.md`: `total_count` is how often a pattern occurs, `stand_alone_count` how often it occurs outside a longer repeating pattern, and `example_text_nastaleeq` gives an Arabic example. The study lists are in section 2.3.

---

## 5. Lexicon tables (`lexicon/`)

### 5.1 `quran-root-families.csv`: all the words of a root (4,657 rows)

| Column | Meaning |
|---|---|
| `root_bw`, `root_ar`, `root_count` | the root and how often it occurs in all its words |
| `lemma_bw`, `lemma_ar` | one word of the root, in dictionary form |
| `pos`, `verb_form`, `derived_type` | its word type, its verb form if it is a verb, and `ACT_PCPL` / `PASS_PCPL` / `VN` if it is a derived noun |
| `count`, `top_glosses`, `n_surahs` | how often it occurs, its most common short meanings, and in how many surahs |
| `first_word`, `example_text_indopak` | where it first occurs and how it looks |

**How to read it.** Root `اله` (2,851): `ٱللَّه` (proper noun, 2,699 uses, "Allah"), `إِلَٰه` (noun, 147 uses, "god", "gods"), `ٱللَّهُمَّ` (5 uses, "O Allah").

**Use.** Filter `root_ar` to a root to study its whole family together, then compare the glosses.

### 5.2 `quran-surface-forms.csv`: every written form that occurs (22,103 rows)

One row for each dictionary word in each written form with its grammar: `text_indopak`, `pos`, `verb_form`, `aspect`, `voice`, `mood`, `person`, `gender`, `number`, `case`, `state`, `count`, `first_word`. The rows are sorted by how common the dictionary word is.

**Use.** To see which forms of a word actually occur, and which one is most common. Filter `lemma_ar` to a word and sort by `count`.

### 5.3 `quran-verb-paradigms.csv`: which conjugations occur (399 rows)

One row for each combination of form, tense, voice, mood and person-gender-number, such as `3MS` (he) or `1P` (we).

| Column | Meaning |
|---|---|
| `form`, `aspect`, `voice`, `mood` | verb form (I–XII), `PERF` / `IMPF` / `IMPV`, `PASS` if passive, `JUS` / `SUBJ` if marked |
| `person_gender_number` | for example `3MS` third person masculine singular, `1P` first person plural |
| `count`, `distinct_verbs` | how many verbs, and how many different verbs |
| `example_word`, `example_verb`, `example_gloss` | one example |

**How to read it.** Form I, perfect, `1P` ("we"): 592 verbs from 109 different verbs, for example `رَزَقَ` ("We have provided them"). Form I, perfect, `2D` (you two): only 2 verbs.

**Use.** To see which slots of the conjugation table you will really meet. Rare slots, like dual forms, can be learned last.

### 5.4 `quran-noun-features.csv`: nouns, adjectives and names (345 rows)

One row for each combination of word type, case, definiteness, gender, number and derived type.

* **Definiteness** has three values: `definite (Al-)` (the word has the article), `indefinite (marked)` (the notes mark it as indefinite), and `unmarked` (for example names, first terms of a possessive phrase, words with an attached pronoun).
* **`derived_type`** is blank unless the word is a participle or verbal noun.

**How to read it.** Adjectives, accusative, indefinite, masculine, singular: 331 occurrences from 94 different adjectives.

### 5.5 `quran-pronouns.csv` (701 rows) and `quran-pronouns-summary.csv` (300 rows)

Pronouns have no dictionary form in the notes, so they are counted by form. The summary merges the different spellings of the same pronoun.

| Column | Meaning |
|---|---|
| `person`, `gender`, `number` | who the pronoun refers to |
| `attached` | `attached` (written as part of another word) or `independent` |
| `host_pos` | the type of the word it is attached to (V verb, N noun, P preposition) |
| `role` | its role in the sentence: `Subj` subject, `Obj` object, `Poss` possessor, `gen` after a preposition |
| `count`, `top_spellings_uthmani` | how often, and its most common spellings |

**How to read it.** Attached, third person masculine plural, on a verb, as subject (the ending that makes `يَعْلَمُونَ`): 3,796 times, written 15 different ways. Attached, second person masculine plural, on a verb, as subject: 2,395 times. Attached, third person masculine plural, on a noun, as possessor (`هُمْ` as in "their"): 1,279 times.

### 5.6 `quran-affixes.csv`: prefixes and suffixes (28 rows)

Every kind of prefix and suffix with its meaning, count and what it attaches to.

**How to read it.** `Al+` (the definite article): 8,377 times, mostly on nouns (7,483). `w:CONJ+` (the conjunction `وَ`): 8,177 times, most often on verbs (2,698). `bi+` (the preposition `بِ`): 2,544 times.

### 5.7 `quran-function-words.csv`: particles and other small words (92 rows)

One row per dictionary word that is not a noun, verb, adjective or name: prepositions, negations, relatives, demonstratives, time and place words and similar. `with_prefix` and `with_suffix` say how often the word occurs with something attached.

**How to read it.** `مِن` ("from", "of", "any"): 3,226 uses, 213 with a prefix and 564 with an attached pronoun.

### 5.8 `quran-special-groups.csv`: kana, inna and kada and their sisters (20 rows)

The words in the special groups the notes mark, one row per word.

**How to read it.** In the "inna and sisters" group: `إِنّ` 1,682 uses, `أَنّ` 362, `لَعَلّ` 123.

### 5.9 Rare words and names

| File | Rows | Contents |
|---|---|---|
| `quran-hapax-lemmas.csv` | 1,994 | dictionary words that occur only once |
| `quran-hapax-roots.csv` | 395 | roots that occur only once |
| `quran-proper-nouns.csv` | 104 | proper nouns with counts and spread |

**How to read the hapax lists.** `مَغْضُوب` ("those who earned (Your) wrath") occurs once, at 1:7:6. A word can be a once-only word while its root occurs elsewhere: the root `غضب` occurs 24 times in 5 different words.

**Use.** Skip the once-only words when you start; the memorisation lists don't need them early.

---

## 6. Syntax tables (`syntax/`)

The relations in these tables are the Treebank's own. The tables only count them.

### 6.1 `quran-case-by-function.csv`: which role goes with which ending (323 rows)

Case × role in the sentence × type of the word it depends on. `pct_of_case` is the share of all words with that case.

**How to read it.** Nominative as the subject of a verb: 2,160 times (24.12% of all nominatives); as the main word of a nominal sentence: 1,160 times; as a predicate whose head is a pronoun: 877.

### 6.2 `quran-verb-valency.csv`: how each verb is used (1,475 rows)

| Column | Meaning |
|---|---|
| `form`, `lemma_*`, `root_ar`, `occurrences` | the verb |
| `with_object` | occurrences with an object (this includes a quoted statement after "said") |
| `with_two_objects`, `with_cognate_object` | occurrences with two objects, or with a cognate object |
| `with_passive_subject` | occurrences with a passive subject |
| `subject_attached`, `subject_separate_word`, `subject_implicit` | whether the subject is part of the verb word, a separate word, or unwritten |
| `with_preposition`, `with_circumstantial` | occurrences with a preposition, or with a circumstantial phrase |

One occurrence can count in several columns.

**How to read it.** `قَالَ` (1,618): 1,383 with an object, 45 passive, subject attached 536, separate 236, implicit 792. `عَلِمَ` (382): 218 with an object.

### 6.3 `quran-verb-preposition-pairs.csv`: which preposition goes with which verb (1,823 rows)

Verb × preposition, with `count`, the verb's total occurrences and `pct_of_verb_uses`.

**How to read it.** `كَذَّبَ` + `بِ`: 104 of its 176 uses (59.1%). `ءَامَنَ` + `بِ`: 175 of 537 (32.6%). `أَتَى` + `بِ`: 101 of 264 (38.3%). `قَالَ` + `لِ`: 201 of 1,618 (12.4%). `جَعَلَ` + `لِ`: 96 of 340 (28.2%).

**Use.** To learn each verb together with the preposition it usually takes.

### 6.4 `quran-idafa-pairs.csv`: possessive phrases (3,015 rows)

The first word and the possessor of each possessive construction.

**How to read it.** `رَبّ` + `كَ` ("your Lord"): 235 times. `كُلّ` + `شَىْء`: 121 times. A possessor that is a pronoun is written `<PRON 2MS>` and so on (the person, gender and number).

### 6.5 `quran-noun-adjective-pairs.csv`: nouns with their adjectives (1,472 rows)

Each pair with how often the two agree in gender, number and case (the `same_…` and `different_…` columns; only occurrences where both words give the feature are counted).

**How to read it.** `غَفُور` + `رَّحِيم`: 70 times, always the same gender, number and case. `عَذَاب` + `أَلِيم`: 67 times. A pair like `حَيَوٰة` + `دُّنْيَا` (68) agrees in gender and case. The different-number counts show where agreement breaks the usual rule.

### 6.6 `quran-preposition-usage.csv`: each preposition (12 rows)

For each preposition: how often it is a prefix or a separate word, the types of word it governs, the words it governs most often (`top_governed`) and what it is most often linked to (`top_linked_to`).

**How to read it.** `min` ("from"): 3,226 times, all as a separate word. It governs nouns 2,277 times and pronouns 564 times. `bi+`: 2,544 times, all as a prefix.

### 6.7 `quran-particle-mood-government.csv`: particles and the verbs they go with (448 rows)

The Treebank links a particle and a verb in one of two directions, which the `direction` column states: **the verb depends on the particle** (as with negation) or **the particle depends on the verb** (as with the future `سَ`). The table gives the relation, the verb's tense and the verb's mood.

**How to read it.** `لَمْ`: 345 of its links (94.8%) are to an imperfect jussive verb. `لَن`: 103 (85.8%) are to an imperfect subjunctive verb. `أَن`: 425 (49.2%) are to an imperfect subjunctive verb. The future `سَ`: 119 links, all to imperfect verbs. A mood of `none` means no special mood is marked.

### 6.8 Unwritten elements

| File | Rows | Contents |
|---|---|---|
| `quran-implicit-elements.csv` | 11,157 | every unwritten element, with its role, head and position |
| `quran-implicit-elements-summary.csv` | 151 | the same grouped by what the element is |

**How to read the summary.** An unwritten "he" `(هُوَ)` as subject: 3,472 times. An unwritten predicate `(*)`: 1,414. An unwritten "you" `(أَنْتَ)` as subject: 1,391.

### 6.9 Phrases and clauses

| File | Rows | Contents |
|---|---|---|
| `quran-constituents.csv` | 26,463 | every phrase and clause the Treebank marks, with its words |
| `quran-constituents-summary.csv` | 6 | counts per kind |

**Kinds:** prepositional phrase `PP` 12,870; verbal sentence `VS` 10,858; nominal sentence `NS` 1,838; subordinate clause `SC` 564; sentence `S` 183; conditional sentence `CS` 150.

**Use.** Filter `tag` to `CS` to see all 150 conditional sentences, or to `SC` for subordinate clauses.

### 6.10 `quran-sentence-length-distribution.csv` (70 rows)

How many sentences have 1, 2, 3 ... words, and the running percentage. There are 521 one-word sentences, 1,101 two-word and about 1,770 each of three and four words. Half of all sentences have five words or fewer.

---

## 7. Reading tables (`reading/`)

### 7.1 `quran-surah-profile.csv` (114 rows)

| Column | Meaning |
|---|---|
| `surah`, `ayahs`, `words`, `sentences`, `avg_words_per_sentence` | the size |
| `verbs`, `noun_segments`, `particle_segments` | the make-up |
| `distinct_lemmas`, `new_lemmas_first_seen_here`, `cumulative_distinct_lemmas` | how many different words, how many appear here for the first time in Quran order, and the running total |
| `lemmas_found_only_in_this_surah`, `once_only_lemmas_here` | words found nowhere else, and words that occur once in the whole Quran |
| `pct_top100_lemmas` ... `pct_top1000_lemmas` | the share of this surah's dictionary words covered by the 100, 300, 500 or 1,000 most frequent words in the Quran |

**How to read it.** Surah 1 has 29 words in 4 sentences, with 23 different dictionary words. Surah 2 has 6,117 words in 967 sentences, with 1,136 different dictionary words.

**Use.** To choose a surah by vocabulary difficulty: a high `pct_top500_lemmas` means few rare words.

### 7.2 `quran-ayah-vocabulary-load.csv` (6,236 rows)

One row per ayah: `words`, `lemma_segments`, `distinct_lemmas`, `pct_top100_lemmas`, `pct_top500_lemmas`, `pct_top1000_lemmas`, the number of rare words (`rare_segments_5_or_fewer_uses`), the number of once-only words, the new words first seen here, the verbs, and the ayah text.

**Use.** To find easy ayahs. Filtering `pct_top500_lemmas` = 100 and `lemma_segments` ≥ 6 gives 578 ayahs made entirely of the 500 most frequent words. The first is 2:3, `الَّذِیْنَ یُؤْمِنُوْنَ بِالْغَیْبِ…`.

---

## 8. Study recipes

1. **Start reading with easy ayahs.** In the ayah table, filter `pct_top500_lemmas` = 100 and read those first. Raise the difficulty gradually by allowing 90%, then 80%.
2. **Build vocabulary.** Work down `quran-greedy-order-lemmas-content-words.csv`. The first 500 content words cover half of all dictionary-word occurrences. Skip the once-only lists until much later.
3. **Meet every word efficiently.** Use `quran-greedy-order-ayahs.csv` as a reading plan: it shows which ayahs introduce the most new words per word read.
4. **Learn verbs with what they take.** For each verb from `quran-greedy-order-verbs.csv`, look up `quran-verb-valency.csv` (object, subject) and `quran-verb-preposition-pairs.csv` (preposition).
5. **Learn the grammar words.** Read `quran-affixes.csv`, then `quran-function-words.csv`, then `quran-particle-mood-government.csv` to see which mood follows `لَمْ`, `لَن`, `أَن` and the others.
6. **Learn conjugation from what occurs.** `quran-verb-paradigms.csv` shows which slots really occur and how often; `quran-surface-forms.csv` shows the written forms of a given word.
7. **Learn phrases.** Follow `quran-greedy-order-phrases-3plus.csv` for recurring multi-word phrases, then look up their verses in `phrases/quran-phrases.csv`.
8. **Choose passages to memorise.** In `phrases/quran-coverage-by-surah.csv`, surahs with a high phrases-only percentage are built from repeated phrases.
9. **Study sentence structure.** Use `quran-constituents.csv` to pull out all conditional sentences, `quran-implicit-elements-summary.csv` to see how often subjects are left unwritten, and `quran-case-by-function.csv` to see which role goes with which ending.
10. **Study a root.** Pick a root from the root list, filter `quran-root-families.csv` to it, then look at its verbs in `analysis/quran-verb-form-occurrences.csv`.

---

## 9. Cautions

1. **These are the Treebank's relations and labels.** The tables count what the experts annotated. They don't settle disputed readings.
2. **"Object" includes quoted speech.** After `قَالَ` the quoted statement is counted as its object, so `قَالَ` has 1,383 objects in 1,618 uses.
3. **Counts of dictionary words, roots, pronouns and affixes are counts of word parts**, not whole written words.
4. **Pronouns have no dictionary form in the notes**, so they are counted by form.
5. **The vocabulary tables use frequency across the whole Quran.** An ayah or surah with a low "top-500" share is not necessarily hard in meaning, only rich in rarer words.
6. **The study lists rank by coverage, not by meaning or importance.** Decide your own priorities and use the filters.
7. **The glosses are short labels and vary with the context** (for example "the wrongdoers", "(are) the wrongdoers").
8. **A particle-to-verb link can run in either direction** in the notes; the `direction` column says which.
9. **Form I is assumed** for every verb with no other form marked.

## 10. Rebuilding

All tables are regenerated by `./run_all.sh` (about two minutes). Stage 10 re-reads every table and checks it against the grammar files and against the other tables. Individual stages can be run on their own, for example `./run_all.sh 07 08`.
