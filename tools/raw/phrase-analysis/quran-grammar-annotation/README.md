# Quranic grammar annotation layers

Two JSON files that annotate the existing IndoPak Nastaleeq Quran files with word morphology and sentence syntax
from the Quranic Arabic Corpus / Treebank. They add grammar to `indopak-nastaleeq.json` and
`indopak-nastaleeq-wbw.json`; they never change or re-define that text.

| Output (`output/`) | Records | Contains |
|---|---|---|
| `indopak-nastaleeq-wbw-grammar-normalized.json` | 77,432 written words (`surah:ayah:word`) | segments, POS, root, lemma, features, verb forms (explicit vs inferred), derived nouns, word gloss, whole-word projections |
| `indopak-nastaleeq-sentence-grammar-normalized.json` | 11,693 Treebank sentences | words, nodes with relation and head, constituents, implicit nodes, POS / function sequences |
| `validation-report.json` | | result of every validation check plus informational source findings |

Start with `docs/SCHEMA.md` (all fields and rules) and `docs/examples/` (real records).

## Run

```bash
pip install -r requirements.txt
./run_all.sh          # build -> validate -> question tests -> examples  (about a minute)
```

All inputs are in `data/` exactly as supplied (`data/CHECKSUMS.sha256`; `validate.py` fails if any changed).

## Ask questions of the JSON (no CSV needed)

```bash
python3 src/queries.py word 67:15:3
python3 src/queries.py sentence 10846
python3 src/queries.py find --root jEl
python3 src/queries.py verbforms
python3 src/queries.py derived-nouns
python3 src/queries.py top --by lemma --n 20
python3 src/queries.py sequences --kind pos_all_segments --min-len 3
```

## What is guaranteed (src/validate.py, 30 checks)

* Word keys equal the written words of the WBW file; text and ids match; verse-end markers are not words.
* **Lossless:** all 139,376 Treebank rows x 43 columns are re-created exactly from the two JSON files; each row is stored once.
* Sentence ids 1..11693, original order, valid heads and constituent spans; every word is in exactly one sentence.
* Derived fields (projections, verb forms, sequences) are recomputed independently and match.
* Every POS, relation, form, case, root and lemma used is defined in `reference_data`.
* Morphology v0.4 has the same 128,219 segments and identical feature strings as the Treebank.

## Things to know

* Original vs derived: anything under `derived` (and sentence `constituents`) is computed here.
* Segment text is Uthmani, so annotations attach to whole IndoPak words, not to characters.
* Form I is never explicit in the source: all 12,347 are inferred. Nouns with a form annotation (1,968) are not counted as verbs.
* 3 words have no Treebank data; 41 words straddle two sentences; 26 sentences are prefix-only fragments; 132 POS tags differ from v0.4. All are recorded in the metadata and in `docs/SCHEMA.md` section 7.
* The supplied feature guide has 7 wrong English descriptions (verb-form ordinals, mood). They are kept verbatim and corrected beside the original.
* Not in the source, hence not in the files: explanations of why a case applies, what a particle does, contextual translation.

CSV reports (frequencies, sequence tables, learning order) are not generated: they are queries over these files.
`src/queries.py sequences` shows how, and `docs/SCHEMA.md` section 9 explains why short POS sequences make a poor learning order.

Grammar data: Quranic Arabic Corpus (corpus.quran.com), morphology v0.4 (GNU GPL, redistribution with this notice; the source
file says it must not be changed). The generated files are derivative works and should carry the same attribution and license terms.
