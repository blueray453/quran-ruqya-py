# Project handoff: Quranic Arabic grammar datasets

## 1. Project objective

Build two comprehensive, normalized JSON datasets representing Quranic Arabic grammar. The purpose is to help learners understand how individual Quranic words are constructed and inflected, how words connect grammatically within sentences, and how morphology and syntax contribute to meaning.

**Current priority: Get the two JSON datasets correct. CSV generation is deferred.**

## 2. Files to generate

### JSON 1: `indopak-nastaleeq-wbw-grammar-normalized.json`

Word-level morphology. One record per complete written Quranic word, identified by `surah:ayah:word`.

It should contain:
- Original and normalized Arabic text.
- Quranic location and stable word ID.
- POS, root and lemma.
- Prefixes, stems and suffixes.
- Gender, number, case and other available grammatical features.
- Verb tense, voice, person and Forms I–XII where supported.
- Explicit versus inferred verb-form classification.
- Derived nominal information.
- All original morphology annotations and source fields.
- Centralized reference dictionaries.

### JSON 2: `indopak-nastaleeq-sentence-grammar-normalized.json`

Sentence-level grammar and syntax. One record per original Quranic Treebank sentence ID.

It should contain:
- Original sentence IDs and boundaries.
- Quranic locations and ayah spans.
- Complete written words in their original order.
- Stable references to morphology word IDs.
- POS and syntactic functions separately.
- Original segment-level syntactic annotations.
- Head-dependent relationships.
- Constituents and phrase boundaries.
- Implicit grammatical nodes.
- Whole-word sequence projections.
- All original Treebank annotations and metadata.
- Centralized reference dictionaries.

## 3. Existing files must remain unchanged

These are inputs, not outputs. Never modify or overwrite them:

1. `indopak-nastaleeq.json`
2. `indopak-nastaleeq-wbw.json`
3. `indopak-nastaleeq-wbw-normalized.json`

## 4. Architectural decisions

| Decision | Requirement |
|---|---|
| Number of canonical JSON files | Exactly two for now |
| Morphology granularity | One complete written word per record |
| Syntax granularity | One original Treebank sentence per record |
| Word identity | `surah:ayah:word` |
| Sentence identity | Original Treebank sentence ID |
| Sentence word sequence | Never split a written word into multiple positions |
| POS and function | Separate concepts |
| Original annotations | Preserve losslessly |
| Derived information | Clearly distinguish from original annotations |
| Implicit nodes | Preserve, but exclude from visible word sequence |
| Cross-ayah sentences | Preserve original sentence boundaries |
| Reference dictionaries | Store centrally |
| CSV generation | Deferred |

Important distinctions:
- Form I must be distinguished as explicitly annotated or inferred.
- Nouns and adjectives with derived-form annotations must not be counted as verb occurrences.
- A word may have multiple segment-level syntactic annotations. Preserve all of them.
- Whole-word projections are derived representations, not replacements for original annotations.
- Morphology and sentence grammar connect through stable word IDs. Avoid duplicating complete morphology records in the sentence dataset.

## 5. Learner-focused questions

### Word-level
1. What does this word mean in context?
2. What are its root, lemma and POS?
3. How is it morphologically constructed?
4. What grammatical features does it carry?
5. Why does it have this particular form?
6. Where else does the word, lemma or root occur?

### Phrase-level
7. Which words belong together?
8. What grammatical relationships connect them?
9. Why does each word have its particular grammatical case?
10. How do construct phrases and adjective-noun phrases work?

### Sentence-level
11. Where are sentence and clause boundaries?
12. What are the subjects, predicates, objects and other grammatical elements?
13. How are words connected syntactically?
14. Which grammatical elements are implicit?
15. How do word order and particles affect sentence meaning?

### Recurring patterns
16. Which words, roots and grammatical constructions occur most frequently?
17. Which patterns should learners study first?
18. Where can learners find other Quranic examples of a particular construction?

These are learning objectives, not a requirement to invent annotations absent from the source data.

## 6. Preliminary JSON structures

Morphology:

```json
{
  "metadata": {},
  "reference_data": {},
  "words": {
    "1:1:1": {},
    "1:1:2": {}
  }
}
```

Sentence grammar:

```json
{
  "metadata": {},
  "reference_data": {},
  "sentences": {
    "SOURCE_SENTENCE_ID_1": {},
    "SOURCE_SENTENCE_ID_2": {}
  }
}
```

These are preliminary structures. Final schemas must be based on actual source inspection.

## 7. Work completed so far

- Established the two-dataset architecture.
- Defined the distinction between word morphology and sentence syntax.
- Identified important preservation requirements.
- Identified the main learner-focused research questions.
- Proposed preliminary JSON structures.

**No datasets have been generated or validated yet.**

## 8. Immediate next steps

1. **Inspect the source files.** Locate and inspect the actual morphology, Treebank, reference dictionaries, normalized WBW data and existing processing scripts.
2. **Map source annotations.** Establish how morphology segments and Treebank segments map to complete written words and sentence IDs.
3. **Finalize both JSON schemas.** Define every field, data type, relationship, null policy and projection rule based on actual source data.
4. **Generate morphology JSON.** Preserve all original annotations and validate word coverage.
5. **Generate sentence grammar JSON.** Preserve original sentence boundaries, segment relationships and implicit nodes.
6. **Validate both datasets.** Check completeness, source traceability, word alignment, sentence boundaries and annotation preservation.

## 9. Deferred work

No CSV files should be generated during this phase. Possible later outputs include verb-form statistics, root and lemma statistics, POS sequence analysis, syntactic-function sequence analysis, greedy learning-priority rankings and syntax relationship summaries.

## Handoff instruction

Continue from source inspection, not from generating JSON immediately. Establish an accurate mapping between the original source annotations and the normalized written-word and sentence structures. Do not assume the illustrative schemas are final. Preserve every original annotation, document any derived fields, and validate the resulting datasets before considering the JSON work complete.
