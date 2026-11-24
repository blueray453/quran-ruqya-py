# Plain-language guide to the Quran grammar project

## What this is

The project attaches grammar information to every word and sentence of your IndoPak Quran text. The information comes from the Quranic Arabic Corpus, a set of notes written by Arabic grammar experts. Nothing was invented: where the experts' notes say nothing, the project says nothing.

For any word you can find its meaning label, root, word type, pieces, endings and verb pattern. For any sentence you can find who does what, which words depend on which, and which words are understood but not written.

You use it in two ways:

1. **Question scripts.** Twenty-three small programs. Each one answers a single question about a word, a sentence or the whole Quran.
2. **Spreadsheets.** Tables you can open in Excel or Google Sheets, sort and filter. They cover repeating grammar patterns, verb statistics, word counts and a list of oddities in the source data.

---

## How to refer to a word or a sentence

* **A word** is written as `chapter:verse:word`. For example, `67:15:3` is chapter 67, verse 15, the third word. Words are counted as in your IndoPak text.
* **A sentence** has a number, for example `10846`. These are the sentence numbers used in the grammar notes. A sentence can be shorter than a verse, or it can span several verses. You don't need to know the number in advance: question 9 returns it for any word.

## How to run a question

Each question script is run by typing one line in a terminal and pressing Enter:

```
python3 queries/q01_word_meaning.py 67:15:3
```

The first part names the script. The last part is the word or sentence you are asking about; replace it to ask about something else. The answer is printed on screen. If you would rather not use a terminal, someone technical can set it up once for you; after that, the line is always the same.

All examples below are real answers.

---

## The 23 questions

### About a single word

**1. What does this word mean?**
* **Returns:** a short English gloss for each part of the word, and the glosses the same dictionary word has elsewhere in the Quran.
* **Command:** `python3 queries/q01_word_meaning.py 67:15:3`
* **Example:** `جَعَلَ` is glossed "made"; elsewhere the same word appears as "and made", "We made", "make".
* **Note:** this is a short word-level gloss, not a translation of the verse.

**2. What are its root, dictionary form and word type?**
* **Returns:** the root, the lemma (dictionary form) and the part of speech (noun, verb, particle and so on).
* **Command:** `python3 queries/q02_root_lemma_pos.py 67:15:3`
* **Example:** root ج ع ل, lemma `جَعَلَ`, verb.

**3. What is the word made of?**
* **Returns:** the word split into prefix, stem and suffix, with the type of each part.
* **Command:** `python3 queries/q03_word_construction.py 67:15:4`
* **Example:** `لَكُمُ` is the prefix `لَ` ("for") plus the pronoun `كُمُ` ("you all").

**4. What grammatical details does it carry?**
* **Returns:** tense, person, gender, number, case, state, voice and mood, wherever the notes give them, each with a plain explanation.
* **Command:** `python3 queries/q04_word_features.py 67:15:3`
* **Example:** perfect (past) tense, third person, masculine, singular.

**5. Which verb form is it?**
* **Returns:** the verb form (I to XII), its pattern, and whether the form is written in the notes or assumed.
* **Command:** `python3 queries/q05_verb_form.py 67:15:3`
* **Example:** Form I, assumed.
* **Note:** the notes never write "Form I". We assume it for any verb with no other form marked, which is the convention in the notes' own feature guide.

### About words that belong together

**6. Which words form a phrase or clause with this word?**
* **Returns:** the phrases and clauses that contain the word, using the experts' labels (verbal sentence, nominal sentence, prepositional phrase and so on).
* **Command:** `python3 queries/q06_phrase_membership.py 67:15:4`
* **Example:** `لَكُمُ` is a prepositional phrase by itself, inside the verbal sentence `جَعَلَ لَكُمُ الْأَرْضَ ذَلُولًا`.

**7. How is it connected to the other words?**
* **Returns:** the word's grammatical role, the word it depends on (its head), and the words that depend on it.
* **Command:** `python3 queries/q07_word_relations.py 67:15:4`
* **Example:** the prefix `لَ` links to the verb `جَعَلَ`; the pronoun `كُمُ` depends on `لَ`.

**8. Why does the word have this case?**
* **Returns:** the case ending (nominative, accusative or genitive), the word's role and head, and a one-line reason.
* **Command:** `python3 queries/q08_case_explanation.py 67:15:5`
* **Example:** `الْأَرْضَ` is accusative because it is the object of the verb `جَعَلَ`.
* **Note:** the notes give the case, the role and the head, but not the reason. The reasons come from a small set of rules we wrote for the common situations. When no rule applies, the answer is left empty instead of guessed.

### About a whole sentence

**9. Where does the sentence begin and end?**
* **Returns:** the sentence number, its first and last word, the verses it covers, and whether it crosses a verse boundary.
* **Command:** `python3 queries/q09_sentence_boundaries.py --key 67:15:3` (you can also use `--ayah 67:15` or `--sentence 10846`)
* **Example:** sentence 10846 runs from word 1 to word 6 of verse 67:15.

**10. What are the subject, object and other elements?**
* **Returns:** every word of the sentence grouped by its role.
* **Command:** `python3 queries/q10_sentence_elements.py 10846`
* **Example:** the object is `الْأَرْضَ`; the subject is an unwritten "he".

**11. How are the words linked? (dependency tree)**
* **Returns:** the sentence as an indented tree, with each word under the word it depends on.
* **Command:** `python3 queries/q11_dependency_tree.py 10846`
* **Example:**
  ```
  [root] هُوَ
      [Pred] ٱلَّذِى
          [sub] جَعَلَ
              [Subj] (هُوَ)  (unwritten)
              [link] لَ
                  [gen] كُمُ
              [Obj] أَرْضَ
              [Obj] ذَلُولًا
  ```
  The label in brackets is the word's role (Subj = subject, Obj = object, Pred = predicate, gen = genitive). The real output also adds a small token number to each line.

**12. Which elements are implicit?**
* **Returns:** the elements the experts consider present in the meaning but not written, with their role and position.
* **Command:** `python3 queries/q12_implicit_elements.py --sentence 10846` (or `--ayah 67:15`)
* **Example:** an implicit pronoun `(هُوَ)` ("he"), the subject of the verb, located between the third and fourth word.

**13. Which particles are in the sentence?**
* **Returns:** every particle (prepositions, conjunctions, the definite article and others) with its role, plus the sentence's word-type order.
* **Command:** `python3 queries/q13_particles_in_sentence.py 10846`
* **Example:** `لَ` (preposition "for") and `ٱلْ` (definite article).
* **Note:** it identifies particles and their roles. It does not explain what each particle adds to the meaning, because the notes don't.

### About counting and finding

**14. What is most frequent?**
* **Returns:** a ranked list of the most frequent dictionary words, roots, word types, sentence roles or particles.
* **Command:** `python3 queries/q14_frequencies.py --by lemma --n 20` (`--by` can also be `root`, `pos`, `function` or `particle`)
* **Example:** the most frequent word is `مِن` (3,226 times), then `ٱللَّه` (2,699).

**15. Where are more examples of this construction?**
* **Returns:** other places with the same grammatical relationship or the same sequence of word types or roles.
* **Commands:**
  `python3 queries/q15_examples_of_construction.py --relation Poss --limit 5` (`Poss` is the possessor in a possessive phrase)
  `python3 queries/q15_examples_of_construction.py --pos_sequence "P N"`
  `python3 queries/q15_examples_of_construction.py --function_sequence "link gen"`
* **Example:** there are 9,805 possessor relations in the Quran; the first is `اللّٰهِ` in verse 1:1.

**16. How are verbs distributed across Forms I to XII?**
* **Returns:** the number of verbs, roots and dictionary words per form, and which roots occur in several forms.
* **Command:** `python3 queries/q16_verb_form_statistics.py`
* **Example:** 12,347 verbs in Form I (all assumed), 3,487 in Form IV, 1,300 in Form II.

**17. Which derived nouns occur?**
* **Returns:** counts of active participles, passive participles and verbal nouns, with their roots. They are never counted as verbs.
* **Command:** `python3 queries/q17_derived_nouns.py`
* **Example:** 2,974 active participles, 674 verbal nouns, 551 passive participles.

**18. Which grammar patterns repeat, and where?**
* **Returns:** a repeating pattern from the pattern spreadsheets (see below), its counts, and where it occurs.
* **Command:** `python3 queries/q18_repeated_sequences.py --kind pos --id P00001`
* **Example:** the single-noun pattern occurs 10,347 times, of which only 15 are "stand-alone" (explained below).

**19. Where else does this root, word or form occur?**
* **Returns:** every word with the same root, dictionary form, spelling or word type.
* **Command:** `python3 queries/q19_occurrences.py --root jEl --limit 10` (roots are typed in English letters; `jEl` is ج ع ل)
* **Example:** 346 words have this root, for example `یَجْعَلُوْنَ` ("They put") at 2:19:9 and `جَعَلَ` ("made") at 2:22:2.

### About problems in the source data

**20. What is irregular in the source notes?**
* **Returns:** counts of the irregular cases; with `--full 1` it prints every one.
* **Command:** `python3 queries/q20_source_issues.py` (add `--full 1` for the complete lists)
* **Finds:**
  * 3 cases where the experts' notes treat two IndoPak words as one word
  * 41 words whose parts are assigned to two different sentences
  * 26 very short "sentences" that contain only a prefix such as `و` or `ال`
  * 836 sentences that cross a verse boundary
  * 16 words whose plain spelling is missing letters, because the IndoPak font stores several letters as one glyph
  * 132 places where two versions of the notes give a different word type

### About roots, verbs and the difficulty of an ayah

**21. Which words belong to this root?**
* **Returns:** every word of a root with how often it occurs, its word types, its verb forms and its most common short meanings.
* **Command:** `python3 queries/q21_root_family.py Elm` (`Elm` is the root علم)
* **Example:** 854 occurrences in total, including `عَلِمَ` ("knew", 382 times) and the other words of the family.

**22. How is this verb used?**
* **Returns:** how often the verb has an object, how its subject is expressed (inside the verb, a separate word or unwritten) and which prepositions it is linked to.
* **Command:** `python3 queries/q22_verb_patterns.py Ealima` (verbs are typed in English letters; put quotes around ones that contain an apostrophe)
* **Example:** `عَلِمَ` occurs 382 times, all in Form I, and 218 of those have an object.
* **Note:** "object" includes a quoted statement after "said".

**23. How hard is this ayah?**
* **Returns:** each dictionary word in the ayah with how often it occurs in the Quran, and the share of the ayah covered by the 100, 500 and 1,000 most frequent words.
* **Command:** `python3 queries/q23_ayah_vocabulary.py 1:2`
* **Example:** verse 1:2 has four dictionary words, all among the 500 most frequent.

---

## The spreadsheets

This section covers the first two folders. The memorization-order, phrase, lexicon, syntax and reading tables are explained in `study-and-linguist-tables-guide.md`. Open a `.csv` file with Excel. If the Arabic looks garbled, use **Data → From Text/CSV** and choose **UTF-8**. In Google Sheets use **File → Import**. Click a column heading to sort.

### Pattern tables (folder `output/sequences/`)

A **pattern** is a run of consecutive words described by their **word types** (noun, verb, preposition and so on) or by their **roles in the sentence** (subject, object and so on). The two are never mixed. A pattern never crosses a sentence boundary, and only patterns that occur at least twice are listed.

**`quran-pos-sequences.csv`** (22,734 patterns by word type) and **`quran-function-sequences.csv`** (22,509 patterns by role)
* **What each row tells you:** the pattern, its length, how many times it occurs in total, how many of those are stand-alone, and one Arabic example.
* **Stand-alone:** an occurrence counts as stand-alone when it is not part of a longer pattern that itself repeats. Example: the single-noun pattern occurs 10,347 times; in 10,332 of them the noun is part of a longer repeating pattern, and in 15 it is not. Total always equals stand-alone plus inside-longer.
* **Use:** sort by `total_count` for the most common patterns, or by `length` for the longest.

**The study-first lists for patterns** (folder `output/memorization-order/`, eight files named `quran-greedy-order-pos-…` and `quran-greedy-order-function-…`)
* **What it is:** a suggested order for learning patterns. At each step it picks the pattern that lets you recognise the most not-yet-covered words per word of pattern length, and no word is counted twice.
* **Use:** read from the top. `cumulative_words_to_learn` is the study effort so far; `cumulative_pct_of_quran` is the share of the Quran's words you can now recognise.
* **Example:** the first pattern is "verb with attached pronoun + preposition + noun" (such as `خَلَقَهٗ مِنْ تُرَابٍ`). It occurs 295 times and covers 885 words (about 1.1% of the Quran) for 3 words of study.
* **Variants:** `…-labels-and-sequences.csv` (everything), `…-sequences-only.csv` (two or more words), `…-sequences-3plus.csv` (three or more, the recommended one) and `…-sequences-5plus.csv`. The first variant simply starts with the most common single word types, which carries little ordering; the three-plus lists are the useful ones.

**The `…annotation.json` files and `sequence-analysis-report.json`** hold the exact locations behind the tables and the settings used. You don't need to open them: question 18 reads them for you.

### Verb and counting tables (folder `output/analysis/`)

| Table | Contents | Example |
|---|---|---|
| `quran-verb-form-summary.csv` | one row per verb form, I to XII: verbs written vs assumed, number of roots | Form I: 12,347 verbs, 675 roots |
| `quran-verb-form-words.csv` | the verbs (dictionary words) under each form, with root and counts | `قَالَ` ("said"), Form I: 1,618 times |
| `quran-root-form-summary.csv` | for each root, the forms it occurs in and how often | root `خلف` occurs in 7 forms |
| `quran-verb-form-occurrences.csv` | every verb in the Quran (19,356 rows): form, tense, person, gender, number, gloss | `نَعْبُدُ` at 1:5:2 |
| `quran-derived-form-summary.csv` | participles and verbal nouns, kept apart from verbs | 2,974 active participles |
| `quran-frequency-lemmas.csv` | dictionary words by frequency (4,832) | `مِن`: 3,226 |
| `quran-frequency-roots.csv` | roots by frequency (1,642) | `اله`: 2,851 |
| `quran-frequency-pos.csv` | word types by frequency (45) | noun: 25,136 |
| `quran-frequency-functions.csv` | sentence roles by frequency (677) | main word of the sentence: 9,042 |
| `quran-frequency-particles.csv` | particles by frequency (36) | preposition: 13,005 |

The frequency tables are already sorted from most to least frequent.

### Lists of irregularities (folder `output/analysis/source-lists/`)

These are the complete lists behind question 20.

| Table | Contents | Rows |
|---|---|---|
| `sentences-crossing-ayah.csv` | sentences that span more than one verse | 836 |
| `words-merged-in-treebank.csv` | words the notes treat as one that IndoPak writes as two | 3 |
| `words-split-across-sentences.csv` | words whose parts belong to two sentences | 41 |
| `sentences-prefix-only-fragments.csv` | very short sentences holding only a prefix | 26 |
| `words-text-normalized-incomplete.csv` | words whose plain spelling lost letters | 16 |
| `segments-pos-differs-from-v04.csv` | places where two versions of the notes give a different word type | 132 |

---

## Quick guide: what to use for what

| I want to... | Use |
|---|---|
| see a word's meaning label | question 1 |
| find a word's root, dictionary form and type | question 2 |
| see a word's prefix, stem and suffix | question 3 |
| see tense, person, gender, number, case | question 4 |
| find a verb's form | question 5 |
| see which words form a phrase | question 6 |
| see how a word is connected to others | question 7 |
| understand a word's case | question 8 |
| find where a sentence begins and ends | question 9 |
| find the subject, object and other elements | question 10 |
| see the dependency tree of a sentence | question 11 |
| find implicit (unwritten) elements | question 12 |
| find the particles in a sentence | question 13 |
| find the most frequent words or roots | question 14, or the `quran-frequency-…` tables |
| find more examples of a construction | question 15 |
| count verbs by form | question 16, or `quran-verb-form-summary.csv` |
| count participles and verbal nouns | question 17 |
| find repeating grammar patterns | the `quran-…-sequences.csv` tables, or question 18 |
| decide what to study first | the tables in `output/memorization-order/` |
| see which words belong to a root | question 21 |
| see how a verb is used | question 22 |
| check how hard an ayah is | question 23 |
| find every use of a root | question 19, or `quran-verb-form-occurrences.csv` |
| see what is irregular in the data | question 20, or the `source-lists` tables |

---

## Terms used

| Term | Meaning |
|---|---|
| **root** | the three consonants a family of related words is built on |
| **lemma** | the dictionary form of a word |
| **word type (part of speech)** | noun, verb, particle and so on |
| **role (function)** | what the word does in the sentence: subject, object, predicate and so on |
| **prefix, stem, suffix** | the parts of a written word: before, main part, after |
| **head** | the word that another word depends on |
| **case** | nominative, accusative or genitive: the ending that marks a noun's role |
| **implicit element** | something understood in the meaning but not written |
| **verb form (I–XII)** | one of the twelve derived verb patterns |
| **written vs assumed** | "written" means the experts' notes state it; "assumed" means we filled it in with a stated rule |
| **gloss** | a short English label for a word |
| **stand-alone** | an occurrence of a pattern that is not inside a longer repeating pattern |

---

## Limits to keep in mind

1. **The meaning is a short gloss only.** It is not a translation of the verse.
2. **Reasons for case are rule-based.** The experts' notes do not include reasons; question 8 applies a small set of rules and says nothing when none fits.
3. **Form I is always assumed.** It is never written in the notes.
4. **The grammar is one set of experts' analysis.** The project reproduces it faithfully and does not claim it is the only reading.
5. **Word boundaries differ slightly between the two sources in three verses** (2:181, 8:6, 13:37). The two were matched by their Arabic letters, and the cases are listed.
6. **Sixteen words lost letters in the plain spelling** because of the IndoPak font. They are listed.
7. **Licence.** The grammar notes come from the Quranic Arabic Corpus, which requires credit and sharing under the same terms.

For the technical description of every field, see `docs/SCHEMA.md`.
