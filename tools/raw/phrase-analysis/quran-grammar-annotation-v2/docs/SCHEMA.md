# Schema reference (v1.0.0)

Two canonical JSON files annotate the existing Quran text files. They are **annotation layers**: they never
change or re-define `indopak-nastaleeq.json` or `indopak-nastaleeq-wbw.json`.

| File | Records | Owns |
|---|---|---|
| `indopak-nastaleeq-wbw-grammar-normalized.json` | 77,432 written words, keyed `surah:ayah:word` | morphology |
| `indopak-nastaleeq-sentence-grammar-normalized.json` | 11,693 Treebank sentences, keyed by original sentence id | syntax and structure |

Each file is `{ "metadata": {}, "reference_data": {}, "words" | "sentences": {} }`.
Real examples: `docs/examples/`.

## 1. Principles

1. **Text authority.** Keys are the WBW keys. `metadata.text_authority` records the SHA-256 of the two Quran files the layers were built against.
2. **Every Treebank row is stored exactly once per layer that owns its columns.** Morphology columns live in the word layer, syntax columns in the sentence layer, pointers in both. `src/validate.py` rebuilds all 139,376 rows × 43 columns from the two files and compares them to `Quranic.csv`.
3. **Original vs derived.** Anything under a `derived` key, and the sentence-level `constituents` list, is computed by this project. Original annotations are never replaced.
4. **Whole written words only.** A written word is one position. Segments (prefix / stem / suffix) are never separate positions in a sequence.
5. **No invented grammar.** Nothing is filled in where the source is silent.

## 2. Null policy

A source value of `_` means "no value": the JSON key is **absent** (keeps the files compact).
Round trip: absent → `_`. One exception: in the source, `lemma_ar` / `root_ar` hold the placeholder `ـ` (tatweel) whenever `lemma` / `root` is absent; the placeholder is re-created on round trip and not stored.
Read optional fields with `.get()`.

## 3. Word layer

```
words["67:15:3"] = {
  wbw_id, text_indopak, text_normalized, text_exact, [restored_from],
  annotation_status,      // "annotated" | "absent_in_treebank" (3 words)
  sentence_id,            // sentence of the STEM segment; null if absent
  segments: [ ... ],      // original morphology, one per Treebank row
  derived: { ... },       // absent when there are no segments
  [secondary_db]          // values from word-stem/lemma/root .db, never overriding the Treebank
}
```

| Field | Meaning |
|---|---|
| `wbw_id` | `id` of the entry in indopak-nastaleeq-wbw.json |
| `text_indopak` | the WBW text, unmodified (authoritative for display) |
| `text_normalized`, `text_exact` | from indopak-nastaleeq-wbw-normalized.json |
| `restored_from` | present for the 2 words whose glyph is restored from `word-stem.db` (18:19:34, 73:20:8) |

### Segment (original annotation)

| Key | Source column | Notes |
|---|---|---|
| `treebank_tid` | `tid` | unique row id |
| `location` | `location` | `surah:ayah:word:segment` |
| `type` | `segment` | `PREFIX` / `STEM` / `SUFFIX` |
| `text_uthmani`, `uthmani_bw` | `uthmani_token`, `uthmani_unicode` | **Uthmani** spelling and Buckwalter. Not IndoPak: segments cannot be mapped onto IndoPak characters, so annotations attach at whole-word level only |
| `text_imlaai`, `imlaai_bw`, `phonetic` | `imlaai_token`, `imlaai_unicode`, `phonetic` | |
| `gloss` | `trans` | word-level gloss (present on 77,915 segments); not a contextual translation |
| `pos`, `pos_ar` | `pos`, `pos_ar` | Treebank POS (see §7 for 132 re-taggings vs v0.4) |
| `features_raw` | `features` | original feature string, e.g. `STEM\|POS:V\|PERF\|LEM:jaEala\|ROOT:jEl\|3MS` |
| `lemma`, `root` | `lemma`+`lemma_ar`, `root`+`root_ar` | objects `{bw, ar}` |
| `verb_form_raw` | `verb_form` | e.g. `(IV)`. Also present on some nouns/adjectives, see `derived.nominal_form_annotations` |
| `prefix`, `suffix` | `prefix`, `suffix` | morpheme tags, e.g. `l:P+` |
| `aspect`, `voice`, `mood` | `verb_aspect`, `verb_voice`, `verb_mood` | mood values are written `MOOD:JUS` / `MOOD:SUBJ` |
| `state`, `case`, `derived_noun`, `special_group` | `nominal_state`, `nominal_case`, `derived_nouns`, `special_group` | |
| `person`, `gender`, `number` | same | |
| `syntax_ref` | `sentence_id`, `token_id` | pointer to the node in the sentence layer that owns the relation and head |

### `derived` (word)

| Key | Rule |
|---|---|
| `is_verb` | true if a STEM segment has POS `V`. Nouns/adjectives carrying a verb-form annotation are **not** verbs |
| `verb_forms[]` | one per verb stem: `{segment, value, basis}`. `basis: "explicit"` when the Treebank gives the form; `"inferred"` → Form **I**, the default stated in `CAMorphFeatures.xlsx`. Form I is never explicit in the source (12,347 inferred) |
| `nominal_form_annotations[]` | non-verb STEM segments with a form annotation (1,968); kept apart from verbs |
| `derived_nouns[]` | `{segment, pos, type}` for ACT_PCPL / PASS_PCPL / VN annotations |
| `prefix_tags`, `suffix_tags`, `n_segments` | convenience |
| `neighbors` | previous / next written word in the same ayah (`null` at the ends) |
| `projections` | whole-word labels joined with `+` in segment order: `pos_stem`, `pos_all_segments`, `function_all`, `function_without_NonRel`, `function_stem` |

Choosing a projection is an analysis decision, so all are stored. `pos_stem` has 54 distinct values, `pos_all_segments` 359; stem-only hides prefix particles (the preposition in `بِسْمِ` is a PREFIX, so the word is just `N`). `function_without_NonRel` drops the `NonRel` markers carried by prefixes such as ال; a word whose only label is `NonRel` keeps `NonRel`.

## 4. Sentence layer

```
sentences["10846"] = {
  sentence_id,
  span: { first_word, last_word, ayahs: [], crosses_ayah },
  words: [ "67:15:1", ... ],     // written words in text order, each word in exactly one sentence
  nodes: [ ... ],                // every Treebank row of the sentence, in original order
  constituents: [ ... ],         // word-id view of the source spans
  derived: { ... }
}
```

### Node (one per Treebank row; `token_id` = its index in the sentence)

| Key | Meaning |
|---|---|
| `token_id`, `treebank_tid`, `sentence_word` | pointers / original ordering columns |
| `implicit` | `true` for rows with no Quranic word location (11,157, e.g. an unspoken subject) |
| `word`, `segment` | the word key and segment location (`null` / absent for implicit nodes) |
| `pos` | copy of the segment's POS (validated equal); implicit nodes carry full `morphology` instead |
| `word_in_sentence` | present when the word is assigned to another sentence (see §6) |
| `rel`, `rel_ar` | `rel_label`, `rel_label_ar` (syntactic function, kept separate from POS) |
| `head` | `ref_token_id`, the token this node depends on. A root node or `NonRel` node points to itself |
| `is_constituent`, `constituents_loc`, `constituents_text`, `constituent_label` | original constituent columns; `constituents_loc` is `[a-b]` over `token_id` |
| implicit only: `chapter_id`, `verse_id`, `word_id`, `tok_id`, `anchor{after_word, before_word}`, `morphology{}` | `anchor` lets a UI place the unwritten element without touching the Quran text |

### `constituents[]` (derived from node spans)

`{tag, token_span, source_token_id, first_word, last_word, words[], text}`. Tags: `NS` nominal sentence, `VS` verbal sentence, `CS` conditional sentence, `PP` prepositional phrase, `SC` subordinate clause, `S` (see `reference_data.constituent_tags`). The original span stays on the node.

### `derived` (sentence)

`word_count`, `node_count`, `implicit_node_count`, `is_prefix_only_fragment`, `split_words[]`, `root_nodes[]` (nodes with relation `root`), `pos_sequence{stem, all_segments}`, `function_sequence{all, without_NonRel, stem}`.
Sequences list one label per written word and never cross a sentence boundary.
A sentence "type" (nominal/verbal) is **not** derived: the Treebank annotates it only through constituent tags, and the outermost tag does not always cover the whole sentence.

## 5. Reference data

Word file: `pos`, `features` (every sheet of `CAMorphFeatures.xlsx`: `columns`, `entries` by tag, raw `rows`), `verb_forms`, `verb_moods`, `roots`, `lemmas` (the two lexicons), `corrections`.
Sentence file: `pos`, `relations` (140 labels with Arabic names), `constituent_tags`.

**Corrections.** The supplied feature guide has 7 errors in its English descriptions, kept verbatim as `source_description_en` with a corrected `description_en` and a flag:
verb-form ordinals for V, VI, VII, VIII, IX are off by one or more (the tag `(IX)` and the Arabic pattern say ninth, the text says "Fifth form"), and the mood descriptions for `JUS` and `SUBJ` are swapped. Data columns are never altered.

## 6. Sentences vs written words

* 41 written words have segments in two adjacent sentences (prefixes in the earlier one). Each word is assigned to the sentence of its stem so a word is never split in a sequence; every segment keeps its own sentence id in `syntax_ref`, and the node carries `word_in_sentence`.
* 26 of the 11,693 sentences contain only such prefix segments (`is_prefix_only_fragment`). They are kept (ids and boundaries preserved) but own no written word; ids are in the sentence file's `metadata.source_issues`.
* 836 sentences cross an ayah boundary (up to 31 ayahs). Never assume one ayah = one sentence.

## 7. Known source issues (reported, never silently fixed)

| Issue | Handling |
|---|---|
| 3 written words absent from the Treebank and from morphology v0.4: `2:181:14`, `8:6:12`, `13:37:20` | records with `annotation_status: "absent_in_treebank"`, no segments |
| 132 segments where the Treebank `pos` differs from the POS in v0.4 (e.g. `N→T`, `CONJ→REM` ×47, `ADJ→N` ×17); `features_raw` keeps the v0.4 tag | Treebank `pos` is stored; all 132 locations listed in `metadata.source_issues` |
| `rel_label_ar` on 666 rows and `pos_ar` on 10,021 rows differ from the lookup tables | row values kept as given |
| word-level `.db` lemma/root differ from the Treebank for some words (lemma: 7,056 words, root: 343, including words where the Treebank has none) | `secondary_db` stored separately; Treebank is never overridden |
| 5 feature-guide verb-form descriptions and 2 mood descriptions are wrong | see §5 |

## 8. Not in the data (do not expect it)

The source has no explanation text for why a case applies, no description of what a particle does to the meaning, no contextual translation beyond the word gloss, and no sentence-level verbal/nominal label. These can be *derived* from relation + head + case (e.g. a pronoun with `rel: gen` depending on a `P` node is genitive because a preposition governs it), but the files do not claim them as annotations.

## 9. Sequences and learning order

`python3 src/generate_sequences.py` writes the grammar equivalents of `quran-phrases.csv` to `output/sequences/`, from the two JSON layers only
(columns and options: README). Definition: consecutive complete written words inside one sentence, never across a sentence boundary, kept when
they occur at least twice, `total = stand_alone + inside_longer`; POS and function sequences are separate. Annotation JSON occurrence encoding:
`occurrences` and `stand_alone_occurrences` are start positions `s` into `word_index`; a unit of length `n` covers `word_index[s : s+n]`
and `sentence_index[s]` is its sentence id.

Measured on this data (share of word positions inside a repeated sequence of length >= L):

| projection | L=2 | L=3 | L=5 | L=8 | longest repeated |
|---|---|---|---|---|---|
| `pos_stem` | 99.3% | 96.1% | 73.3% | 16.2% | 29 |
| `pos_all_segments` (default) | 98.4% | 90.0% | 34.1% | 5.3% | 29 |
| `function_without_NonRel` (default) | 97.6% | 87.1% | 31.9% | 4.4% | 29 |

Because label alphabets are small, nearly every short sequence repeats. The original greedy algorithm (`--greedy-min-len 1`) therefore ranks
single labels first (the first 10 POS units cover 63% of the Quran). Use `--greedy-min-len 3` or higher for a learning order with information.
