# Handoff: Quran clause/phrase dataset (Al-Mulk pilot -> whole Quran)

Read this first in the new chat. Upload the files listed in section 10.

## 1. Goal
Build a dataset that splits every ayah into **clauses** and **phrases** with English (and Bangla) renderings, then
- find which clauses/phrases repeat most and how often,
- extract segmentation rules and measure each rule's frequency and accuracy.

Surah Al-Mulk (67) is the pilot for "idea generation"; the target is the whole Quran (114 surahs, 6,236 ayahs, about 77,430 words).
Rough size if Al-Mulk ratios hold: ~20,000 clauses, ~49,500 phrases (unverified guess).

## 2. Definitions agreed with the user
- **Clause**: a group of consecutive Arabic words forming one clause of the verse.
- **Phrase**: the smallest chunk inside a clause that still makes natural sense **in English** (a word-by-word gloss would not).
  Example: 67:3 `ٱلَّذِي | خَلَقَ | سَبْعَ سَمَٰوَٰتٖ | طِبَاقٗا` = "the One who | created | seven heavens | in layers".
  Joined in order, the phrases must rebuild the clause's translation.
- Both are defined on **Arabic word ranges** (`word_start`..`word_end`), shared by all languages.
- **Phrases keep Arabic order in every language.** The user reads Bangla and confirmed Arabic order reads fine
  ("যিনি সৃষ্টি করেছেন সাত আসমান স্তরে স্তরে"), so there is no per-language reading order.
- Where a reorder is needed inside one phrase (e.g. 67:8 "a group is thrown into it"), the phrase stays one unit.

## 3. Current state (what exists)
Folder `mulk-dataset/` (built in the assistant sandbox; re-upload to continue):
- `annotations/mulk_spec.json`: the ONLY hand-edited file. ayah -> clauses -> phrases = `[word_start, word_end, "English"]`.
- `scripts/build_dataset.py`: merges spec + sources -> `data/mulk.json`. Asserts phrases tile clauses and clauses tile each ayah.
- `scripts/analyze.py`: frequency + rule mining (flattens the JSON with pandas in memory). Report in `data/analysis_report.txt`.
- `scripts/convert_treebank.py`: converts the Quranic Treebank CSV to per-surah JSON (the user already ran it on their machine).
- `reference/*.json`: legends for POS, prefix, constituent and relation tags (from the treebank legend files).
- `sources/`: QPC words, Digital Khatt, Sahih (Surah 67 slices), `qul_mulk_morph.tsv` (QUL root/lemma/stem), and `mulk-quran-morphology.txt`.
- `data/mulk.json`: nested ayah > clause > phrase > word, morphology inline. **333 words, 213 phrases, 86 clauses, 30 ayahs. English only.**
- `README.md`: field documentation.

**Not yet done:** Bangla in the schema; the tag source is still the `mustafa0x/quran-morphology` fork of QAC (to be replaced by the
treebank); range-based IDs; review-status field; sentence ids / constituent spans; any surah other than 67.

## 4. Source priority (user decision: QUL first, Quranic Treebank second)
| Need | Source |
|---|---|
| Word text, word numbering, waqf marks | QUL `qpc-hafs-word-by-word.json` (**master word list**) |
| Ayah text | QUL `digital-khatt-v2.json` |
| English ayah translation | QUL `en-sahih-international-simple.json` |
| root, lemma, stem | QUL `word-root.db`, `word-lemma.db`, `word-stem.db` |
| English / Bangla word glosses (drafting aid only) | QUL `english-wbw-translation.json`, `bangali-word-by-word-translation.json` |
| Bangla reference translation | QUL `bn-dr-abu-bakr-muhammad-zakaria-simple.json` (uses respectful আপনি; Rawai al-Bayan uses তুমি, so not used) |
| POS / prefix tags, features | Quranic Treebank (NoorBayan/Quranic, MIT; derived from QAC, GPL accepted by user) |
| Sentence ids, constituent spans (PP/VS/NS/CS/SC/S) | Quranic Treebank, **used only as a post-hoc check**, never to propose boundaries |
| Per-ayah word counts, surah names/revelation place | QUL metadata files |
| Outside repetition check | `Mutashabihat ul Quran/*.json`, `matching-ayah.json` |

**Dropped:** QSU (units are ayah-sized, too coarse); recitation timing (varies by reciter, readers stop anywhere);
the `mustafa0x` fork (modified QAC: changed roots/lemmas) once the treebank is wired in; dependency relations (deferred);
treebank lemma/root columns; `topics.db`, tajweed and other script variants.

## 5. Decisions made
1. **Format: JSON only** (no CSV). Analysis flattens in memory; whole-Quran analysis may use JSON-lines (still JSON).
2. **Annotation must stay independent of the rules.** Boundaries and English are decided from Arabic + meaning only.
   Tags/treebank data are attached afterwards as observations. Rules are mined once, later, over the whole dataset.
   (The Al-Mulk annotation was made before any tags were pulled, so its rule statistics are not circular.)
3. **Translation memory only flags** same-Arabic/different-English conflicts; it does not auto-fill (auto-fill would inflate repetition stats).
4. **Layout:** raw `sources/` never edited; per-surah annotation files; per-surah built JSON.
5. **Stable IDs:** use word-range IDs (`67:15:3-6`) instead of `c2:p1` counters (counters renumber when boundaries change).
6. **Status per ayah:** `auto | draft | reviewed`; statistics use `reviewed` only.
7. **Languages:** `translations: {"en": ..., "bn": ...}` on phrases and clauses; a clause translation = its phrases joined in Arabic order.
   Ayah level keeps `translation_sahih` and the Zakaria Bangla reference.
8. **Bangla address conventions** (record in CONVENTIONS.md): singular "you" = আপনি, plural = তোমরা, the command قُلْ = বলুন.
   Word-gloss file is drafting material only (stray quote marks, informal "বল").
9. **Repetition counting** must include **sequences of consecutive phrases** (sliding window), not only whole phrases,
   because repeated Arabic sequences often cross phrase boundaries (e.g. 67:25:1-4 repeats in 6 ayahs but is 3 phrases here).
10. **Context-window / batching strategy for the whole Quran: deliberately deferred** by the user until the dataset shape and sources are final.
    Design assumption: work through scripts, per surah, with short reports back to the chat; `CONVENTIONS.md` + this file are the memory.

## 6. Findings so far (all measured on Al-Mulk only, against the assistant's own segmentation)
Tag meanings (from the treebank legends): **REM** = resumption particle (a وَ/فَ opening a new statement, not joining items),
**NEG** = negative particle (مَا, لَا...), **COND** = conditional particle (إِنْ "if", لَوْ), **CONJ** = coordinating conjunction,
**CIRC** = circumstantial وَ ("while"), **INTG** = interrogative, **CAUS** = cause fā' ("so").

Candidate rules (hypotheses; recheck on all surahs):
| Rule | Al-Mulk accuracy |
|---|---|
| Waqf mark on previous word -> clause start | 15/15 |
| Prefix REM -> clause start | 10/10 |
| NEG or COND particle -> clause start | 12/12 |
| Prefix CONJ -> clause start | 9/17 (53%) |
| Prefix CIRC -> not a clause start | 1/3 inside (33%): weak |
| Definite (ٱل) word never starts a clause | 38/38 |
| Bare preposition (no pronoun suffix) stays with next word | 22/22 |
| Relative pronoun after a non-verb joins previous word | 9/10 |
| Clause 2-6 words / phrase 1-3 words | 82/86 / 208/213 |

Other results:
- Waqf marks: ۚ (stopping preferred) 6 in Al-Mulk; ۖ (continuing preferred) 9. QSU split at 5/6 of the former and 0/9 of the latter.
  Idea not yet implemented: a `waqf_strength` field.
- Most repeated (Al-Mulk): phrases قُلْ x6, وَهُوَ x4, هُوَ ٱلَّذِي x3, إِنْ x3. Only repeated clause: قُلْ أَرَأَيْتُمْ x2.
- QUL root vs QAC-fork root: 0 disagreements on 209 words. Lemma: 28 differences of 309 (mostly spelling; 3 words have no QUL lemma:
  67:8:9, 67:19:9, 67:23:10; 3 words أَمَّنْ are مِن in QUL vs أَم in QAC).
- Treebank vs my segmentation (Surah 67): 53/54 treebank sentence starts are my clause starts; 0/50 PP spans split by my phrases;
  39/50 PP spans start at my phrase start; ~25/50 equal one of my phrases (reported, not re-verified). The one sentence start I don't share: **67:23:11** (`مَّا تَشۡكُرُونَ`;
  I kept `قَلِيلٗا مَّا` as one phrase) - **flagged for grammar review**, unresolved.
- Translation normalisation already applied in the spec: فَسَتَعْلَمُونَ = "So you will soon know" (67:17, 67:29); فَمَن = "who then" (67:28, 67:30);
  إِنَّهُ = "Indeed, He is" (67:13, 67:19; 19:12-15 now "Indeed, He is | All-Seeing over everything."); وَهُوَ in 67:4 stays "and it is"
  (refers to the vision) but shares the key "and he is" via `translation_key`.

## 7. Data inconsistencies found (user will check other QUL datasets)
Counts of words excluding end-of-ayah markers: **QPC 77,432 | treebank 77,429 | metadata sum 77,433 | English WBW keys 83,665 | Bangla WBW keys 83,664**.
- **`بَعْدَ مَا` merge:** QPC has two words; the treebank has one (`بَعْدَمَا`) in **8:6 (QPC 4+5), 13:37 (QPC 8+9), 2:181 (QPC 3+4)**.
  After the merge every treebank word number is one lower than QPC. Build needs an explicit QPC<->treebank mapping table for these ayahs.
- **English and Bangla WBW lack the `مَا` keys** `8:6:5`, `13:37:9`, `2:181:4`. Bangla also lacks the end marker `2:181:15`
  (the earlier "missing key" was just this marker, not a word).
- **Metadata `words_count`** for **37:130** is 4, QPC and treebank say 3 (QPC key `37:130:3` holds `إِلۡ يَاسِينَ` as one entry with a space).
- **Not yet checked:** word *text* equality QPC vs treebank for all ayahs (counts can match while words differ); QUL root/lemma/stem coverage outside Surah 67.
- Treebank file notes: UTF-16 TSV inside `corpus/Quranic.rar`; 139,376 token rows; 11,157 elided (inserted) tokens are skipped by the converter;
  converted subset = 10.2 MB for 114 surahs, 77,429 words, 26,463 spans.
- `DATA_SOURCE.adoc` lists `bn-taisirul-quran-simple.json`, but the user's folder has the Zakaria file; fix the README source table.
- The English descriptions in the treebank's `CAMorphFeatures.xlsx` VerbMood and VerbForm sheets are **wrong** (e.g. JUS labelled "Subjunctive");
  use Arabic names / tag codes only. Those sheets were not included in `reference/`.

## 8. Next steps (suggested order)
1. Run the word-text comparison QPC vs treebank for all ayahs; list every mismatch (user can then check other QUL datasets).
2. Resolve inconsistencies in section 7 with the user's other QUL datasets; build the QPC<->treebank mapping table.
3. Rebuild Al-Mulk in the new layout: range IDs, `status`, `translations {en, bn}`, QUL-first sources, treebank tags + sentence ids + constituent spans.
4. Draft Bangla for Al-Mulk phrases (from word glosses + Zakaria); mark as draft; the user reads Bangla and reviews.
5. Write `CONVENTIONS.md` (segmentation guidelines, English and Bangla style, punctuation/quotes, address forms, normalisation list).
6. Generalise extraction + validation to all 114 surahs (needs the user's full QUL files; assertions per surah; mismatches reported, never skipped).
7. Design the annotation workflow and the batching/context-window plan (deferred topic; discuss after steps 1-6).
8. Mine rules and repetition over the whole dataset (sliding windows over consecutive phrases; compare with Mutashabihat ranges).

## 9. Cautions / unverified
- Rule accuracies are measured on one surah and on the assistant's own segmentation: strong hypotheses, not ground truth.
- The `jq` example in the README was never run (jq was not installed in the sandbox). The Bangla example phrases in the schema discussion were illustrative only.
- The treebank's syntactic annotations (sentences, spans) are newer than QAC; their accuracy is not independently verified.
- Treebank licence: MIT for the repo, GPL for the QAC-derived data (user is fine with GPL); QUL licence terms: see qul.tarteel.ai.
- Size and annotation-volume projections for the whole Quran are rough.

## 10. What is in this package (upload the whole zip to the new chat)
Everything in sections 3-9 is in `mulk-dataset/`: this file, README, `annotations/mulk_spec.json`, the three scripts, `reference/*.json`,
`sources/` (Surah 67 slices of QPC, Digital Khatt, Sahih; `qul_mulk_morph.tsv`; `mulk-quran-morphology.txt`), `data/mulk.json` and `data/analysis_report.txt`.
Rebuild check: `python3 scripts/build_dataset.py && python3 scripts/analyze.py` (needs pandas).

**Not in the package (still on the user's machine, ask when needed):** `mulk-slices.json` (English/Bangla word glosses, Zakaria and Rawai translations,
matching-ayah, phrase_verses and recitation slices for Surah 67), the full QUL files, the full `Quranic.csv`, and the 114 converted treebank JSON files.

## 11. How the user likes to work
- Decide the dataset shape and sources before building; ask for the plan first.
- Runs commands on their own machine (zsh, `python3`, `sqlite3`) and pastes output back; keep commands self-contained and the output short.
- Prefers JSON; wants plain-language meanings for tags (never just abbreviations); wants inconsistencies in any dataset reported so they can cross-check against other QUL resources.
- Reads Bangla and Arabic; wants things confirmed with real data, not assumed.
