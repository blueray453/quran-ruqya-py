# Quran-wide Phrase & Chunk Dataset

**Release:** 1.0  
**Scope:** Quran-wide phrase, sentence-role, clause and repeated lexical chunk inventory for an English-first Quranic Arabic comprehension curriculum.

## 1. Why this dataset exists

This dataset is a curriculum-support and retrieval layer. It is not a new grammar syllabus and does not replace teacher-reviewed classical Arabic grammar.

Keep the teaching spine:

1. **Word:** Ism, Fi'l, Harf; then the four Ism properties.
2. **Phrase:** the six ILMHUB constructions.
3. **Sentence/clause:** nominal and verbal sentences, sentence roles, particles and subordinate/conditional clauses.
4. **Ayah comprehension:** assemble the units in their complete verse context.

The dataset deliberately separates three kinds of object that are often all called a “chunk”:

- **Source grammatical spans and relation-derived chunks:** spans or syntactic relations in the QAC-derived Treebank, with a conservative mapping into curriculum concepts.
- **Repeated lexical chunks:** repeated contiguous multiword strings. They are useful for vocabulary, recognition and memory practice, but repetition does not prove a grammatical phrase construction.
- **Navigation links:** member words, dependency edges, parent/child containment, and links to the curriculum concept map.

## 2. Curriculum alignment and guardrails

The learner-facing framework remains ILMHUB's **3–2–6**: three word classes (Ism, Fi'l, Harf), two principal sentence types (nominal and verbal), and six core phrase constructions. The dataset retains those six as the only core phrase-construction taxonomy:

| ILMHUB construction | Name in data | Conservative evidence used |
|---|---|---|
| Murakkab Tawsifi | `tawsifi` | QAC `Adj` relation where the head is nominal and dependent is adjective |
| Murakkab Idafi | `idafi` | QAC `Poss` relation; chains may appear as nested pairs |
| Murakkab Jarri | `jarri` | QAC `gen` relation governed by a preposition node; attached preposition prefixes remain segment-aware |
| Murakkab Ishari | `ishari` | Demonstrative linked to a definite noun/proper-noun target |
| Murakkab Atfi | `atfi` | Nominal coordination with an explicit conjunction node |
| Murakkab Badali | `badali_candidate` | Nominal `App` relations are candidates only; teacher review required |

Do not turn sentence roles, clause labels, or QAC constituent tags into additional phrase types. They are separate curriculum layers. In particular:

- `Fa'il`, `Maf'ul Bih`, `Na'ib al-Fa'il`, `Mubtada`, `Khabar`, `Ism Inna`, and `Khabar Inna` are sentence-role concepts.
- Relative, conditional, result and subordinate tags are clause concepts.
- `PP`, `NS`, `VS`, `SC`, `CS` and `S` are source-defined constituent types, not extra ILMHUB phrase constructions.
- MASAQ-style phrase function (external syntactic function) must not be conflated with the six constructions (internal phrase structure).
- Ism case is Raf'/Nasb/Jarr. The Mudari' verb has Raf'/Nasb/Jazm. Madi and Amr are Mabni. Jarr is not a verb mood and Jazm is not a noun case.
- Current ILMHUB DiGNI labels are the course-facing four Ism properties: definiteness, gender, number and I'rab. Bayyinah Ch.3 wording “qism/type” should not be silently equated with definiteness without expert crosswalk.

The Bayyinah Nahw sequence is supported without reorganising it: Ch.1 word classes; Ch.2 I'rab, pronouns, jarr and Idafah; Ch.3 gender and number; Ch.4 descriptive, demonstrative and conjunctive structures; Ch.5-6 nominal/verbal sentence work; Ch.7 Mudari' and governing particles; Ch.8 passive voice; Ch.9 negation; Ch.10 Kana and sisters; Ch.11 compound Ism and An/sisters. Sarf remains a parallel morphology layer (verb forms, weak verbs, derived forms, verbal nouns/participles, plural patterns).

The supplied Arabic101 85% book is used only for the high-level principle of frequency-led vocabulary sequencing and review. Its supplied copy is marked personal-use-only / not for sale or distribution. No protected word lists or pages are reproduced here, and the book itself is not included in this package.

## 3. Files and layers

### Source inputs (`data_sources/`)

These are frozen normalized data inputs required by the build script:

- `indopak-nastaleeq-wbw-grammar-normalized.json` — whole-word Quran text, ordered word positions, word morphology segments and lexical metadata.
- `indopak-nastaleeq-sentence-grammar-normalized.json` — Treebank sentence records, syntax nodes, dependency relations and constituent spans.
- `quran-phrases-annotation.json` — normalized repeated lexical n-gram types and their locations.
- `quran-phrases-exact-diacritics-annotation.json` — exact-diacritic repeated lexical n-gram types and their locations.

`source_manifest.csv` records SHA-256 hashes and byte sizes for the four inputs. If you replace a source file, rerun the build and retain the updated manifest with that release.

### Generated outputs (`output/csv/`)

| CSV | Row unit / purpose |
|---|---|
| `quran_chunk_occurrences.csv` | One row per explicit source constituent or selected dependency-derived teaching chunk |
| `quran_chunk_members.csv` | One row per written-word member within a chunk, with segment-level POS, morphology, gloss, lemma/root and verb/noun features |
| `quran_dependency_edges.csv` | Overt source dependency edges used for auditing and alternate analyses |
| `quran_chunk_curriculum_links.csv` | Many-to-many links from chunk ID to curriculum concept ID |
| `quran_chunk_hierarchy.csv` | Strict span-containment parent/child links; containment does not itself prove grammatical dependency |
| `quran_chunk_type_frequency.csv` | Family, construction and source-tag occurrence/ayah/surah counts |
| `grammatical_chunk_pattern_frequency.csv` | Repeated text patterns within grammar-derived families, with evidence status retained |
| `six_core_phrase_pattern_summary.csv` | Summary for the six ILMHUB constructions |
| `repeated_lexical_chunk_types.csv` | Repeated contiguous lexical types (2+ words, repeated at least twice), normalized and exact-diacritic modes kept separate |
| `repeated_lexical_chunk_occurrences.csv` | Every retrieved occurrence of those repeated lexical types |
| `curriculum_concept_map.csv` | Lesson/concept IDs, teaching use and source alignment |
| `source_alignment_audit.csv` | Explicit curriculum crosswalk and decisions |
| `teacher_review_queue.csv` | Ambiguous and non-confirmed candidates; not ready for automated answer keys |
| `dataset_summary.csv` | Build population and category totals |
| `data_dictionary.csv` | Definitions and row units for key CSVs |
| `source_manifest.csv` | SHA-256 and byte-size manifest for the four input JSONs |

### Reports (`output/reports/`)

- `curriculum_alignment_and_chunk_dataset.docx`
- `curriculum_alignment_and_chunk_dataset.pdf`

The DOCX/PDF report is generated **from the CSV outputs only**. You may edit a CSV and regenerate the report without reprocessing the source JSONs.

## 4. Rebuild

Python 3.10 or later is recommended.

Install the report dependency:

```bash
python -m pip install -r requirements.txt
```

Run the complete pipeline:

```bash
python run_pipeline.py
```

Or run the two stages separately:

```bash
python scripts/build_phrase_chunk_dataset.py
python scripts/build_curriculum_audit_report.py
```

The phrase/chunk CSV builder uses Python's standard library. `python-docx` is required only to generate the DOCX report. If LibreOffice (`soffice`) is installed, the wrapper can also export the reports to PDF.

Custom paths:

```bash
python scripts/build_phrase_chunk_dataset.py \
  --data-dir data_sources \
  --out-dir output/csv

python scripts/build_curriculum_audit_report.py \
  --csv-dir output/csv \
  --output output/reports/curriculum_alignment_and_chunk_dataset.docx
```

## 5. Snapshot size and current extraction counts

The current source snapshot has:

- 77,432 whole-word positions;
- 11,693 Treebank sentence records;
- 26,463 source constituent spans;
- 95,749 grammar/constituent chunk occurrences (source constituents plus selected relation-derived units);
- 207,074 member-word rows;
- 88,170 exported overt dependency edges;
- 25,188 normalized repeated lexical chunk types and 23,555 exact-diacritic types;
- 150,935 repeated lexical occurrence rows across both matching modes;
- 62,901 strict containment links;
- 237,006 chunk-to-curriculum links;
- 2,790 rows in the teacher-review queue.

Six-construction snapshot:

| Construction | Observed occurrences | Unique ayahs | Unique surahs | Qualification |
|---|---:|---:|---:|---|
| Tawsifi | 1,542 | 1,347 | 98 | Direct nominal `Adj` relation; not manually checked case-by-case |
| Idafi | 9,149 | 4,171 | 112 | `Poss` relation; nested chains can contribute multiple pairs |
| Jarri | 12,952 | 4,984 | 114 | Preposition-governed `gen`; includes attached preposition segments |
| Ishari | 71 | 70 | 39 | Demonstrative linked to definite noun/proper-noun target |
| Atfi | 2,573 | 1,796 | 101 | Nominal coordination with explicit conjunction node |
| Badali candidate | 457 | 504 | 90 | Candidate only; App can represent broader apposition; teacher review required |

Counts are for this QAC-derived annotated snapshot and these operational rules. They are **not** a claim that every occurrence of every classical Arabic construction has been exhaustively and correctly annotated across the Quran. Ayah incidence can exceed occurrence count when an annotation relation crosses ayah boundaries; `crosses_ayah` and member positions are retained to audit this.

## 6. Interpretation and quality safeguards

1. **Do not conflate row units.** A written word, a prefix/stem/suffix segment, a source constituent, a dependency edge and a repeated n-gram are different units.
2. **Do not equate lexical repetition with grammar.** A repeated two-word string may be a useful learning chunk without being a complete Murakkab Tamm or one of the six constructions.
3. **Do not overstate source tags.** The Treebank is syntactic evidence. The learner-facing pattern names are a carefully mapped layer, not labels supplied directly for every occurrence by a grammarian.
4. **Badali remains a review queue.** The source `App` relation is broader than the narrowly taught substitution construction.
5. **Ishari filtering is intentional.** A demonstrative followed by an indefinite target is not automatically a phrase; ILMHUB explains that the interpretation may instead be a complete nominal sentence.
6. **Atfi filtering is intentional.** Verbal/clause coordination is retained separately rather than being counted as a nominal phrase construction.
7. **Morpheme boundaries matter.** A preposition or conjunction can be attached to a written word; use `quran_chunk_members.csv` and its segment IDs for morphology, while keeping the full written word for reading display.
8. **Review before teaching.** Use `teacher_review_queue.csv` for qualified Arabic grammar review before turning candidates into answer keys.

## 7. References and source provenance

See `SOURCES_AND_ALIGNMENT.md` for the source-by-source curriculum audit, web references and scope notes. The normalized QAC-derived source inputs are included directly, so the present chunk dataset can be regenerated without network access or external API calls.

Before redistribution or commercial deployment, check rights for Quran text editions, corpus glosses, QAC-derived annotations and each third-party data source. The user-supplied 85% guide is not redistributed here.
