# MERGED PROJECT HANDOFF — Quran Clause & Phrase Dataset

**Version 1.0 (merge edition).** This document supersedes both earlier handoffs:

- Package A: `quranic_phrase_clause_handoff/` (reference-only annotation architecture, EQTB + QAC)
- Package B: `mulk-dataset/` with `HANDOFF.md` (Al-Mulk clause/phrase dataset with English + Bangla)

A fresh session should read this document top to bottom and start work at the Roadmap (§10). It contains everything needed to continue without either original chat history.

---

## 1. Project goal (merged statement)

Build **one** Quran-wide clause/phrase annotation project that serves two coordinated purposes from a single canonical store:

1. **Reader layer (Package B's mission).** Segment every ayah into **clauses** and **phrases** — minimal semantic building blocks that make natural sense — with **English and Bangla for every phrase**, such that joining the phrases of a clause in Arabic word order reads naturally in both languages. The dataset must support mining of **repetition frequencies and segmentation rules** afterwards.
2. **Linguist layer (Package A's mission).** Attach, as an overlay, **phrase/clause classifications** (structural type, grammatical function, speech act, rhetorical function) and typed relationships, with **full provenance**: every unit traceable to immutable source records, every classification carrying evidence and review status.

**Pilot:** Surah 67 (Al-Mulk). **Target:** the whole Quran — 6,236 ayahs, 77,432 QPC words, 114 surahs.

Example of the core idea (67:15):
هُوَ ٱلَّذِي | جَعَلَ لَكُمُ ٱلۡأَرۡضَ ذَلُولٗا | فَٱمۡشُواْ فِي مَنَاكِبِهَا | وَكُلُواْ مِن رِّزۡقِهِۦ | وَإِلَيۡهِ ٱلنُّشُورُ
→ "He is the One who" / "made the earth manageable for you," / "so walk through its regions" / "and eat from His provision;" / "and to Him is the resurrection."

---

## 2. Settled decisions — do NOT re-litigate

| # | Decision | Origin |
|---|---|---|
| 1 | **Hybrid storage.** Canonical annotation store (SQLite) holds only genuinely new annotations plus source references. Per-surah JSON exports with inline morphology are rebuildable rendered views, explicitly marked as cache. | Merge session (user) |
| 2 | **Package B's tiling segmentation is the base unit model**; Package A's classification dimensions are an optional overlay on the same units. | Merge session (user) |
| 3 | **Status vocabulary: candidate / pending / reviewed / accepted / uncertain / rejected** (Package A's six states). B's three states map into them (Appendix A). | Merge session (user) |
| 4 | **Both source families are canonical references**: QUL for text/translations/glosses/morphology; EQTB (treebank) for constituents, sentence ids, relations; QAC morphology as cross-check. | Merge session (user) |
| 5 | **First build step: source registry + read-only adapters.** | Merge session (user) |
| 6 | JSON only for authoring and exports (CSV dropped). One nested JSON per surah; analysis flattens with pandas in memory. | B |
| 7 | Source priority: QUL first, Quranic Treebank second. GPL licence is acceptable to the user. | B |
| 8 | Bangla reference = Zakaria (`bn-dr-abu-bakr-muhammad-zakaria-simple.json`, respectful আপনি). Rawai al-Bayan dropped (uses তুমি). | B |
| 9 | Bangla phrases follow Arabic word order; no separate Bangla reading order. | B |
| 10 | **Annotation must be independent of rules** (anti-circularity). The annotating model sees only Arabic words, word glosses, the two reference translations, CONVENTIONS.md and a glossary — never tags, sentence ids or mined rules. Tags/ids attach afterwards; rules are mined only after the dataset exists. Translation memory may FLAG conflicts only, never auto-fill. | B |
| 11 | **Reference, never copy** (Package A's central rule, now governing the canonical store): existing datasets are immutable and independently versioned; no Arabic text, tokens, morphology, roots, lemmas, POS, dependencies, codebooks or lexicons are stored in the canonical annotation store; source values resolve at render/runtime. | A |
| 12 | Never force a single label: structural type, grammatical function, speech act and rhetorical function are separate, overlapping dimensions. | A |
| 13 | Uncertainty is explicit: automatically generated candidates are never exposed as gold annotations. | A + B |
| 14 | QPC word keys (`s:a:w`) are the canonical word identifiers for the whole project. Never tokenize QPC text by whitespace (37:130:3 contains a space inside one word). | B (promoted in merge) |
| 15 | Dropped: QSU (too coarse; kept finding: it split at waqf ۚ 5/6 but ۖ 0/9), recitation timings (reciter-dependent), dependency-relation storage (deferred), the `mustafa0x` morphology fork (replaced by converted treebank JSON). | B |
| 16 | User has an OpenRouter API key; generation pipeline uses it. | B |

Decisions that were **proposed but unconfirmed in B** and are now resolved by this merge: (B) word-range IDs — **adopted**, see §5.4; (C) per-ayah status — **adopted**, using the merged vocabulary; (E) per-surah key-alignment validation — **adopted** as Phase 1 exit criterion; (F) CONVENTIONS.md as shared memory — **kept**; (A) flat JSONL per level — **deferred** to Phase 2 (cheap to generate from the canonical store on demand). `waqf_strength` field (ۚ major vs ۖ minor) — **still open**.

---

## 3. Architecture (hybrid storage)

```text
        +----------------------------------------------------------+
        |            Application / query / analysis layer          |
        |   reader views            |        mining (pandas)       |
        +--------+--------------------------+----------------------+
                 | resolve refs on demand   | flatten cached exports
        +--------v-----------+    +---------v----------------------+
        | CANONICAL STORE    |    | RENDERED EXPORTS  (cache)      |
        | SQLite             |    | per-surah JSON, flat JSONL     |
        | new units + refs   |    | built by build_dataset.py      |
        | only               |    | rebuildable, never authoritative|
        +--------+-----------+    +---------^----------------------+
                 | source refs                  | render
        +--------v------------------------------+------------------+
        |   Source registry (key, version, checksum) + adapters    |
        |   read-only; resolvers: QPC key <-> EQTB <-> QAC          |
        +--------+---------------+----------------+-----------------+
                 |               |                |
        +--------v------+ +------v------+ +-------v--------+ +------------------+
        | QUL files     | | EQTB        | | QAC morphology | | Mutashabihat /   |
        | (text, trans, | | Quranic.csv | | 0.4 (cross-    | | matching-ayah    |
        | glosses, morph)| | + 6 aux     | | check)         | | (repetition QA)  |
        +---------------+ +-------------+ +----------------+ +------------------+
```

Rules:

1. **Canonical store = the released annotation dataset.** It contains: new phrase/clause units, their token-span references, phrase translations (en/bn — genuinely new content), classifications, relationships, evidence, reviews, and the glossary. It contains **no** word text, morphology, roots, lemmas, POS, dependency edges, ayah translations, glosses or codebook rows — those resolve through adapters.
2. **Rendered exports = cache.** Package B's `data/mulk.json` shape stays as the reader format, but morphology/glosses/translations arrive resolved from sources at build time, and the file header records the source versions + checksums used. Any cache must be rebuildable from store + sources alone.
3. **Phrase translations live in the canonical store** (they are our new annotation). Full-ayah translations (Sahih, Zakaria) and word glosses are **source content** — referenced by key, resolved at render.
4. If a phrase/clause already exists exactly as an EQTB constituent, **reference that constituent** (`exact_entity` role) instead of creating a duplicate unit. Create new units only for genuinely missing boundaries/relationships; store minimum token-span references only.
5. Source reference = `source_dataset_key` + `version` (+ checksum where possible). A changed release must never silently repoint to different records.

---

## 4. Annotation model

### 4.1 Base layer — tiling segmentation (Package B)

Definitions (from `CONVENTIONS.md`, kept verbatim in Package B):

- **Phrase**: smallest run of consecutive Arabic words forming a natural, meaningful unit (not a word-by-word gloss). Keep together what only makes sense together (preposition + noun, possessive construction, verb + attached pronoun, fixed expression).
- **Clause**: consecutive run of phrases forming a clause-sized idea (statement, condition, result, relative clause, question, command, quoted speech act). Decide by meaning, not length.
- **Tiling**: phrases cover words 1..N of the ayah exactly once, in order, no gaps/overlaps; clauses tile the ayah the same way. Phrases always follow Arabic word order.

Each base unit stores: internal ID, level (`phrase`/`clause`), word-span (QPC keys), English + Bangla translation, normalized `translation_key` (lower-case, no punctuation, referent-neutral — e.g. "and it is" → key "and he is" when the referent is Allah), source evidence references, annotator/version/status.

Translation consistency rules (from B, already applied on Al-Mulk): same Arabic phrase → same English and Bangla wording and same `translation_key`, unless the referent genuinely differs. Known normalizations: فَسَتَعْلَمُونَ → "So you will soon know"; فَمَن → "who then"; إِنَّهُ → "Indeed, He is"; وَهُوَ in 67:4 stays "and it is" (refers to the vision) but shares key "and he is".

### 4.2 Overlay layer — linguistic classifications (Package A)

Optional per-unit classifications across six dimensions: `phrase_structure`, `clause_structure`, `grammatical_function`, `speech_act`, `rhetorical_function`, `discourse_function`. Typed relationships (`condition_of`/`result_of`, `subordinate_to`, `relative_clause_of`, `coordinates_with`, …) link units — never encode a relationship as a label on one unit. For a conditional construction, condition and result are separate clause units linked by a condition-result relationship; an EQTB CS span covers the larger construction and does **not** automatically supply both child spans.

Reuse-vs-create rule (A §7, binding): (1) search sources for the same entity/span and meaning; (2) if it exists and is adequate → reference it, do not recreate; (3) if the entity exists but the classification is new → attach only the classification to the source reference; (4) if boundary/entity/relationship is missing → create a new unit with token-span references; (5) ambiguous source meanings keep their source-specific label with any crosswalk marked provisional.

Nesting/overlap policy: the reader layer is flat tiling by design. Nesting, overlap and multi-segment spans live in the overlay and in source constituents (EQTB constituents nest and overlap — never flatten them), resolved at runtime. Cross-ayah sentences: EQTB `sentence_id` can span verses — do not split sentence-level structures at ayah boundaries.

### 4.3 Status vocabulary (canonical)

`candidate` (auto-generated, unreviewed) → `pending` (awaiting review) → `reviewed` (checked) → `accepted` (part of released set); plus `uncertain` (plausible, unresolved) and `rejected` (reviewed, not accepted). A candidate must never be exposed as a verified gold label. Statistics and rule-mining use `reviewed`+`accepted` only. Mapping from B's statuses in Appendix A.

### 4.4 Identifiers

- **Word**: QPC key `s:a:w` (77,432 words; the last key of each ayah in `qpc-hafs-word-by-word.json` is the end-of-ayah marker, not a word).
- **Unit IDs (canonical, adopted from B's proposal):** `{surah}:{ayah}:{level}{start}-{end}` — e.g. phrase `67:15:p3-6`, clause `67:15:c3-9`. Cross-ayah overlay spans (e.g. rhetorical units): `{s}:{a}:{level}{start}-{s2}:{a2}:{end}`. The legacy `c2`/`p1` counters remain as display labels.
- **Source record keys**: EQTB token `tid` and `(sentence_id, token_id)`; EQTB constituent = `sentence_id` + inclusive `constituents_loc` token range; QAC location `s:a:w:segment`; QUL = file + key. Every stored reference also carries `source_dataset_id` (key + version).

---

## 5. Sources (canonical references)

| Source | File(s) | Role |
|---|---|---|
| QUL word list | `quran-script/wbw/qpc-hafs-word-by-word.json` | Master word list: keys `s:a:w`, QPC Hafs text, waqf marks. **Authority on word counts.** |
| QUL ayah text | `quran-script/… digital-khatt-v2` | Ayah text for display |
| QUL translations | `en-sahih-international-simple.json`; `bn-dr-abu-bakr-muhammad-zakaria-simple.json` | Reference ayah translations (en; bn with আপনি) |
| QUL word glosses | `english-wbw-translation.json`; `bangali-word-by-word-translation.json` | Drafting hints for the annotating model only |
| QUL morphology | `grammar/word-root.db`, `word-lemma.db`, `word-stem.db` | Root/lemma/stem (join `*_words.word_location` to the id table) |
| EQTB main | `Quranic.csv` (~50 MB, UTF-16, TAB) — data.mendeley.com/datasets/rk96pn66m4/1, github.com/NoorBayan/Quranic | Constituents, sentence ids, dependency relations; 139,376 rows; fields incl. `tid, sentence_id, token_id, location, uthmani_token, pos, features, lemma, root, rel_label, ref_token_id, is_constituent, constituents_loc, constituent_label` |
| EQTB aux (in Package A) | `RelLabels.csv` (140), `CAPoS.csv` (45), `ConstituentsTags.csv` (6), `CAMorphFeatures.xlsx` (13 sheets), `CALemmaLexicon.csv` (4,833), `CARootLexicon.csv` (1,643) — all UTF-16 TAB | Codebooks/lexicons to interpret values; not six more corpora |
| QAC morphology | `quranic-corpus-morphology-0.4.txt` | Independent morphology cross-check; locations `s:a:w:segment` |
| Treebank JSON | `quranic-treebank/data/surah-NNN.json` (converted by `convert_treebank.py`, QPC-keyed) | Tags, sentence ids, constituent spans for the build |
| Mutashabihat | `Mutashabihat ul Quran/phrases.json` + `phrase_verses.json`; `matching-ayah.json` | Repetition cross-check |
| QUL metadata | `metadata/quran-metadata-ayah.json` | **`words_count` is WRONG for 37:130** (counts 4; QPC/treebank 3) — do not rely on it |

Licensing: EQTB's software licence does not establish the licence of its data files; QAC has specific data-use requirements; QUL terms at qul.tarteel.ai. Verify all before any redistribution; keep licence metadata in the source registry. The annotation layer's own licence is chosen independently after that review.

Not included in either package (supply from original downloads): full `Quranic.csv`, `quranic-corpus-morphology-0.4.txt`.

---

## 6. Data gotchas — merged, complete

### 6.1 From Package B (scaling gotchas)

1. QPC writes بَعۡدَ مَا as 2 words in **2:181, 8:6, 13:37**; the treebank merges it into 1 word (all later treebank words in those ayahs number one lower). `convert_treebank.py` fixes this via the ALIGN table; output keys = QPC keys; asserts 77,432 words; `--qpc FILE` checks every ayah. The English/Bangla gloss files keep QPC keys but lack the 3 second-part entries.
2. **37:130:3** `إِلۡ يَاسِينَ` is ONE QPC word containing a space — never tokenize QPC text by whitespace; use word keys.
3. English WBW has 83,665 keys = 83,668 QPC keys (77,432 words + 6,236 end markers) minus the 3 missing second parts. Bangla gloss file lacks end-marker key 2:181:15 (harmless). Bangla glosses contain stray quotes and informal forms — drafting hints only.
4. QUL vs QAC roots: 0 disagreements on 209 words (Surah 67; compare after removing spaces, treating ا/أ/ء alike). Lemmas differ on 28 (mostly spelling: dagger alif, رَءَا vs رَأَى, هَٰذَا vs ذا); 3 words have no QUL lemma (67:8:9, 67:19:9, 67:23:10); 3 أَمَّنۡ words lemmatised مِن by QUL vs أَم by QAC (67:20:1, 67:21:1, 67:22:7). Keep `qac_lemma` for comparison.
5. Treebank/QAC English descriptions in the VerbMood and VerbForm sheets of `CAMorphFeatures.xlsx` are wrong — do not use them.

### 6.2 From Package A (EQTB structure facts)

6. `constituents_loc` values like `[3-18]` are **inclusive, sentence-local `token_id` ranges**; the lookup key is `(sentence_id, token_id)`, not Quranic location alone. `tid` also exists and can be retained as an additional record identifier.
7. An EQTB sentence may cross an ayah boundary — never split sentence-level structures at verse boundaries.
8. Implicit tokens (54 in Surah 67) have `sentence_word = 0`, `location = _`, surface placeholders like (هُوَ) or (*). They are legitimate source records with **no** Quranic word coordinates — never invent coordinates for them; exclude from direct QAC matching.
9. EQTB constituent tags: PP, NS, VS, SC, CS (+ S in the codebook). **PP is phrase-like; NS/VS/CS/SC are sentence/clause-like** — never treat them all as phrase types. Constituents nest and overlap — do not flatten. 116 ≠ number of reviewed phrases; 66 clause-like candidates ≠ 66 validated clauses.
10. `RelLabels.csv`'s `rel_en` column contains relation **codes** (cond, rslt, circ…), not English glosses — use `rel_ar` for the Arabic description and preserve the source code.
11. The VerbMood sheet's English descriptions for JUS and SUBJ are reversed relative to the Arabic — correct for display only, preserve raw values.

### 6.3 Feature-reading rules (apply to QAC/EQTB adapters)

- `_`, `-`, blank placeholders count as **missing**, not unknown.
- `MOOD:SUBJ`/`MOOD:JUS` normalize to `SUBJ`/`JUS` for lookup only; `SP:kaAn`, `SP:<in~`, `SP:kaAd` lose the `SP:` prefix for lookup only.
- Original raw values are always preserved; lookups never mutate sources.

### 6.4 Surah 67 alignment facts (from A's production run)

529/529 QAC rows match coordinate-bearing EQTB rows exactly; 54 EQTB implicit tokens excluded from direct matching; 0 duplicate location keys. 116 constituents (PP 50, NS 17, VS 44, SC 3, CS 2), 560 constituent-token memberships, 583 dependency rows, 171/171 lemmas and 128/128 roots found in the EQTB lexicons (membership is a lookup check, not proof of linguistic correctness).

---

## 7. Annotation process

### 7.1 Generation (OpenRouter pipeline — B's engine, kept)

`generate_spec.py` batches ~350 words per call, writes per-surah `annotations/surah-NNN.json` (`{"surah", "ayahs": {a: clauses}, "status": {a: {status, warnings, model, prompt_hash, depth}}}`), validates every reply (tiling, JSON shape, quotes, scripts), retries failures, marks survivors `needs_human`, logs token usage to `annotations/usage.jsonl`, and is resumable (done ayahs skipped). **Tested offline only — no live API call has ever been made.**

### 7.2 Anti-circularity (binding)

The annotating model sees only: numbered Arabic words, word glosses (en/bn), the two reference translations, `CONVENTIONS.md`, `glossary.json`. It never sees tags, sentence ids, constituent spans or mined rules. Tags and sentence ids attach afterwards through adapters into the canonical store's evidence/reference tables. Rules are mined only after the dataset exists. Translation memory flags conflicts only.

### 7.3 Review workflow (merged)

Generator output enters the canonical store as `candidate` (or `pending` if validation failed). Human review promotes `reviewed`; accepted releases mark `accepted`; unresolved items become `uncertain`/`rejected`. Full-Quran run: review all flagged ayahs + ~5% random sample. Bangla requires review by a Bangla reader (known draft issues: 67:3 verb-first negative; 67:20 clumsy; 67:15 and 67:8 stiff Arabic order; 67:4:1 كَرَّتَيْنِ "দুইবার" vs Zakaria "দ্বিতীয়বার"; وَهُوَ is "আর তিনি" everywhere except 67:4 "আর তা হবে" — English aliases it, Bangla alias still missing).

### 7.4 Cross-checks / QA harness (merged)

1. Treebank cross-checks: sentence-start vs clause-start disagreements; PP spans split by phrase boundaries (Al-Mulk baseline: 53/54 agreement, 0/50 PP split, one disagreement at 67:23:11 — treebank starts a sentence at مَّا تَشۡكُرُونَ where the annotation kept قَلِيلٗا مَّا as one phrase; adjudicate during the overlay PoC).
2. Same-Arabic-different-`translation_key` flags.
3. Mutashabihat comparison, sequence-based (repetition counting must use **sequences of consecutive phrases**, e.g. 67:25 words 1-4 repeat in 6 surahs but span 3 annotation phrases — not only whole phrases).
4. Tiling asserts + QUL-vs-QAC root agreement assert (already in `build_dataset.py`).
5. Per-surah key-alignment validation (QPC vs QUL vs treebank) — B's proposal (E), now a Phase 1 exit criterion.
6. Provenance completeness: every `accepted`/`reviewed` unit has ≥ 1 evidence reference and a review record.
7. No-copied-source audit: the canonical store must contain Arabic strings only in the glossary table and unit translations must not embed source rows.

---

## 8. What exists today

### 8.1 Package A assets (in `handoff_extracted/quranic_phrase_clause_handoff/`)

- 6 EQTB auxiliary files (verified intact) + `reference/results_surah_67/dataset_summary_surah_67.json` (the run summary quoted above).
- `schema/proposed_schema.sql` — 8-table proposal (source_datasets, annotation_units, unit_source_refs, unit_span_segments, unit_relationships, unit_classifications, annotation_evidence, annotation_reviews) — **starting point for the merged schema**, to be extended with translation fields and tiling spans.
- `schema/source_registry.example.yaml`, `schema/taxonomy_template.yaml` (scaffold, not a finalized standard).
- `prototype/` scripts — exploratory EQTB+QAC integration; useful parsing logic; **not** the final architecture; do not use their enriched CSVs as data.

### 8.2 Package B assets (in `handoff2_extracted/mulk-dataset/`)

- `annotations/mulk_spec.json` — Al-Mulk annotation, 30 ayahs; English finalised and normalised; **Bangla is a draft, not reviewed by a Bangla reader**.
- `annotations/CONVENTIONS.md` (annotating prompt with 3 drafted worked examples — replace with reviewed ones) + `glossary.json` (10-entry starter).
- `scripts/build_dataset.py` — builds `data/mulk.json` from spec + sources; asserts tiling, word alignment, QUL-vs-QAC root agreement. Verified working: prints **333 words, 213 phrases, 86 clauses**.
- `scripts/analyze.py` — pandas frequency/rule mining (`data/analysis_report.txt` is a saved copy).
- `scripts/convert_treebank.py` — treebank → per-surah QPC-keyed JSON (ALIGN fix, asserts 77,432). User ran it successfully; output files were written to the working directory and still need moving into `quranic-treebank/data/`.
- `scripts/generate_spec.py` + `spec_lib.py` — OpenRouter generator (dry-run tested only).
- `sources/` — Surah 67 slices of QUL files + `qul_mulk_morph.tsv` + `mulk-quran-morphology.txt` (mustafa0x fork — being replaced).
- `reference/*.json` — tag legends (pos, prefix, constituent tags, relation labels).

### 8.3 Mined hypotheses from Al-Mulk (small n; measured on the annotation made before tags were seen; re-measure on the whole Quran)

| Rule | Result |
|---|---|
| Previous word has waqf mark → clause start | 15/15 (ۚ 6, ۖ 9) |
| Prefix REM (resumption) → clause start | 10/10 |
| NEG or COND word → clause start | 12/12 |
| INTG → clause start | 4/6 |
| CONJ → clause start | 9/17 |
| CIRC → clause start | 1/3 |
| Definite (ٱل) word never starts a clause | 38/38 |
| Bare preposition stays with next word | 22/22 |
| Relative pronoun after non-verb joins previous word | 9/10 |
| Clause length 2–6 words | 95% |
| Phrase length 1–3 words | 98% |
| Phrases that are one word | 59% |
| Most repeated phrases | قُلۡ ×6, وَهُوَ ×4, إِنۡ ×3, هُوَ ٱلَّذِي ×3 |
| Only repeated clause | قُلۡ أَرَءَيۡتُمۡ ×2 |

---

## 9. Merged schema (canonical store)

Package A's 8 tables are retained and extended:

| Table | Disposition in merge |
|---|---|
| `source_datasets` | Kept. One row per source file/dataset with key, version, URL, licence, checksum. Add the QUL files and Mutashabihat as first entries. |
| `annotation_units` | Kept + **extended**: add `translation_en`, `translation_bn`, `translation_key_en`, `translation_key_bn`, and tiling fields (`ayah`, `word_start_key`, `word_end_key`, `display_order`). `unit_level` stays `phrase|clause`. |
| `unit_span_segments` | Kept. Tiling base units get one segment each (QPC key endpoints); overlay spans may use multiple ordered segments. |
| `unit_source_refs` | Kept. Roles: `exact_entity` (reuse an EQTB constituent), `evidence`, `candidate`, `derived_from`, `cross_check`. |
| `unit_relationships` | Kept (typed, directional). |
| `unit_classifications` | Kept (six dimensions; taxonomy_version; review status; confidence). |
| `annotation_evidence` | Kept (points to source records; never duplicates them). |
| `annotation_reviews` | Kept (accept/reject/revise/uncertain + reviewer + note). |
| `glossary` | **New.** From B's `glossary.json`: ar / en / bn term triples, versioned. |

---

## 10. Roadmap (merged; Phase 1 is the agreed next step)

**Phase 0 — done.** Architecture frozen by this document. Outstanding: verify licence/version metadata for every source file.

**Phase 1 — Source registry + read-only adapters + resolvers (NEXT, user-selected).**
1. `source_registry.yaml`: dataset key, version/release, URL, licence identifier, file checksum for every source.
2. Read-only adapters: QUL word list, QUL ayah translations, QUL wbw glosses, QUL morph dbs, EQTB main (UTF-16 TAB) + 6 aux files, QAC morphology, converted treebank JSON, Mutashabihat/matching-ayah. Apply the feature-reading rules (§6.3).
3. Resolvers: QPC key ↔ EQTB `(sentence_id, token_id)`/`tid`; QPC key ↔ QAC `s:a:w:segment`; implicit-token policy (no invented coordinates); constituent span resolver (`sentence_id` + inclusive `constituents_loc`).
*Exit criteria:* given any stored reference, the tool retrieves the original row on demand; checksums before/after prove sources unmodified; per-surah key-alignment validation passes (QPC vs QUL vs treebank).

**Phase 2 — Canonical store + round-trip.** Implement the merged schema (§9); convert `annotations/mulk_spec.json` into the store as first test data; re-render the Surah 67 export from store + sources and diff against existing `data/mulk.json` (must match modulo declared differences); run the no-copied-source audit; decide on flat JSONL exports for analysis.

**Phase 3 — Generator tuning on Al-Mulk.** `generate_spec.py --surah 67 --dry-run`, then a live run with a chosen model; write a model-vs-Al-Mulk-gold comparison script (boundary agreement, phrase counts, translation_key consistency); tune CONVENTIONS.md; replace the three drafted worked examples with reviewed ones; grow the glossary; Bangla review by a Bangla reader.

**Phase 4 — Pilot surahs + linguistic overlay PoC.** Pilot ~5 varied surahs interactively (1, 12, 112, 2 — especially 2:255 and 2:282 — and 67). In parallel, run the overlay PoC on Surah 67: reuse-vs-create inventory (reference exact EQTB PP/NS/VS/CS/SC constituents; create units only for missing spans), first classifications with evidence + reviews, adjudicate 67:23:11.

**Phase 5 — QA harness.** Implement §7.4 as one script suite.

**Phase 6 — Full run + review.** `--surahs 1-114`; human review of flagged + ~5% sample; finalize annotation guidelines and adjudication rules; if a second annotator is available, measure inter-annotator consistency on a sample.

**Phase 7 — Mining + release.** Mine rules and frequencies on `reviewed`+`accepted` ayahs only; version the dataset; complete licence/attribution review before any redistribution.

**Phase 8 — Application integration.** Phrase/clause browsing and search; source data resolved on demand; filters by type/function/root/lemma/surah/verse; source citations + provenance displayed; `candidate`/`uncertain` states clearly marked.

---

## 11. Open items & not verified

- Live OpenRouter calls never made; format assumed OpenAI-style chat-completions.
- `jq` examples in Package B's README untested.
- Bangla quality unreviewed (known issues in §7.3).
- Token/cost estimates are rough: whole Quran ≈ 1.3–1.8M read + 0.6–0.9M written tokens, plus ~2–3k fixed prompt tokens per batch.
- Licences: EQTB data licence, QAC data-use terms, QUL terms — all pending verification.
- Full `Quranic.csv` and QAC morphology file are not in either package — supply from original downloads.
- Converted treebank files need moving into `quranic-treebank/data/`.
- `waqf_strength` field idea (ۚ major vs ۖ minor) — open.
- `taxonomy_template.yaml` is a scaffold; the phrase/clause taxonomies need grounding in a chosen Arabic grammatical framework (Phase 4).
- Dependency relations: storage deferred (B); EQTB `rel_label` still resolves at render for display.

---

## Appendix A — Status mapping

| Canonical (A) | B origin | Meaning |
|---|---|---|
| `candidate` | `auto` | Generated automatically; never shown as gold |
| `pending` | `needs_human` | Awaiting review (validation failed, flagged, or queued) |
| `uncertain` | — | Plausible but unresolved |
| `reviewed` | `reviewed` | Checked by a human |
| `accepted` | — | Approved into the released set |
| `rejected` | — | Reviewed and not accepted |

## Appendix B — Rendered export (cache) field provenance

| Field group | Level | Source at render | Stored in canonical store? |
|---|---|---|---|
| `text`, `text_norm`, `waqf_mark` | word | QUL word list | No |
| `root`, `lemma`, `stem`, `gloss_en/bn` | word | QUL morph dbs / wbw glosses | No |
| `pos`, `cat`, `prefix_tags`, `features`, `definite`, `suffix_pron`, `qac_lemma` | word | QAC/treebank JSON | No |
| `boundary_before`, `is_clause_start`, `is_phrase_start`, `prev_word_waqf` | word | Derived from store | No (derivable) |
| word/phrase/clause spans, `translations`, `translation_keys` | unit | — | **Yes** (the new annotation) |
| `reference_translations`, `translations_phrased` | ayah | QUL translations + units | No (resolved) |
| `mutashabihat`, `matching_ayah` | ayah | Mutashabihat files | No (resolved) |
| `pattern`, `first_cat/last_cat`, tag lookups | derived | Codebooks (aux files) | No (resolved) |

## Appendix C — Working commands (from B; verified unless noted)

```bash
# Build the Al-Mulk dataset (verified working)
cd mulk-dataset && python3 scripts/build_dataset.py     # -> 333 words 213 phrases 86 clauses

# Rule/frequency mining (needs pandas)
python3 scripts/analyze.py > data/analysis_report.txt

# Convert the treebank (run once; move outputs into quranic-treebank/data/)
python3 scripts/convert_treebank.py --qpc quran-script/wbw/qpc-hafs-word-by-word.json

# Generate annotations (never live-tested)
export OPENROUTER_API_KEY=...
python3 scripts/generate_spec.py --data-root /path/to/qul --surah 67 --dry-run
python3 scripts/generate_spec.py --data-root /path/to/qul --surah 67 --model <slug>
python3 scripts/generate_spec.py --data-root /path/to/qul --surahs 1-114 --model <slug>
python3 scripts/generate_spec.py ... --retry-failed

# Package A legacy prototype (exploratory only; NOT the reference-only architecture)
python prototype/build_surah_mulk_dataset.py --eqtb data/Quranic.csv \
  --qac data/quranic-corpus-morphology-0.4.txt --aux-dir reference/eqtb_aux --out outputs/surah_67_full
```

## Appendix D — Where the original assets live

| Asset | Location |
|---|---|
| Package A (architecture, docs, schema, EQTB aux, Surah 67 summary, prototypes) | `handoff_extracted/quranic_phrase_clause_handoff/` |
| Package B (mulk-dataset: annotations, scripts, data, sources, reference legends) | `handoff2_extracted/mulk-dataset/` |
| Original archives | `upload/quranic_phrase_clause_handoff.tar.gz`, `upload/mulk-handoff.zip` |
| This merged handoff | `download/MERGED_HANDOFF.md` (+ `.docx` reading copy) |
