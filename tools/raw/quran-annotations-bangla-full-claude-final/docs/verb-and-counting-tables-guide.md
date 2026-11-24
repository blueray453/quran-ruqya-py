# Verb and counting tables: how to read them and how to study with them

These are the eleven tables in the folder `output/analysis/` that cover verbs and word counts:

| Group | Tables |
|---|---|
| Verbs | `quran-verb-form-summary.csv`, `quran-verb-form-words.csv`, `quran-root-form-summary.csv`, `quran-verb-form-occurrences.csv`, `quran-derived-form-summary.csv`, `quran-derived-forms-words.csv` |
| Counting | `quran-frequency-lemmas.csv`, `quran-frequency-roots.csv`, `quran-frequency-pos.csv`, `quran-frequency-particles.csv`, `quran-frequency-functions.csv` |

All numbers and examples in this guide are taken from the tables themselves.

---

## 1. Which table answers which question

| Question | Table |
|---|---|
| How common is each verb form (I to XII)? | `quran-verb-form-summary.csv` |
| Which verbs belong to a given form, and how often does each occur? | `quran-verb-form-words.csv` |
| Which forms does a given root use? Which roots use many forms? | `quran-root-form-summary.csv` |
| Where is every single verb, and in what tense, person, gender and number? | `quran-verb-form-occurrences.csv` |
| How many participles and verbal nouns are there? | `quran-derived-form-summary.csv` |
| Which participles and verbal nouns occur? | `quran-derived-forms-words.csv` |
| Which dictionary words are most frequent? | `quran-frequency-lemmas.csv` |
| Which roots are most frequent? | `quran-frequency-roots.csv` |
| Which word types (noun, verb, preposition...) are most frequent? | `quran-frequency-pos.csv` |
| Which particles are most frequent? | `quran-frequency-particles.csv` |
| Which sentence roles are most frequent? | `quran-frequency-functions.csv` |

---

## 2. Before you start

**Opening a table.** Double-click the `.csv` file. If the Arabic looks garbled, use **Data → From Text/CSV** in Excel and choose **UTF-8**. In Google Sheets use **File → Import**.

**Sorting and filtering.** Select the heading row, then use **Data → Filter**. Click the arrow on a column to sort it or to show only some values. The frequency tables are already sorted from most to least frequent.

**Two kinds of text columns.** Arabic columns end in `_ar` or are named `text_indopak`. The same item is often given again in English letters (columns ending in `_bw`, such as `root_bw` = `jEl`). The English-letter version is only a way to type the root on a keyboard. In a spreadsheet you can filter on the Arabic column instead.

**Three things that apply to every table:**

1. **Form I is assumed, not written.** The experts' notes never state "Form I". Any verb with no other form marked is counted as Form I. Every other form is written in the notes. The `basis` column says which is which.
2. **Counts are of word parts, not always whole words.** A written word such as `لَكُمُ` is a preposition plus a pronoun, so it adds one to each of those. This matters for the lemma, root, word-type and particle tables. The verb tables count verbs (one per verb), and the sentence-role table counts whole written words.
3. **The source is one team's analysis.** The tables repeat what the notes say. They do not settle disputed readings.

---

## 3. The verb tables

### 3.1 `quran-verb-form-summary.csv`: how common is each form?

12 rows, one per form.

| Column | Meaning |
|---|---|
| `form` | verb form, I to XII |
| `description` | English name of the form (the notes' own descriptions were corrected, see section 7) |
| `pattern` | the pattern in letters, with `f ʕ l` standing for the three root letters |
| `explicit` | verbs where the notes state the form |
| `inferred` | verbs assumed to be Form I |
| `total` | `explicit` + `inferred` |
| `distinct_roots` | how many different roots occur in this form |
| `distinct_lemmas` | how many different verbs (dictionary words) occur in this form |

**How to read it.** Row `IV`: 3,487 verbs, all explicit, from 261 roots. Row `I`: 12,347 verbs, all inferred, from 675 roots.

Share of the 19,356 verbs in the Quran:

| Form | Verbs | Share |
|---|---|---|
| I | 12,347 | 63.8% |
| IV | 3,487 | 18.0% |
| II | 1,300 | 6.7% |
| VIII | 963 | 5.0% |
| V | 414 | 2.1% |
| X | 369 | 1.9% |
| III | 334 | 1.7% |
| VI | 77 | 0.4% |
| VII | 51 | 0.3% |
| XII | 9 | 0.05% |
| IX | 5 | 0.03% |
| XI | 0 | 0% |

**Watch for.**
* Form XI has no verbs in the Quran. Form XII has 9 (all `ٱطْمَأَنَّ`, one root). Form IX has 5 (`ٱبْيَضَّتْ`, `ٱسْوَدَّتْ`).
* The pattern shown for Form III is `/faʕala/`, the same as Form I. The notes leave out the long vowel. The real pattern is `فَاعَلَ`.

### 3.2 `quran-verb-form-words.csv`: which verbs are in each form?

1,475 rows. Each row is one verb (a dictionary word) under its form. The rows are sorted by form, then from most to least frequent.

| Column | Meaning |
|---|---|
| `form` | the verb form |
| `lemma_bw`, `lemma_ar` | the verb in its dictionary form, in English letters and in Arabic |
| `root_bw`, `root_ar` | its root |
| `occurrences` | how often it occurs in the Quran, in all its tenses and persons |
| `explicit`, `inferred` | how many of those occurrences have the form written or assumed |
| `top_glosses` | its three most common short meanings with counts |
| `n_surahs` | in how many surahs it occurs |
| `first_word` | location of the first occurrence (`chapter:verse:word`) |
| `example_text_indopak` | that occurrence as it is written in the IndoPak text |

**How to read it.** Form I, `قَالَ` (root قول): 1,618 occurrences. That is every use of "said" and its other tenses and persons, added together.

**Most frequent verbs in some forms:**

| Form | Most frequent verbs (occurrences) |
|---|---|
| I | `قَالَ` 1,618, `كَانَ` 1,358, `عَلِمَ` 382, `جَعَلَ` 340, `كَفَرَ` 289 |
| II | `كَذَّبَ` 176, `نَزَّلَ` 62, `نَبَّأَ` 46, `سَبَّحَ` 42, `عَذَّبَ` 41 |
| III | `قَٰتَلَ` 54, `نَادَىٰ` 44, `جَٰهَدَ` 27, `جَٰدَلُ` 25, `هَاجَرَ` 16 |
| IV | `ءَامَنَ` 537, `آتَى` 271, `أَنزَلَ` 183, `أَرَادَ` 139, `أَرْسَلَ` 130 |
| V | `تَوَلَّىٰ` 78, `تَذَكَّرَ` 51, `تَوَكَّلْ` 40, `تَوَفَّىٰ` 24, `تَبَيَّنَ` 18 |
| VIII | `ٱتَّقَىٰ` 166, `ٱتَّبَعَ` 136, `ٱتَّخَذَ` 124, `ٱفْتَرَىٰ` 50, `ٱهْتَدَىٰ` 40 |
| X | `ٱسْتَطَاعَ` 42, `ٱسْتَغْفَرَ` 40, `ٱسْتَكْبَرَ` 40, `ٱسْتَجَابَ` 28, `ٱسْتُهْزِئَ` 21 |

**Watch for.** Each verb appears under only one form, so the table has no duplicates. 540 of the 1,475 verbs occur exactly once.

### 3.3 `quran-root-form-summary.csv`: which forms does each root use?

943 rows, one per root that has verbs. It is sorted so that the roots with the most forms come first.

| Column | Meaning |
|---|---|
| `root_bw`, `root_ar` | the root |
| `n_forms` | how many different forms the root occurs in |
| `forms` | those forms, separated by `\|` |
| `total_verbs` | the root's verbs in all forms |
| `form_I` ... `form_XII` | verbs of the root in each form. **A blank cell means zero.** |

**How to read it.** Root `نزل`: `n_forms` 4, forms I, II, IV, V, 258 verbs. Form I 6, Form II 62, Form IV 183, Form V 7.

How many forms roots use: 594 roots use one form, 218 use two, 91 use three, 31 use four, 7 use five, 1 uses six and 1 uses seven. The root with seven forms is `خلف` (I, II, III, IV, V, VIII, X).

### 3.4 `quran-verb-form-occurrences.csv`: every verb in the Quran

19,356 rows, one per verb occurrence, in the order of the Quran.

| Column | Meaning |
|---|---|
| `word`, `wbw_id`, `text_indopak` | the location (`chapter:verse:word`), the ID of the word in your IndoPak file, and the word itself |
| `sentence_id` | the sentence the word belongs to |
| `form`, `basis` | the verb form, and `explicit` (written in the notes) or `inferred` (assumed Form I) |
| `lemma_*`, `root_*` | dictionary form and root, in English letters and Arabic |
| `aspect` | the tense, see the code table below |
| `voice` | `PASS` for passive; blank for active |
| `mood` | `JUS` jussive, `SUBJ` subjunctive; blank when the notes mark no special mood |
| `person`, `gender`, `number` | who is doing it, see the code table below |
| `gloss` | a short English label from the notes |

**What the codes mean:**

| Column | Value | Meaning | Count in the Quran |
|---|---|---|---|
| `aspect` | `PERF` | perfect (past) | 9,150 |
| | `IMPF` | imperfect (present or future) | 8,330 |
| | `IMPV` | imperative (command) | 1,876 |
| `voice` | `PASS` | passive | 1,140 |
| `mood` | `JUS` | jussive | 1,418 |
| | `SUBJ` | subjunctive | 1,330 |
| `person` | `1` / `2` / `3` | I or we / you / he, she, it or they | 2,433 / 4,614 / 12,309 |
| `gender` | `M` / `F` | masculine / feminine | 15,633 / 1,236 (2,487 blank) |
| `number` | `S` / `D` / `P` | singular / dual / plural | 10,036 / 157 / 9,163 |

A blank gender is normal, mostly for first person, where the notes give none.

**How to read a row.** `2:31:1`, `وَعَلَّمَ`, form II, explicit, `PERF`, `3`, `M`, `S`, gloss "And He taught": a past-tense verb, he, masculine, singular.

**Watch for.** The gloss is copied from the notes and sometimes carries punctuation or brackets, for example "it descended." or "[you] know."

### 3.5 `quran-derived-form-summary.csv`: participles and verbal nouns

3 rows: active participles, passive participles and verbal nouns. These are nouns or adjectives built from verbs. They are never counted as verbs and never appear in the other verb tables.

| Column | Meaning |
|---|---|
| `type` | `ACT_PCPL` active participle, `PASS_PCPL` passive participle, `VN` verbal noun |
| `total` | number of occurrences |
| `pos_N`, `pos_ADJ`, `pos_PN`, `pos_LOC` | how many of them are nouns, adjectives, proper nouns and place words. A blank cell means zero. |
| `distinct_roots`, `distinct_lemmas` | how many different roots and words |

**How to read it.** Active participles: 2,974 occurrences (2,708 nouns, 248 adjectives), 417 roots, 597 different words.

**Watch for.** This table has counts only. The words themselves are in the next table.

### 3.6 `quran-derived-forms-words.csv`: the participles and verbal nouns themselves

1,000 rows, one per word, grouped by type (the most frequent type first) and, within a type, from most to least frequent.

| Column | Meaning |
|---|---|
| `type` | `ACT_PCPL` active participle, `PASS_PCPL` passive participle, `VN` verbal noun |
| `lemma_bw`, `lemma_ar` | the word in its dictionary form |
| `pos` | its most common word type (noun or adjective, proper noun) |
| `root_bw`, `root_ar` | its root |
| `count` | how often it occurs |
| `top_glosses` | its three most common short meanings with counts |
| `n_surahs`, `first_word`, `example_text_indopak` | in how many surahs it occurs, where it first occurs, and how it looks |

**How to read it.** Active participle `ظَالِم` (root ظلم): 129 occurrences, 44 surahs, "the wrongdoers" (62 times).

**Use.** To learn participles and verbal nouns by frequency, and to pair each one with its verb through the root.

---

## 4. The counting tables

### 4.1 `quran-frequency-lemmas.csv`: most frequent dictionary words

4,832 rows, one per dictionary word, sorted from most to least frequent. Each count is the total of all the ways that word is written (all tenses, endings and attached pieces).

| Column | Meaning |
|---|---|
| `lemma_bw`, `lemma_ar` | the dictionary word in English letters and in Arabic |
| `count` | how often it occurs |
| `pos`, `pos_en` | its most common word type, as a code and in English |
| `root_bw`, `root_ar` | its root (blank if it has none) |
| `top_glosses` | its three most common short meanings with counts |
| `n_surahs` | in how many surahs it occurs |
| `first_word`, `example_text_indopak` | where it first occurs and how it looks |

**How to read it.** `مِن` ("from"): 3,226. `ٱللَّه`: 2,699. `مَا`: 2,565.

**Watch for.**
* The very top of the list is particles and pronouns such as `مِن`, `مَا`, `لَا`, `فِى`, `إِنّ`, so the most frequent content words start lower down.
* To leave out particles, filter the `pos` column to `N`, `V`, `ADJ` and `PN`.
* The meanings in `top_glosses` are short labels and vary with the context (for example "the wrongdoers" and "(are) the wrongdoers").

### 4.2 `quran-frequency-roots.csv`: most frequent roots

1,642 rows, one per root, sorted from most to least frequent. The count covers every word built on that root: verbs, nouns, adjectives and so on.

| Column | Meaning |
|---|---|
| `root_bw`, `root_ar` | the root |
| `count` | how often any word of the root occurs |
| `n_lemmas`, `top_lemma_ar` | how many different words it has, and the most frequent one |
| `pos_mix` | the word types of its occurrences, such as `V 1620 \| N 102` |
| `top_glosses` | the three most common short meanings with counts |
| `n_surahs`, `first_word`, `example_text_indopak` | spread and first occurrence |

**How to read it.** `اله`: 2,851. `قول`: 1,722 (6 different words; 1,620 verbs and 102 nouns; "Say", "He said", "They said"). `كون`: 1,390. `ربب`: 980. `امن`: 879. `علم`: 854.

For all the words of a root, see `lexicon/quran-root-families.csv` (in the other guide).

### 4.3 `quran-frequency-pos.csv`: word types

45 rows: `pos` (the type code), `pos_en` (its English name), `segments` (how many word parts have that type).

**How to read it.** `N` Noun: 25,136. `PRON` Personal pronoun: 24,685. `V` Verb: 19,356. `P` Preposition: 13,005. `CONJ` Coordinating conjunction: 9,399. `DET` Determiner: 8,377. `PN` Proper noun: 3,911.

Pronouns are high because 87% of them (21,384 of 24,685) are attached to another word (for example the `كُمُ` in `لَكُمُ`), and each attached pronoun is counted separately.

### 4.4 `quran-frequency-particles.csv`: particles

36 rows with the same columns as the word-type table. It lists only the particle types: everything except nouns, proper nouns, verbs, adjectives, pronouns, demonstratives, relative pronouns, and time and place words.

**How to read it.** Preposition 13,005, coordinating conjunction 9,399, determiner 8,377, resumption particle 2,953, negative particle 2,688, accusative particle 2,283.

### 4.5 `quran-frequency-functions.csv`: sentence roles

677 rows: `function_without_NonRel` (the role or roles of a written word) and `words` (how many written words have it). The counts add up to all 77,432 words.

**How to read it.** A role with a `+` means the written word has two parts with different roles. `link+gen` is a preposition together with the word it governs, as in `لَكُمُ`.

| Label | Arabic term | Plain meaning | Words |
|---|---|---|---|
| `root` | root | the main word of the sentence structure | 9,042 |
| `link+gen` | متعلق + مجرور | a preposition written together with the word it governs, such as `لَكُمُ` (preposition + pronoun) or `بِسْمِ` | 6,846 |
| `link` | متعلق | a preposition or similar word connected to a verb or other word | 6,002 |
| `Obj` | مفعول به | object | 5,487 |
| `gen` | مجرور | genitive noun, usually after a preposition | 3,906 |
| `Poss` | مضاف إليه | possessor: the second word of a possessive phrase | 3,528 |
| `conj` | معطوف | a word joined to another with "and" | 3,342 |
| `Adj` | صفة | adjective | 2,711 |
| `Pred` | خبر | predicate | 2,390 |
| `Subj` | فاعل | subject | 2,065 |
| `sub` | صلة | the clause attached to a relative word | 1,477 |
| `sub+Subj` | صلة + فاعل | a verb with its subject pronoun attached, inside a clause that belongs to a relative word | 1,441 |
| `root+Subj` | root + فاعل | a verb with its subject pronoun attached that is the main word of the sentence (often after `وَ` or `فَ`) | 1,259 |
| `gen+Poss` | مجرور + مضاف إليه | a genitive noun together with the attached pronoun that possesses it (like "in his house") | 1,236 |

The labels are the Quranic Treebank's own. The Arabic terms are the names given in its label list. The top 10 roles cover 58.5% of all words, and the top 20 cover 72.6%.

**Watch for.** The labels `NonRel` (a marker carried by prefixes such as the definite article) have been removed from this table so that they don't hide the real role.

---

## 5. Using the tables to study

### 5.1 Build your vocabulary in order of frequency

Use `quran-frequency-lemmas.csv` and `quran-frequency-roots.csv`.

The share of all dictionary-word occurrences (74,608 in total) covered by the top words:

| Top N words | All words (including particles) | Content words only (nouns, verbs, adjectives, names) |
|---|---|---|
| 50 | 47.5% | 24.0% |
| 100 | 57.5% | 30.7% |
| 200 | 67.6% | 38.9% |
| 500 | 80.8% | 50.2% |
| 1,000 | 88.9% | 57.4% |
| 2,000 | 95.0% | |

The share of all root occurrences (49,968 in total) covered by the top roots:

| Top N roots | Share |
|---|---|
| 50 | 45.7% |
| 100 | 60.5% |
| 200 | 75.8% |
| 300 | 83.5% |
| 500 | 91.7% |

**A way to use this.**
1. Learn the particles and pronouns first. They are few and cover a large share (the particle and word-type tables list them).
2. Then work down the lemma list from the top, skipping what you already know, and mark each word as known.
3. Alongside it, learn roots from the root list. Learning 300 roots covers 83.5% of root occurrences.
4. Don't spend effort early on the long tail. 1,994 dictionary words and 395 roots occur only once in the whole Quran.

### 5.2 Learn the verbs that matter most

Use `quran-verb-form-words.csv` (sorted by form, then by frequency) and `quran-verb-form-summary.csv`.

The share of all 19,356 verbs covered by the most frequent verbs (1,475 different verbs in all):

| Top N verbs | Share of all verbs |
|---|---|
| 10 | 29.0% |
| 25 | 41.5% |
| 50 | 51.8% |
| 100 | 64.4% |
| 200 | 77.1% |
| 500 | 91.0% |

**A way to use this.**
1. Start with Form I, which holds 63.8% of all verbs. In the verb-words table, filter `form` = `I` and learn from the top: `قَالَ`, `كَانَ`, `عَلِمَ`, `جَعَلَ`, `كَفَرَ`.
2. Move to Form IV (18.0%), then Form II (6.7%) and Form VIII (5.0%). Forms I, IV, II and VIII together cover 93.5% of all verbs.
3. Learn the rare forms (VI, VII, IX, XII) last. Their few verbs can be memorised as a short list.
4. Keep a count of what you know: 100 verbs gives you 64% of all verb occurrences.

### 5.3 See how the form changes the meaning of a root

Use `quran-root-form-summary.csv` to choose a root, then `quran-verb-form-occurrences.csv` to see its verbs.

Two real examples from the tables:

| Root | Form | Example | Gloss | Count |
|---|---|---|---|---|
| `علم` | I | `یَعْلَمُوْنَ` | they know | 382 |
| | II | `وَعَلَّمَ` | and He taught | 41 |
| | V | `فَیَتَعَلَّمُوْنَ` | but they learn | 2 |
| `نزل` | I | `نَزَلَ` | it descended | 6 |
| | II | `نَزَّلْنَا` | We have revealed | 62 |
| | IV | `اُنْزِلَ` | was sent down | 183 |
| | V | `نَتَنَزَّلُ` | we descend | 7 |

**A way to use this.**
1. In the root summary, sort by `n_forms` (largest first) and pick a root that has three or more forms.
2. In the occurrences table, filter `root_ar` to that root and sort by `form`.
3. Read the `gloss` column for each form and notice what the pattern adds: the second form of `علم` is "teach", the fifth is "learn".
4. Do this for the roots that use the most forms: `خلف` (7 forms), `لقي` (6), `طوع`, `نجو`, `كبر`, `اذن`, `عجل`, `قسم`, `غشو` (5 each).

### 5.4 Practise recognising tense, person and number

Use `quran-verb-form-occurrences.csv`.

* To practise one form, filter `form` = `IV` and `basis` = `explicit`.
* To practise one conjugation, filter `aspect` = `IMPF`, `person` = `2`, `number` = `P`.
* To practise passives, filter `voice` = `PASS` (1,140 verbs).
* To practise commands, filter `aspect` = `IMPV` (1,876 verbs).
* For flashcards, keep only `text_indopak` and `gloss`, hide the gloss column, read the Arabic, say the meaning and form, then reveal the gloss and the `form`, `aspect`, `person`, `gender` and `number` columns to check.

### 5.5 Learn the common sentence roles

Use `quran-frequency-functions.csv`.

1. Learn the ten roles in the table in section 4.5 first. They cover 58.5% of the words.
2. For each one, look at a real example: `python3 queries/q10_sentence_elements.py <sentence number>` or `python3 queries/q11_dependency_tree.py <sentence number>` (for example 10846).
3. To find more examples of one role: `python3 queries/q15_examples_of_construction.py --relation Poss --limit 10`.

### 5.6 A suggested order

1. Particles and pronouns (`quran-frequency-particles.csv`, top of `quran-frequency-lemmas.csv`).
2. The top 100 content words (`quran-frequency-lemmas.csv`).
3. The top 50 Form I verbs (`quran-verb-form-words.csv`, `form` = `I`).
4. Forms IV, II and VIII (same table).
5. Root families with several forms (`quran-root-form-summary.csv`, then the occurrences table).
6. The ten most common sentence roles (`quran-frequency-functions.csv`).
7. Test yourself with flashcards from the occurrences table.

---

## 6. Cautions

1. **Form I is assumed.** If a verb that you believe is in another form is counted as Form I, the notes did not mark it.
2. **Counts of lemmas, roots, word types and particles are counts of word parts.** They can be higher than a count of written words.
3. **The gloss is a short label, not a translation of the verse.** It is useful for recognition, not for exact meaning.
4. **Lemma and root frequencies mix every use.** A root's count includes its nouns and adjectives as well as its verbs. For verbs only, use the verb tables.
5. **Roots follow the experts' analysis.** Particles, pronouns and some other words have no root, so they do not appear in the root tables.
6. **The tables don't rank by usefulness for you.** They rank by how often an item occurs. Decide your own priorities (for example, a root family you care about) and use the filters.

## 7. About the corrected form descriptions

The notes' own English names for verb forms V to IX were wrong: for example, they called the form with pattern `ٱفْعَلَّ` "Fifth form" when it is the ninth. The `description` column in `quran-verb-form-summary.csv` shows the corrected names (the form number and the Arabic pattern were always right). The original wording is kept in the data files for reference.

## 8. What these tables cannot do

* **Per-surah counts in the frequency tables.** Everything is counted over the whole Quran. For a single surah, use `reading/quran-surah-profile.csv` (described in `study-and-linguist-tables-guide.md`), the verb-occurrences table (its `word` column starts with the chapter number) or the question scripts.
* **Meaning beyond a short label.** The glosses are word-level labels from the notes, not translations.

Many more tables (memorization-order lists, root families, written forms, conjugations, pronouns, prefixes, particles, verb usage and more) are described in `study-and-linguist-tables-guide.md`.
