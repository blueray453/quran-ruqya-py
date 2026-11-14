# `sources/` — the read-only layer

These files are **inputs only**. They are never modified, never merged into each
other, and never copied into the annotation layer. `build.py` joins them at read
time; `annotations/` references them by word number only. `qa.py` verifies their
integrity against `sources.lock.yaml` (sha256).

| Folder | Family | Contents | Role |
| --- | --- | --- | --- |
| `text/` | text_words | `indopak.json` (whole Quran), `mulk-qpc-words.json` (surah 67 reference instance) | Word positions + Arabic text (IndoPak script) |
| `wbw/` | wbw_english | `english-wbw-translation.json` | Per-word English glosses; enters the annotation package |
| `translation/` | translation_ayah | `mulk-en-sahih.json` | Whole-ayah English reference translation; enters the annotation package |
| `audio/` | audio_timestamps | `ar.alafasy.json` | Per-ayah recitation segments `[word_no, start_ms, end_ms]`; joined at build time |
| `chunker/` | chunker | `chunks.tsv` | QA cross-check signal only; never a build basis |
| `eqtb/` | eqtb | `Quranic.csv` + tag lexicons | QA cross-check signal (clause starts, i'rab); never a build basis |
| `lexicon/` | lexicon | `word-*.db`, `ayah-*.db`, `CA*Lexicon.csv` | Lemma/root/stem inventories; inputs for the separate whole-Quran glossary project |
| `reference/` | reference | `mulk_spec.json` | Hand-edited Surah 67 prototype annotation; provenance of the bundled `annotations/surah-067.json` sample |

## Two numbering conventions (verified across the whole Quran)

1. **Ayah-end marker.** In the keyed text/wbw sources every ayah has one extra final
   key: the ayah-end marker. Therefore `keyed_max == real_max + 1`, and the real word
   count of an ayah is `keyed_max - 1` (6,236 ayahs, 77,432 real words; 83,668 keyed
   entries). The annotation layer always uses **real word numbers**.
2. **Recitation segments.** `ar.alafasy.json` uses real word numbers. 5,824 of 6,236
   ayahs align 1:1; the rest contain extra short fragments (pauses / aligner
   artifacts). `build.py` applies the documented fallback: fragments < 100 ms extend
   the nearest real word in time; longer extras are mapped onto unmatched words in
   time order; anything left is reported and left null.

## Known gaps (handled, not hidden)

- wbw glosses are missing for exactly 3 real word positions: `2:181:4`, `8:6:5`,
  `13:37:9`. `build.py` renders them as `null`; `qa.py` asserts no other gaps.
- The wbw gloss on the marker key (e.g. `67:1:10` = `(1)`) is discarded by the
  same "drop the last key" rule.
