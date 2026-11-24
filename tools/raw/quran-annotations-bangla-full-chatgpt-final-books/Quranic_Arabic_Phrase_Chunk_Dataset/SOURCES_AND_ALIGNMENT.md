# Sources, books and curriculum alignment

## 1. ILMHUB: keep the learner-facing grammar map stable

ILMHUB Foundations presents the 3–2–6 framework: three word classes (Ism, Fi'l, Harf), two principal sentence types (nominal and verbal), and six core phrase constructions. This remains the organising mental model for the beginner curriculum.

Official ILMHUB references:

- Foundations: <https://www.ilmhub.org/arabic-grammar/foundations/>
- The Four Properties of ISM: <https://www.ilmhub.org/courses/language-of-quran/book-1/l01-p1-four-properties-of-ism/>
- The Ism: <https://www.ilmhub.org/arabic-grammar/the-ism/>
- Phrases: <https://www.ilmhub.org/arabic-grammar/phrases/>
- Essential Parts (Book 2): <https://www.ilmhub.org/courses/language-of-quran/book-2/bk2-l01-p2/>
- Book 1: <https://www.ilmhub.org/courses/language-of-quran/book-1/>
- Book 2: <https://www.ilmhub.org/courses/language-of-quran/book-2/>

Four properties (DiGNI):

1. Definiteness: Ma'rifah / Nakirah.
2. Gender: Mudhakkar / Mu'annath.
3. Number: Mufrad / Muthanna / Jam'.
4. I'rab: grammatical state, including Raf', Nasb and Jarr for Ism.

Six core phrase constructions:

1. Murakkab Tawsifi — descriptive.
2. Murakkab Idafi — possessive / Idafah.
3. Murakkab Jarri — prepositional.
4. Murakkab Ishari — demonstrative.
5. Murakkab Atfi — conjunctive.
6. Murakkab Badali — substitution.

The ILMHUB phrase guide also discusses supplementary compound constructions such as numerical and blended compounds. They are not added to the core six in this dataset.

The demonstrative construction is treated carefully: a demonstrative followed by a definite target is a core Ishari phrase candidate; a demonstrative followed by an indefinite noun may instead function as a complete sentence. The dataset therefore excludes indefinite targets from the confirmed Ishari subset and retains candidates separately.

## 2. User-supplied Bayyinah book: preserve its sequence

Book used as a curriculum crosswalk (not reproduced in this project):

**The Qur'an's Language: A New Approach — Bayyinah Dream Arabic Program**, Section 1: Nahw and Section 2: Sarf.

The Nahw chapters in the supplied copy establish this progression:

| Chapter | Topic group | Curriculum placement |
|---|---|---|
| 1 | Types/classes of words | Foundations: Ism, Fi'l, Harf |
| 2 | I'rab/status and signs; pronouns; Jarr/Majrur; Harf al-Nasb and its Ism; Idafah | Ism properties, case, pronouns, particles and phrase construction |
| 3 | Gender, number and “qism/type” | Gender and number; terminology requires a deliberate crosswalk to ILMHUB DiGNI |
| 4 | Mawsuf/Sifah, Ism al-Isharah, Huruf al-'Atf | Tawsifi, Ishari and Atfi |
| 5 | Jumlah Ismiyyah, Mubtada/Khabar, word order and complex sentences | Nominal sentence and phrase as sentence slot |
| 6 | Madi, Fa'il, Maf'ul, questions and complex sentences | Verbal sentence; agent and object |
| 7 | Mudari', governing particles, commands/prohibitions and word order | Fi'l morphology and mood; particle governance |
| 8 | Passive voice | Passive clause and Na'ib al-Fa'il |
| 9 | Negation | Negation of nominal/verbal structures |
| 10 | Kana and sisters | Ism Kana / Khabar Kana |
| 11 | Compound Ism, An and sisters, compound Mudaf Ilayh | Advanced noun/particle structures |

The book's Sarf section adds verb forms, weak/irregular verbs, derived forms, verbal nouns/participles and plural patterns. These are linked to chunk examples but stay in the morphology curriculum rather than being redefined as phrase types.

**Terminology caution:** the supplied Bayyinah Chapter 3 heading includes “qism/type”. This project does not silently equate that wording with ILMHUB's definiteness property. The learner-facing current four-property framework follows ILMHUB's explicit labels until a qualified instructor approves a more detailed crosswalk.

## 3. User-supplied Arabic101 85% guide: use method, not protected content

The supplied copy of **How to understand 85% of the Quran** is marked “FREE VERSION — PERSONAL USE ONLY — NOT FOR SALE / DISTRIBUTION”. It is not included in this package. The curriculum audit uses only the high-level pedagogical idea of frequency-led sequencing, function-word/particle work, thematic vocabulary and systematic review. No word list, page text, examples or protected explanatory content is reproduced.

The frequency-led vocabulary strategy supports the traditional grammar map; it does not replace the Ism/Fi'l/Harf categories, the two sentence types or the six phrase constructions.

## 4. Quranic Arabic Corpus (QAC): annotation and extraction source

- Main corpus: <https://corpus.quran.com/>
- Documentation: <https://corpus.quran.com/documentation/>
- Morphological features: <https://corpus.quran.com/documentation/morphologicalfeatures.jsp>
- Syntactic relations: <https://corpus.quran.com/documentation/syntaxrelation.jsp>

QAC documents a Quranic Arabic annotation approach with morphology and syntactic dependency relations. Written words can comprise multiple morphological segments (prefix, stem and suffix). The dataset therefore keeps written-word display and segment-level members separately. Dependency relations are preserved as source evidence and are not automatically equivalent to a complete human-reviewed grammar lesson label.

The QAC-derived Treebank source inputs in this package include 77,432 whole-word positions and 11,693 sentence records. The source constituent tags used include PP, NS, VS, SC, CS and S. These are maintained as source types, not substituted for the ILMHUB six phrase constructions.

## 5. How sources are kept separate in this dataset

| Source / framework | Role | Not used for |
|---|---|---|
| ILMHUB | Learner-facing grammar taxonomy and sequence | Corpus-frequency claims |
| Bayyinah book | Detailed traditional topic progression and examples to map | Replacing or expanding the six phrase taxonomy indiscriminately |
| Arabic101 frequency guide | Frequency-first vocabulary sequencing method | Reproducing protected lists or replacing grammar architecture |
| QAC morphology | Word/segment POS and morphological evidence | Assuming every source tag is a teacher-approved pedagogical label |
| QAC syntax/treebank | Dependency edges, constituent spans and sentence structure | Treating relation counts as an exhaustive census of all possible grammar |
| Repeated n-gram annotations | Recurring lexical strings and locations | Calling every repeated string a grammatical phrase |

## 6. Licensing and reuse

This package contains derived and source-normalized text/annotation files. Rights and licence conditions can differ by source component and by Quran text edition. Check the relevant source licence and obtain permission where required before public redistribution or commercial embedding. The supplied personal-use-only Arabic101 book and the Bayyinah book are not included in the package.
