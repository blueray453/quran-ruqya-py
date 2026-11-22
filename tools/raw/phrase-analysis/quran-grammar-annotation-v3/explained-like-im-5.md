# What this project does, in plain words

## The short version

We took the grammar notes that experts wrote for the Quran and attached them to every word of your IndoPak Quran text.

Now, for any word or sentence, you can ask things like:

* What does this word mean, roughly?
* What small pieces is it made of?
* Which other words is it connected to?
* Which word is understood but not written?

You get two kinds of help:

1. **Question helpers.** Small tools that answer one question each. There are 20 of them.
2. **Tables.** Spreadsheets you can open in Excel or Google Sheets and sort however you like.

---

## How to find a word or a sentence

**A word has an address with three numbers:** chapter, verse, word.

> `67:15:3` means chapter 67, verse 15, the 3rd word.

**A sentence has a single number**, like `10846`. You don't have to know it in advance. Question 9 below will tell you the sentence number of any word.

---

## How to ask a question

Each question helper is used by typing one short line and pressing Enter, like this:

```
python3 queries/q01_word_meaning.py 67:15:3
```

The first part says which helper to use. The last part is the word (or sentence) you are asking about. Change the last part to ask about a different word.

If you don't want to type, ask a technical friend to set it up once. After that, it is the same one line every time.

Every example below is a real answer from the real data.

---

## The 20 question helpers

### Questions about one word

**1. What does this word mean?**
* **What you get:** a short English label for the word, and how the same word is labelled elsewhere in the Quran.
* **How to ask:** `python3 queries/q01_word_meaning.py 67:15:3`
* **Example:** the word `جَعَلَ` is labelled **"made"**. Elsewhere the same word appears as "and made", "We made", "make".
* **Good to know:** this is a short label, not a full translation of the verse.

**2. What family is this word from?**
* **What you get:** the three-letter base the word grows from, its dictionary form, and what kind of word it is (noun, verb and so on).
* **How to ask:** `python3 queries/q02_root_lemma_pos.py 67:15:3`
* **Example:** base letters **ج ع ل**, dictionary form `جَعَلَ`, a **verb**.

**3. What small pieces is this word made of?**
* **What you get:** the word split into a piece at the front, the main part, and a piece at the end.
* **How to ask:** `python3 queries/q03_word_construction.py 67:15:4`
* **Example:** `لَكُمُ` is `لَ` ("for") + `كُمُ` ("you all").

**4. What details does the word carry?**
* **What you get:** past or present, who is doing it (I, you, he), masculine or feminine, one or many, and more, each explained in words.
* **How to ask:** `python3 queries/q04_word_features.py 67:15:3`
* **Example:** past tense, "he", masculine, one person.

**5. Which verb pattern is it?**
* **What you get:** Arabic verbs come in up to 12 patterns, and each pattern slightly changes the meaning. This tells you which one your verb uses.
* **How to ask:** `python3 queries/q05_verb_form.py 67:15:3`
* **Example:** it is the plain, basic pattern (called Form I).
* **Good to know:** the experts never write "Form I" in their notes. We assume it whenever a verb has no other pattern marked. The answer tells you whether the pattern was written down or assumed.

### Questions about words that belong together

**6. Which words form a group?**
* **What you get:** the little groups of words (phrases and clauses) that your word is part of.
* **How to ask:** `python3 queries/q06_phrase_membership.py 67:15:4`
* **Example:** `لَكُمُ` ("for you") is a small group on its own, and it also sits inside the bigger group "جَعَلَ لَكُمُ الْأَرْضَ ذَلُولًا".

**7. How is this word connected to the others?**
* **What you get:** the job the word does, which word it leans on, and which words lean on it.
* **How to ask:** `python3 queries/q07_word_relations.py 67:15:4`
* **Example:** the `لَ` part connects to the verb `جَعَلَ`, and the `كُمُ` part leans on the `لَ`.

**8. Why does this word end the way it does?**
* **What you get:** Arabic nouns change their endings depending on their job. This tells you the ending and gives a one-line reason.
* **How to ask:** `python3 queries/q08_case_explanation.py 67:15:5`
* **Example:** `الْأَرْضَ` ("the earth") has the ending for "the thing the verb acts on", because it is the object of the verb `جَعَلَ`.
* **Good to know:** the experts' notes contain endings and connections but never the reasons. The reasons come from a small set of simple rules we wrote. If none of our rules fits, the answer says nothing instead of guessing.

### Questions about a whole sentence

**9. Where does the sentence start and end?**
* **What you get:** the sentence's start and end, its number, and whether it spills over into other verses.
* **How to ask:** `python3 queries/q09_sentence_boundaries.py --key 67:15:3`
  (you can also use `--ayah 67:15` or `--sentence 10846`)
* **Example:** sentence 10846 runs from the 1st to the 6th word of verse 67:15.

**10. Who does what in this sentence?**
* **What you get:** every word sorted by its job: the doer, the thing acted on, the describer, and so on.
* **How to ask:** `python3 queries/q10_sentence_elements.py 10846`
* **Example:** "the earth" is the thing acted on, and the doer is an unwritten "he".

**11. Draw me the sentence.**
* **What you get:** the sentence as a tree, with the main word on the left and the words that lean on it indented to the right.
* **How to ask:** `python3 queries/q11_dependency_tree.py 10846`
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
  (The real answer also shows a small number at the end of each line.)

**12. What is understood but not written?**
* **What you get:** the words the experts say are there in the meaning but are not in the text, such as an unwritten "he".
* **How to ask:** `python3 queries/q12_implicit_elements.py --sentence 10846`
  (or `--ayah 67:15` for a whole verse)
* **Example:** one hidden "he" `(هُوَ)`, the doer of the verb, sitting between the 3rd and 4th words.

**13. Which little helper words are in the sentence?**
* **What you get:** the small words like "for", "the", "and", "not", each with its job, plus the order of the word types in the sentence.
* **How to ask:** `python3 queries/q13_particles_in_sentence.py 10846`
* **Example:** it finds `لَ` ("for") and `ٱلْ` ("the").
* **Good to know:** it tells you which helpers are there and what job they do. It does not explain what each one adds to the meaning.

### Questions about counting and finding

**14. What appears most often?**
* **What you get:** a top list of the most common words, base letters, word types, jobs or helper words.
* **How to ask:** `python3 queries/q14_frequencies.py --by lemma --n 20`
  (instead of `lemma`, you can use `root`, `pos`, `function` or `particle`)
* **Example:** the most common word is `مِن` ("from") with 3,226 uses, then `ٱللَّه` with 2,699.

**15. Show me more examples like this.**
* **What you get:** other places in the Quran with the same kind of word connection.
* **How to ask:**
  `python3 queries/q15_examples_of_construction.py --relation Poss --limit 5`
  (`Poss` means "belonging to", as in "the lord of the worlds")
  `python3 queries/q15_examples_of_construction.py --pos_sequence "P N"`
  `python3 queries/q15_examples_of_construction.py --function_sequence "link gen"`
* **Example:** there are 9,805 "belonging to" connections in the Quran, and the first is `اللّٰهِ` in the very first verse.

**16. How are the verb patterns spread out?**
* **What you get:** how many verbs use each of the 12 patterns, and which base-letter families use several patterns.
* **How to ask:** `python3 queries/q16_verb_form_statistics.py`
* **Example:** 12,347 verbs use the basic pattern (assumed, not written), 3,487 use the fourth pattern, and 1,300 use the second.

**17. Which "doer-words" and "action-nouns" exist?**
* **What you get:** words built from verbs that act like nouns, such as "writer" from "write". They are counted separately and are never counted as verbs.
* **How to ask:** `python3 queries/q17_derived_nouns.py`
* **Example:** 2,974 "doer" words, 674 "action" nouns, 551 "done-to" words.

**18. Which patterns repeat, and where?**
* **What you get:** looks up a repeating pattern of word types or jobs (see "Tables about patterns" below) and shows where it appears.
* **How to ask:** `python3 queries/q18_repeated_sequences.py --kind pos --id P00001`
* **Example:** the plain noun pattern appears 10,347 times, but only 15 of those are "on its own" (explained in the pattern tables below).

**19. Where else does this word family appear?**
* **What you get:** every word with the same three-letter base, the same dictionary form, or the same spelling.
* **How to ask:** `python3 queries/q19_occurrences.py --root jEl --limit 10`
  (roots are typed with English letters: `jEl` stands for ج ع ل)
* **Example:** 346 words share that base, such as `یَجْعَلُوْنَ` ("They put") at 2:19:9 and `جَعَلَ` ("made") at 2:22:2.

### A question about problems in the data

**20. What is unusual in the source notes?**
* **What you get:** a count of the odd cases, and with `--full 1` the full list of every one.
* **How to ask:** `python3 queries/q20_source_issues.py` (add `--full 1` for everything)
* **What it finds:**
  * 3 spots where the experts' notes treat two words as one
  * 41 words whose pieces were put into two different sentences
  * 26 tiny "sentences" that hold only a front piece like `و` or `ال`
  * 836 sentences that stretch over more than one verse
  * 16 words that lost letters in their plain spelling (the font packs several letters into one symbol)
  * 132 places where two sources disagree about the type of a word

---

## The tables (spreadsheets)

Double-click a table to open it in Excel. If the Arabic looks wrong, use **Data → From Text/CSV** and choose **UTF-8**. Click a column heading to sort.

### Tables about patterns (folder `output/sequences/`)

Think of a sentence as a row of beads. Each bead is a word, coloured by its **type** (noun, verb, small helper word...) or by its **job** (doer, thing acted on...). A **pattern** is a short row of colours that shows up in many places. These tables count them. Types and jobs are never mixed.

**`quran-pos-sequences.csv`** (22,734 patterns, by type) and **`quran-function-sequences.csv`** (22,509 patterns, by job)
* **What it is:** every pattern that appears at least twice.
* **What it tells you:** how often the pattern appears, how many of those are "on its own", and one Arabic example.
* **What "on its own" means:** say the pattern is "noun". It appears 10,347 times. In 10,332 of those times the noun is part of a longer pattern that repeats. In only 15 times does it stand by itself. The two numbers always add up to the total.
* **How to use it:** open it and sort by `total_count` to see the most common patterns, or by `length` to see the longest.

**`quran-greedy-order-pos-sequences.csv`** and **`quran-greedy-order-function-sequences.csv`**
* **What it is:** a "study this first" list.
* **What it tells you:** it picks the pattern that lets you recognise the most new words for the least effort, then the next best, and so on. No word is counted twice.
* **How to use it:** read from the top. `cumulative_words_to_learn` says how many words you have studied so far, and `cumulative_pct_of_quran` says how much of the Quran you can now recognise.
* **Example:** the first pattern, "verb with attached pronoun + preposition + noun" (like `خَلَقَهٗ مِنْ تُرَابٍ`), appears 295 times and covers 885 words, about 1% of the Quran, for only 3 words of study.
* **Good to know:** patterns shorter than three words are left out. Otherwise the list would just start with the most common single word types, which tells you nothing useful.

**The `…annotation.json` files and `sequence-analysis-report.json`**
* **What they are:** the exact "where" notebooks behind the tables and a record of the settings used.
* **How to use them:** you don't. Question 18 uses them for you.

### Tables about verbs and counts (folder `output/analysis/`)

**About verbs**

| Table | What it shows | Example |
|---|---|---|
| `quran-verb-form-summary.csv` | One row per verb pattern (12 rows): how many verbs, how many base-letter families | basic pattern: 12,347 verbs |
| `quran-verb-form-words.csv` | The verb words under each pattern | `قَالَ` ("said") is used 1,618 times in the basic pattern |
| `quran-root-form-summary.csv` | For each base-letter family, which patterns it uses | the family `خلف` uses 7 different patterns |
| `quran-verb-form-occurrences.csv` | **Every single verb in the Quran** (19,356 rows) with its pattern, tense, person and English label | `نَعْبُدُ` at 1:5:2 |
| `quran-derived-form-summary.csv` | The "doer", "done-to" and "action" noun counts | 2,974 doer words |

**About counting** (already sorted, biggest first)

| Table | What it counts | Top row |
|---|---|---|
| `quran-frequency-lemmas.csv` | dictionary words (4,832) | `مِن` 3,226 |
| `quran-frequency-roots.csv` | three-letter bases (1,642) | `اله` 2,851 |
| `quran-frequency-pos.csv` | word types (45) | noun 25,136 |
| `quran-frequency-functions.csv` | jobs in a sentence (677) | main word 9,042 |
| `quran-frequency-particles.csv` | little helper words (36) | preposition 13,005 |

**The "odd cases" lists** (folder `output/analysis/source-lists/`)

These are the complete lists behind question 20. Open one when you want to see every case.

| Table | What is in it | Rows |
|---|---|---|
| `sentences-crossing-ayah.csv` | sentences that stretch over more than one verse | 836 |
| `words-merged-in-treebank.csv` | words one source treats as one and the other as two | 3 |
| `words-split-across-sentences.csv` | words whose pieces sit in two sentences | 41 |
| `sentences-prefix-only-fragments.csv` | tiny "sentences" holding only a front piece | 26 |
| `words-text-normalized-incomplete.csv` | words whose plain spelling lost letters | 16 |
| `segments-pos-differs-from-v04.csv` | places where two sources disagree about word type | 132 |

---

## "I want to..." quick guide

| I want to... | Use |
|---|---|
| know roughly what a word means | question 1 |
| see a word's base letters and dictionary form | question 2 |
| see the pieces a word is made of | question 3 |
| see tense, "he/she/you", singular or plural | question 4 |
| know a verb's pattern | question 5 |
| see which words go together | question 6 |
| see how two words are connected | question 7 |
| understand why a word ends the way it does | question 8 |
| find where a sentence starts and ends | question 9 |
| see who does what | question 10 |
| see a sentence as a drawing | question 11 |
| find the unwritten words | question 12 |
| find the small helper words | question 13 |
| find the most common words | question 14, or the `quran-frequency-…` tables |
| find more examples of one kind of connection | question 15 |
| count verbs by pattern | question 16, or `quran-verb-form-summary.csv` |
| count doer-words and action-nouns | question 17 |
| find word-type or job patterns that repeat | the `quran-…-sequences.csv` tables, or question 18 |
| decide what to study first | the `quran-greedy-order-…` tables |
| find every use of a word family | question 19, or `quran-verb-form-occurrences.csv` |
| see what is unusual in the data | question 20, or the `source-lists` tables |

---

## A few words you will meet

| Word | What it means |
|---|---|
| **three-letter base (root)** | The three letters a whole family of related words grows from. |
| **dictionary form** | The word the way a dictionary would list it. |
| **word type** | Noun, verb, small helper word, and so on. |
| **job** | What the word does in the sentence: doer, thing acted on, describer. |
| **piece** | A part of a word: front piece, main part, end piece. |
| **ending** | The ending a noun takes to show its job in the sentence. |
| **unwritten word** | A word that is understood in the meaning but is not in the text. |
| **basic pattern** | The plainest of the 12 verb patterns, with no extra letters added. |
| **assumed vs written** | "Written" means the experts' notes say it. "Assumed" means we filled it in by a simple rule. |
| **on its own** | A pattern that appears by itself, not as part of a longer repeating pattern. |
| **study-first list** | The "most new words for the least effort" order. |

---

## Things to keep in mind

1. **The English meaning is only a short label.** It is not a translation of the verse.
2. **The "why" answers come from simple rules we wrote.** The experts' notes do not contain reasons.
3. **The basic verb pattern is always an assumption.** It is never written in the notes.
4. **This is one team of experts' reading of the grammar.** We copy what they say. We don't claim it is the only way to read the Quran.
5. **Two sources cut the text into words slightly differently in three verses** (2:181, 8:6, 13:37). We matched them up by their Arabic letters and listed the cases.
6. **A few words lost letters in the plain spelling** because the font packs several letters into one symbol. There are 16, and they are listed.
7. **The grammar notes come from the Quranic Arabic Corpus**, which asks anyone using them to give credit and share under the same terms.

If something is unclear, run question 20 with `--full 1` to see the exact cases, or open `docs/SCHEMA.md` for the technical version.
