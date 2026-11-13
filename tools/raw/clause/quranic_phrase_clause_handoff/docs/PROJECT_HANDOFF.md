# Project Handoff: Quranic Phrase & Clause Annotation

## 1. Project objective

Build a new, Quran-wide annotation dataset that identifies and classifies **phrases and clauses** while reusing existing Quranic linguistic datasets as immutable reference sources.

The goal is not to merge EQTB and QAC into another copy of their data. The goal is to create the missing annotation layer and connect it to the existing sources through stable references.

The application should be able to present a unified linguistic view by resolving the relevant information from its original source datasets at query/display time.

## 2. Non-negotiable design principles

1. **Existing datasets remain unchanged and independently versioned.**
2. **Do not duplicate data that already exists.** This includes Quranic text, tokens, morphological features, roots, lemmas, POS tags, syntactic dependency records, codebooks, and lexicons.
3. **Reference rather than copy.** Store source dataset/version and stable source identifiers. Resolve text and linguistic features from the original source.
4. **Create only genuinely new information.** Our principal contribution is phrase identification/classification, clause identification/classification, and relationships not adequately represented in existing sources.
5. **Do not assume that a label means the same thing across annotation systems.** Preserve source-specific terminology and map to our own taxonomy only through documented, reviewed mappings.
6. **Preserve provenance.** Every annotation must be traceable to its source evidence, annotation version, and review history.
7. **Do not force a single label.** Structural type, grammatical function, speech act, and rhetorical function are separate dimensions and can overlap.
8. **Uncertainty is explicit.** Use pending/uncertain/rejected/reviewed statuses; do not present automatically generated candidates as gold annotations.

## 3. Linguistic levels

The intended working progression is:

### Existing level: word and morphology

Provided by reference datasets such as EQTB and QAC. We consume these resources; we do not rebuild them.

Examples of existing information: Quranic word/token identifiers, Arabic text, morphology, root, lemma, POS, grammatical features, and dependency relations.

### New level: phrase

Identify phrase spans and their internal relationships where the needed information is not already available in a source.

Candidate phrase types to investigate include noun phrase, prepositional phrase, adjective phrase, adverbial phrase, and verb phrase. This is an initial working list, not a final taxonomy. Traditional Arabic grammar does not always map one-to-one to phrase-structure categories used in modern linguistics.

### New level: clause

Identify clause spans and their relationships where these are not fully represented by existing source records.

Candidate constructions include nominal/verbal clauses, conditional constructions, relative clauses, circumstantial clauses, causal/purpose clauses, subordinate constructions, and others established by the final taxonomy.

### New annotation dimensions

For each phrase/clause, where relevant:

- structural type;
- grammatical/syntactic function;
- clause/phrase relationship to another unit;
- speech act (declarative, imperative, prohibition, interrogative, vocative, etc.);
- rhetorical/discourse function (emphasis, oath, warning, threat, promise, glad tidings, etc.).

These categories are not all at the same linguistic level. Keep dimensions separate and document overlaps.

## 4. Current source inventory

### EQTB

Main source: `Quranic.csv`.
Supplementary files supplied:

- `RelLabels.csv`
- `CAPoS.csv`
- `ConstituentsTags.csv`
- `CAMorphFeatures.xlsx` (13 worksheets)
- `CALemmaLexicon.csv`
- `CARootLexicon.csv`

The auxiliary files are codebooks/lexicons. They help interpret values in the main table; they are not six more token-level corpora to concatenate.

### QAC

Current integration used the Quranic Arabic Corpus morphology 0.4 export. It is a morphology source, not a full independent syntactic treebank in this project configuration.

QAC is a separate source. Its source records should be referenced, not copied into our new annotation dataset.

## 5. What has been done for Surah Al-Mulk (67)

The user successfully ran the earlier exploratory integration pipeline. The uploaded summary reports:

- EQTB source file: 139,376 total records; 583 records for Surah 67.
- QAC morphology export: 529 records for Surah 67.
- 529 exact Quranic-location matches.
- 54 EQTB implicit tokens without a real Quranic word location.
- 0 duplicate location keys after implicit tokens were excluded from direct coordinate matching.
- 116 EQTB constituent records: PP 50, NS 17, VS 44, SC 3, CS 2.
- 66 clause-like constituent candidates (NS + VS + SC + CS).
- 560 constituent-token memberships.
- 583 dependency records.
- 171 unique lemmas; all 171 found in the EQTB lemma lexicon.
- 128 unique roots; all 128 found in the EQTB root lexicon.

These numbers are from the user's supplied `dataset_summary_surah_67.json`.

### Important interpretation

- 529/529 QAC records match the coordinate-bearing EQTB records in this subset. The 54 implicit EQTB tokens do not have normal Quranic word coordinates and are not failed alignments.
- 116 is the number of constituent records, not the number of unique linguistic phrases/clauses after review.
- 66 is a candidate count, not 66 validated independent clauses.
- The 50 PP records are phrase-like constituents. NS, VS, CS, and SC are sentence/clause-like categories in this EQTB codebook. They should not all be treated as phrase types.
- Constituents can be nested and overlap. Do not flatten them.
- `constituents_loc` contains inclusive sentence-local token-id spans. The correct token lookup key is `(sentence_id, token_id)`, not Quranic word location alone.
- An EQTB sentence may cross an ayah boundary. Do not split sentence-level structures simply at verse boundaries.
- Implicit tokens such as `(هُوَ)` or `(*)` have no normal Quranic location and should remain source records, not be assigned invented word coordinates.

## 6. Earlier pipeline and its status

`prototype/build_surah_mulk_dataset.py` is an exploratory integration/inspection script. It reads EQTB, auxiliary codebooks and QAC morphology, decodes features, and exports enriched copies for analysis.

It is useful for understanding source schemas and validating mappings, but **it does not implement the newly agreed reference-only architecture**. Do not use its enriched output CSV files as the new annotation dataset.

A morphology mapping issue was identified and addressed in the later script:

- `_`, `-`, and blank placeholders should be counted as `missing`, not `unknown`.
- `MOOD:SUBJ` and `MOOD:JUS` are normalized to `SUBJ` and `JUS` for lookup only.
- `SP:kaAn`, `SP:<in~`, and `SP:kaAd` are normalized by removing `SP:` for lookup only.
- Original raw values must be preserved.
- The `VerbMood` sheet's English descriptions for JUS and SUBJ were reversed relative to the Arabic descriptions; the integration prototype corrects them for display.
- `RelLabels.csv`'s `rel_en` field contains relation codes, not ordinary English glosses. Do not fabricate English descriptions from that column.

The supplied production summary predates the user's rerun of the latest corrected pipeline. If morphology mapping audit figures matter, rerun the latest prototype and compare results; do not assume the uploaded summary includes those later fixes.

## 7. Critical architecture decision

Use three separate components:

**A. Reference data layer**

Original EQTB, QAC, and future sources. Read-only and independently versioned.

**B. Annotation layer (our new dataset)**

Only new phrase/clause units, boundaries not already adequately represented, relationships, classifications, evidence references, and review decisions.

**C. Application/query layer**

Resolves source references and annotations at runtime and presents them together without merging/copying the source datasets.

If a phrase/clause already exists completely in EQTB, reference that source constituent. Do not create a duplicate phrase/clause record merely to restate its label. If we add a new classification to an existing source entity, store only the new classification linked to that source entity.

If a boundary or relationship is absent or incomplete, create our own annotation unit and store only the minimum token-span references needed to identify it.

## 8. Next task

Do not immediately scale to all Quranic chapters. First refactor the prototype into source adapters and a reference resolver, then complete a small Surah Al-Mulk phrase-level proof of concept:

1. Load EQTB and QAC as read-only sources.
2. Enumerate source constituent/phrase records with source IDs and source spans.
3. Separate existing source entities from genuinely missing phrase annotations.
4. Define phrase-level annotation units without copying word text or morphology.
5. Preserve nesting and allow multi-segment spans.
6. Link every annotation to source token/constituent references.
7. Review sample phrases against Arabic grammatical references.
8. Only after phrase modeling is validated, move to clause spans and classifications.

See `ARCHITECTURE.md`, `ANNOTATION_MODEL.md`, `ROADMAP.md`, and the SQL proposal for implementation details.
