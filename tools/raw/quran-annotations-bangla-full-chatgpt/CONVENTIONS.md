# Arabic phrase-chunk annotation conventions (v3.0)

## Task

For each Quran ayah, segment its Arabic words into the **smallest meaningful syntactic
phrases / semantic chunks**. For every chunk, provide one English fragment and one Bangla
fragment translating exactly that same Arabic span.

The segmentation is decided from the Arabic. English and Bangla are translations of the
already-decided spans; neither language is allowed to determine or enlarge a span merely
for fluency.

## Definition: phrase / semantic chunk

A **chunk** is the smallest contiguous sequence of one or more complete Arabic words that
forms a meaningful local syntactic or semantic unit in context.

Use the following decision rule:

> Keep words together only when separating them would break an important local grammatical
> dependency, fixed expression, or semantic unit. Otherwise, split them into smaller chunks.

In practice:

- Prefer one Arabic word per chunk when that word has an identifiable meaning or syntactic
  function in context.
- Use two words when they form a tight local unit. Use three when the dependency genuinely
  requires it. Larger chunks should be uncommon and should have a clear grammatical reason.
- Keep an orthographic Arabic word intact. Do not split attached conjunctions, prepositions,
  articles, or pronouns out of a written word; translate their contribution in that word's
  chunk.
- Keep words together when a split would sever a required local relation, such as a
  preposition from its complement where the complement cannot be interpreted as a separate
  chunk, a tightly bound construct/possessive expression, or an idiomatic/fixed expression.
- Do not automatically combine every iḍāfa, verb-object pair, adjective-noun pair, or
  preposition-noun pair. Split them when the parts can be represented as distinct meaningful
  chunks without breaking the local syntax.
- A chunk's English or Bangla fragment may be elliptical or context-dependent. It does not
  need to read as a complete standalone sentence. Do not merge Arabic words just to make an
  English or Bangla fragment sound more fluent.
- Do not split merely to reach a one-word average. The target is the smallest *meaningful*
  unit, not the smallest possible unit.

The reviewed Al-Mulk prototype is a useful reference profile (average about 1.6 Arabic
words per chunk; about 59% one-word and 29% two-word chunks), **not a quota or a hard
statistical target**. Other surahs and constructions can naturally differ.

## Boundary decisions

- Segment from Arabic syntax and local meaning, using the word glosses and whole-ayah
  translations as supporting context only.
- Never use English fluency as the deciding test for an Arabic boundary.
- Never use chunker/treebank output, i'rab labels, mined statistics, QA flags, or previous
  annotations to decide boundaries.
- Chunks must be contiguous and follow the original Arabic word order. Do not skip, repeat,
  overlap, or reorder words.
- There is no clause segmentation task. Do not create clauses, subclauses, or clause-size
  targets. Return one flat ordered chunk list per ayah.

## Faithfulness to each span

- A fragment translates **only** the Arabic words in its own span. Do not import a neighbour's
  meaning, repeat meaning in two chunks, or leave a particle/verb/pronoun untranslated.
- Every source word contributes to exactly one chunk. Attached pronouns are translated once,
  in the chunk containing their host word.
- Use the numbered source-word positions to define every chunk. Return `[n]` for one word
  or `[start, end]` for a contiguous inclusive range. Never reproduce the Arabic text; the
  pipeline reconstructs the exact source spelling and marks from these positions.

## Order

Chunks always follow Arabic word order. Inside one chunk, English or Bangla word order may
be adjusted when required by that language. Never reorder chunks relative to one another.

## English style

- Capitalise at the start of a sentence only. Put punctuation (, . ; : ? !) at the end of
  the chunk where it belongs.
- Quotation marks: outer “ ” and inner ‘ ’. If speech opened in an earlier ayah is still
  open, do not re-open it; if speech continues past this ayah, leave it open.
- Use "Allah" for الله; "the Most Merciful" for الرحمن; capitalise pronouns that refer to
  Allah ("He", "His", "Him").
- Use word glosses and the reference translation as hints only; do not copy them mechanically.

## Bangla style

- Bangla script only. No Arabic script and no romanisation inside fragments.
- Each Bangla fragment translates exactly the same Arabic span as its English counterpart.
  Segmentation is decided once from Arabic; both languages follow it.
- Chunks follow Arabic word order. Fragments may be elliptical/context-dependent. When
  joined with single spaces, the whole ayah should read as natural Bangla.
- Put end punctuation on the chunk that closes the relevant unit; use “।” for a sentence-final
  full stop, and retain “,” “?” “!”.
- Address register: copy the register of the Bangla reference translation for that ayah.
  If it addresses the listener with আপনি / আপনার / আপনাকে, use those; if it uses তুমি /
  তোমার / তোমাকে, use those. Decide per ayah; never mix registers inside one ayah.
- Use respectful honorific pronouns for Allah (তিনি, যিনি, তাঁর, তাঁকে) and “আল্লাহ” for الله.
- Use Bangla word glosses and the whole-ayah translation as hints, not text to copy mechanically.

## Quotation continuity

A previous ayah's English reference translation, when supplied, is context only. Use it to
see whether speech is already open. Never annotate that previous ayah. Earlier ayahs in the
same request serve the same context-only purpose for later ayahs.

## Output contract

Return **only one JSON object**, with one key per requested ayah (`"surah:ayah"`). Each value
is a flat, ordered list of chunk objects:

```json
{
  "67:1": [
    {"words": [1], "en": "Blessed is", "bn": "বরকতময়"},
    {"words": [2, 2], "en": "the One who", "bn": "যিনি"}
  ]
}
```

Each chunk object has exactly these required fields:

- `words`: one-based source-word positions. Use `[n]` for a single word, or
  `[start, end]` for an inclusive contiguous range. Do not return non-contiguous positions.
- `en`: non-empty English fragment translating only that span.
- `bn`: non-empty Bangla fragment translating that same span.

Across the list, the `words` ranges must cover every source word exactly once, in original
order, with no gap, overlap, omission, duplication, or reordering. Never return Arabic text,
clauses, or nested arrays. Return valid JSON only. Inside text fragments, use curly quotation
marks, never a straight double quote.
