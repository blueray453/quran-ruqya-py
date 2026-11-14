# HANDOFF: Quran clause/phrase dataset (Al-Mulk pilot -> whole Quran)

Written at the end of chat 1 so a new chat can continue without the history. Read this first, then README.md.

## 1. Goal
Split every ayah into **clauses** and **phrases** (minimal semantic building blocks that make natural sense in English), with **English and Bangla for each phrase**,
so that joining the phrases of a clause (in Arabic word order) reads naturally. Build it so that **repetition frequencies and segmentation rules can be mined afterwards**.
Surah 67 (Al-Mulk) is the pilot/template; the target is the whole Quran (6,236 ayahs, 77,432 QPC words, 114 surahs).
Example of the idea (67:15): هُوَ ٱلَّذِي | جَعَلَ لَكُمُ ٱلۡأَرۡضَ ذَلُولٗا | فَٱمۡشُواْ فِي مَنَاكِبِهَا | وَكُلُواْ مِن رِّزۡقِهِۦ | وَإِلَيۡهِ ٱلنُّشُورُ
-> "He is the One who" / "made the earth manageable for you," / "so walk through its regions" / "and eat from His provision;" / "and to Him is the resurrection."

## 2. Decisions already made by the user (do not re-litigate)
- **JSON only** (CSV was dropped). One nested JSON per surah is the target layout; analysis flattens with pandas in memory.
- **Source priority: QUL first, Quranic Treebank second** (GPL licence is fine for the user).
- **Bangla reference = Zakaria** (`bn-dr-abu-bakr-muhammad-zakaria-simple.json`; uses respectful আপনি). Rawai al-Bayan dropped (uses তুমি).
- **Bangla phrases follow Arabic order**; no separate Bangla reading order (user reads "যিনি সৃষ্টি করেছেন সাত আসমান স্তরে স্তরে" as natural).
- **Dropped:** QSU (too coarse: ayah-sized units; only finding kept: it split at waqf ۚ 5/6 and ۖ 0/9), recitation timings (reciter-dependent), dependency relations (deferred), the `mustafa0x` morphology fork (to be replaced by the treebank).
- **Annotation must be independent of rules.** The annotating model sees only Arabic words, word glosses, the two reference translations, CONVENTIONS.md and a glossary. It never sees tags, sentence ids or mined rules.
  Tags/sentence ids are attached afterwards, and rules are mined after the whole dataset exists (otherwise the statistics are circular). Translation memory may FLAG conflicts only, never auto-fill.
- User has an **OpenRouter** API key. Context-window/batching strategy was to be discussed after the dataset shape and sources were fixed (they are now); a batching design is implemented (sec. 5).

## 3. Sources (all from the user's QUL download unless noted; user's tree is in tree.txt form: quran-script/, english-translation/, bangla-translation/, grammar/, metadata/, quranic-treebank/, Mutashabihat ul Quran/, matching-ayah.json ...)
| Need | File |
|---|---|
| Master word list (keys `s:a:w`, text, waqf marks) | quran-script/wbw/qpc-hafs-word-by-word.json (the last key of each ayah is the end-of-ayah number, not a word) |
| English / Bangla ayah translations | en-sahih-international-simple.json, bn-dr-abu-bakr-muhammad-zakaria-simple.json |
| English / Bangla word glosses | english-wbw-translation.json, bangali-word-by-word-translation.json |
| root / lemma / stem | grammar/word-root.db, word-lemma.db, word-stem.db (Surah 67 extracted to sources/qul_mulk_morph.tsv; extraction = join *_words.word_location to the id table) |
| Tags, sentence ids, constituent spans | NoorBayan/Quranic corpus/Quranic.rar -> Quranic.csv (UTF-16, tab) -> scripts/convert_treebank.py. Tag legends in reference/ (and quranic-treebank/grammar-legends/) |
| Repetition cross-check | Mutashabihat ul Quran/phrases.json + phrase_verses.json, matching-ayah.json |
| Not needed | recitation/, topics.db, ayah-*.db, tajweed/other scripts, colored WBW, surah-info, Rawai file, other metadata |
`metadata/quran-metadata-ayah.json` words_count is WRONG for 37:130 (counts 4; QPC/treebank 3). QPC is the authority.

## 4. Data gotchas found (important for scaling)
- QPC writes `بَعۡدَ مَا` as 2 words in **2:181, 8:6, 13:37**; the treebank merges it into 1 word (so all later treebank words in those ayahs are numbered one lower than QPC).
  The English/Bangla word-gloss files keep QPC keys but have no entry for the second part (3 missing keys). `convert_treebank.py` already fixes this (ALIGN table; output keys = QPC keys; asserts 77,432 words; `--qpc FILE` checks every ayah).
  The user ran it and got 77,432 words (they wrote output into the current folder `.`; move the surah-NNN.json files into quranic-treebank/data/).
- 37:130:3 `إِلۡ يَاسِينَ` is ONE QPC word containing a space: never tokenise QPC text by whitespace; use the word keys.
- Bangla word-gloss file lacks the end-marker key 2:181:15 (harmless). English WBW total 83,665 keys = QPC 83,668 minus the 3 missing second parts.
- Bangla word glosses contain stray quote marks and informal forms (use as drafting hints only).
- QUL root vs QAC root: 0 disagreements on 209 words (Surah 67). Lemma differs on 28 (mostly spelling; 3 words have no QUL lemma: 67:8:9, 67:19:9, 67:23:10; 3 أَمَّنۡ words lemmatised مِن by QUL vs أَم).
- The treebank/QAC English descriptions in VerbMood and VerbForm sheets of CAMorphFeatures.xlsx are wrong (not used).

## 5. What exists in this zip
| Path | Status |
|---|---|
| annotations/mulk_spec.json | Al-Mulk annotation: ayah -> clauses -> phrases = [word_start, word_end, english, bangla]. English finalised (normalised); **Bangla is Claude's draft, not reviewed by a Bangla reader** |
| annotations/CONVENTIONS.md, glossary.json | Prompt for the annotating model (3 worked examples from Al-Mulk, drafts; glossary is a 10-entry starter) |
| scripts/build_dataset.py | Builds data/mulk.json from the spec + sources/ (Surah 67 only). Asserts tiling, word alignment, QUL-vs-QAC root agreement |
| scripts/analyze.py | pandas: frequency + rule mining; writes to stdout (data/analysis_report.txt is a saved copy) |
| scripts/convert_treebank.py | Treebank -> per-surah QPC-keyed JSON (see sec. 4). 114 files ~10 MB |
| scripts/generate_spec.py + spec_lib.py | OpenRouter generator: batches (~350 words), prompts, validation, retry, resume, per-ayah status. **Tested offline only (dry-run + mock replies); no live API call has ever been made** |
| data/mulk.json | Built dataset: ayah > clause > phrase > word. Fields: translations{en,bn}, translation_keys, reference_translations, translations_phrased, mutashabihat, matching_ayah; word: root/lemma/stem (QUL), gloss_en/bn, pos/cat/prefix_tags/features (QAC fork), boundary flags |
| reference/*.json | Tag legends: pos_tags, prefix_tags, constituent_tags, relation_labels |
| sources/ | Surah 67 slices of the QUL files, mulk-slices.json, qul_mulk_morph.tsv, mulk-quran-morphology.txt (mustafa0x fork, QAC v0.4 modified) |
Run: `cd mulk-dataset && python3 scripts/build_dataset.py` -> prints `333 words 213 phrases 86 clauses`; `python3 scripts/analyze.py > data/analysis_report.txt` (needs pandas).
Generation (see README): `export OPENROUTER_API_KEY=...; python3 scripts/generate_spec.py --data-root <QUL folder> --surah 67 --model <slug> [--dry-run]`.
Spec files from the generator are `annotations/surah-NNN.json` = {"surah","ayahs":{a: clauses},"status":{a:{status auto|needs_human|reviewed, warnings, model, prompt_hash, depth}}}; `ayahs` has the same shape the build reads.

## 6. Rules mined on Al-Mulk (HYPOTHESES: 333 words, measured on Claude's own annotation made BEFORE the tags were looked at; small n; to be re-measured on the whole Quran)
Tags: REM = resumption particle (واو/فاء الاستئناف), NEG = negative particle, COND = conditional particle, CONJ = coordinating conjunction, CIRC = circumstantial (واو الحال), INTG = interrogative (see reference/).
- previous word has waqf mark -> clause start 15/15 (ۚ 6 marks, ۖ 9 marks)
- prefix REM -> clause start 10/10; NEG or COND word -> clause start 12/12; INTG 4/6; CONJ -> clause start 9/17 (53%); CIRC 1/3
- definite (ٱل) word never starts a clause 38/38; bare preposition (no pronoun suffix) stays with next word 22/22; relative pronoun after a non-verb joins previous word 9/10
- clause length 2-6 words 95%; phrase length 1-3 words 98%; 59% of phrases are one word
- Most repeated phrases: قُلۡ x6, وَهُوَ x4, إِنۡ x3, هُوَ ٱلَّذِي x3; only repeated clause: قُلۡ أَرَءَيۡتُمۡ x2
- Treebank cross-checks: 53/54 treebank sentence starts are Claude clause starts; 0/50 PP spans split by Claude phrase boundaries; one disagreement: 67:23:11 (treebank starts a sentence at مَّا تَشۡكُرُونَ, Claude kept قَلِيلٗا مَّا as one phrase)
- Repetition counting must use SEQUENCES of consecutive phrases (e.g. 67:25 words 1-4 repeat in 6 surahs but span 3 Claude phrases), not only whole phrases.

## 7. Bangla review points (Claude's draft)
67:3 verb-first negative ("আপনি দেখতে পাবেন না রহমানের সৃষ্টিতে কোনো খুঁত।"); 67:20 clumsy; 67:15 and 67:8 stiff Arabic order; 67:4:1 كَرَّتَيْنِ "দুইবার" vs Zakaria "দ্বিতীয়বার";
وَهُوَ is "আর তিনি" everywhere except 67:4 ("আর তা হবে", refers to the vision): English aliases it ("and it is"->"and he is") but Bangla has no alias yet (1 Bangla key inconsistency).

## 8. Proposed but NOT yet confirmed by the user
(A) per-surah files + flat JSONL per level for whole-Quran analysis; (B) stable word-range IDs like `67:15:3-6` instead of c2:p1 counters; (C) per-ayah status auto/draft/reviewed and statistics on reviewed only;
(E) per-surah validation of key alignment (QPC vs QUL vs treebank); (F) conventions file as shared memory. Idea: `waqf_strength` field (ۚ major vs ۖ minor).

## 9. Next steps (in this order)
1. Run `generate_spec.py --surah 67 --dry-run`, then a real Surah 67 run with a chosen OpenRouter model; write a comparison script (model vs the Al-Mulk annotation: boundary agreement, phrase counts) to tune CONVENTIONS.md.
2. Pilot ~5 varied surahs interactively (short, long, long ayahs, dialogue, e.g. 1, 12, 112, 2 (2:255, 2:282), 67); replace the three drafted examples with reviewed ones; grow the glossary; Bangla reviewed by a Bangla reader.
3. Update build_dataset.py to loop over annotations/surah-NNN.json and all 114 surahs from the full QUL files; extract root/lemma/stem for all surahs; switch tags to the QPC-keyed treebank JSON (drop the mustafa0x fork); add sentence_id and constituent spans (PP/VS/NS/CS/SC/S) as fields.
4. QA script after annotation: treebank sentence-start disagreements, split PP spans, same-Arabic-different-translation flags, Mutashabihat comparison (sequence-based).
5. Full run (`--surahs 1-114`), human review of flagged + ~5% sample; then mine rules and frequencies on `reviewed` ayahs.

## 10. Not verified
Live OpenRouter calls (format follows its OpenAI-style chat-completions API); the `jq` examples in the README; Bangla quality; token/cost estimates (rough: whole Quran reads ~1.3-1.8M and writes ~0.6-0.9M tokens, plus ~2-3k tokens of fixed prompt per batch).

## 11. Paste this to start the new chat
"I'm continuing a project from a previous chat. The attached zip is the project (mulk-dataset/). Read HANDOFF.md first, then README.md. Goal: clause/phrase dataset with English and Bangla for the whole Quran; Al-Mulk is the pilot. Settled decisions are in HANDOFF.md section 2; don't reopen them. Start with next step 1 in section 9: [say what you want first]."
