# Arabic phrase-chunk annotation conventions (v4.1)

## Task

For each Quran ayah, segment its Arabic words into the **smallest meaningful syntactic phrases / semantic chunks**. For every chunk, provide one English fragment and one Bangla fragment translating exactly that same Arabic span.

**Segmentation quality is the primary objective.** Decide the boundaries from Arabic syntax and local meaning. English and Bangla are translations of the already-decided spans; neither language is allowed to determine, combine, or enlarge a span merely for fluency.

The translations only need to be understandable and convey the meaning of their assigned Arabic spans. They do not need to be elegant, polished, or fully natural when read individually. When the fragments are joined in order, they should make reasonable sense, but do not sacrifice good Arabic segmentation to improve the overall flow.

## Definition: phrase / semantic chunk

A **chunk** is the smallest contiguous sequence of one or more complete Arabic words that forms a meaningful local syntactic or semantic unit in context.

Use this decision rule:

> Keep words together only when separating them would break an important local grammatical dependency, fixed expression, or semantic unit. Otherwise, split them into smaller chunks.

In practice:

- Prefer one Arabic word per chunk when that word has an identifiable meaning or syntactic function in context.
- Use two words when they form a tight local unit. Use three when the dependency genuinely requires it. Larger chunks should be uncommon and should have a clear grammatical reason.
- Keep an orthographic Arabic word intact. Do not split attached conjunctions, prepositions, articles, or pronouns out of a written word; translate their contribution in that word's chunk.
- Keep words together when a split would sever a required local relation, such as a preposition from its complement where the complement cannot be interpreted as a separate chunk, a tightly bound construct/possessive expression, or an idiomatic/fixed expression.
- Do not automatically combine every iḍāfa, verb-object pair, adjective-noun pair, or preposition-noun pair. Split them when the parts can be represented as distinct meaningful chunks without breaking the local syntax.
- A chunk's English or Bangla fragment may be elliptical or context-dependent. It does not need to read as a complete standalone sentence. However, it must not be an arbitrary fragment that breaks a necessary local Arabic dependency.
- Do not strand a connector or function word when it has no useful independent meaning in the local construction. In particular, review chunks consisting only of items such as “if”, “when”, “and”, “of”, “to”, “from”, “for”, “then”, or an auxiliary such as “is”. Keep such a word with the smallest adjacent Arabic span needed to express its function.
- Keep a predicate with the argument needed to identify what is acting or being described when separating them makes either fragment misleading (for example, a passive predicate separated from its post-verbal subject, or a conditional particle separated from the conditional clause it introduces).
- Do not split a verb from an obligatory complement if the resulting fragment is misleading; but do not automatically group every verb-object pair when both are independently meaningful and the relation remains clear.
- Do not split merely to reach a one-word average. The target is the smallest **valid** syntactic-semantic unit, not the smallest possible unit. A chunk may be several words when that is the minimum span that preserves its local Arabic relationship.

The reviewed Al-Mulk prototype is a useful reference profile (average about 1.6 Arabic words per chunk; about 59% one-word and 29% two-word chunks), **not a quota or a hard statistical target**. Other surahs and constructions can naturally differ.

## Boundary decisions

- Segment from Arabic syntax and local meaning, using the word glosses and whole-ayah translations as supporting context only.
- Never use English or Bangla fluency as the deciding test for an Arabic boundary.
- Never use chunker/treebank output, i'rab labels, mined statistics, QA flags, or previous annotations to decide boundaries.
- Chunks must be contiguous and follow the original Arabic word order. Do not skip, repeat, overlap, or reorder words.
- There is no clause segmentation task. Do not create clauses, subclauses, or clause-size targets. Return one flat ordered chunk list per ayah.

## Faithfulness to each span

- A fragment translates **only** the Arabic words in its own span. Do not import a neighbour's meaning, repeat meaning in two chunks, or leave a particle/verb/pronoun untranslated.
- Every source word contributes to exactly one chunk. Attached pronouns are translated once, in the chunk containing their host word.
- Use the numbered source-word positions to define every chunk. Return `[n]` for one word or `[start, end]` for a contiguous inclusive range. Never reproduce the Arabic text; the pipeline reconstructs the exact source spelling and marks from these positions.

## Translation quality and connected flow

- **Arabic segmentation quality comes first.** Find the smallest valid Arabic chunks before composing either translation.
- English and Bangla fragments must convey the meaning of their assigned Arabic spans and be understandable in context. Perfect fluency, elegance, or publication-quality wording is not required.
- English fragments should connect reasonably when joined with single spaces in the original chunk order. Bangla fragments should also make reasonable sense when joined in that order, following the Bangla style rules below.
- Do not make a chunk larger, combine neighbouring chunks, or change a boundary merely because the resulting English or Bangla would sound smoother.
- Individual fragments may be incomplete, elliptical, or somewhat awkward when read alone. This is acceptable when the fragment accurately represents its own Arabic span and the sequence remains comprehensible.
- Use grammatical adjustments and natural word order within a fragment when helpful, but do not add meaning from neighbouring Arabic words, duplicate meaning, or omit any part of the assigned span.
- If smooth flow conflicts with a smaller valid Arabic segmentation or exact span-level meaning, preserve the Arabic segmentation and span-level meaning. Accept less polished translation.

## Order

Chunks always follow Arabic word order. Inside one chunk, English or Bangla word order may be adjusted when required by that language. Never reorder chunks relative to one another.

## Islamic terminology (mandatory)

Do not use the English words **God**, **gods**, **Lord**, **lords**, **lordship**, **deity**, or **deities** in annotation fragments. Do not copy these terms from a reference translation. Use the Islamic term that corresponds to the actual Arabic word:

- الله / اللّٰه → **Allah**.
- رَبّ (including attached pronouns) → **Rabb**: “my Rabb”, “our Rabb”, “their Rabb”, etc.
- إِلٰه / آلِهَة → **ilah / ilahs** (or the appropriate transliteration of the actual form), not “god(s)” or “deity/deities”.
- Other divine names/attributes should follow the Arabic wording and established Islamic names, e.g. **Ar-Rahman** and **Ar-Raheem** where those names occur. Do not replace a specific Arabic name with a generic English label.

In Bangla, use **আল্লাহ** for الله, **রব** for رَبّ, and **ইলাহ** for إِلٰه / آلِهَة. Do not use ঈশ্বর, প্রভু, or খোদা in annotation fragments. Use the appropriate Islamic term based on the Arabic source, not on the wording of a reference translation. For الرَّحْمَٰن, use **Ar-Rahman** in English and **আর-রহমান** in Bangla rather than replacing the name with a generic description.

## English style

- Capitalise at the start of a sentence only. Put punctuation (, . ; : ? !) at the end of the chunk where it belongs.
- Do not use quotation marks of any kind in English fragments.
- Capitalise pronouns that refer to Allah (He, His, Him).
- Use word glosses and the reference translation as hints only; do not copy them mechanically. Reference translations may use generic English religious labels; the mandatory terminology rules above override them.

## Bangla style

- Bangla script only. No Arabic script and no romanisation inside fragments.
- Each Bangla fragment translates exactly the same Arabic span as its English counterpart. Segmentation is decided once from Arabic; both languages follow it.
- Chunks follow Arabic word order. Fragments may be elliptical/context-dependent. When joined with single spaces, the whole ayah should make reasonable sense in Bangla; perfect literary fluency is not required.
- Put end punctuation on the chunk that closes the relevant unit; use “।” for a sentence-final full stop, and retain “,” “?” “!”.
- Do not use quotation marks of any kind in Bangla fragments.
- Address register: copy the register of the Bangla reference translation for that ayah. If it addresses the listener with আপনি / আপনার / আপনাকে, use those; if it uses তুমি / তোমার / তোমাকে, use those. Decide per ayah; never mix registers inside one ayah.
- Use respectful honorific pronouns for Allah (তিনি, যিনি, তাঁর, তাঁকে), “আল্লাহ” for الله, “রব” for رَبّ, and “ইলাহ” for إِلٰه / آلِهَة. Do not use ঈশ্বর, প্রভু, or খোদা.
- Use Bangla word glosses and the whole-ayah translation as hints, not text to copy mechanically.

## Output contract

Return **only one JSON object**, with one key per requested ayah (`"surah:ayah"`). Each value is a flat, ordered list of chunk objects:

```json
{
  "67:1": [
    {"words": [1], "en": "Blessed is", "bn": "বরকতময়"},
    {"words": [2, 2], "en": "the One who", "bn": "যিনি"}
  ]
}
```

Each chunk object has exactly these required fields:

- `words`: one-based source-word positions. Use `[n]` for a single word, or `[start, end]` for an inclusive contiguous range. Do not return non-contiguous positions.
- `en`: non-empty English fragment translating only that span.
- `bn`: non-empty Bangla fragment translating that same span.

Across the list, the `words` ranges must cover every source word exactly once, in original order, with no gap, overlap, omission, duplication, or reordering. Never return Arabic text, clauses, or nested arrays. Return valid JSON only. The JSON syntax must use standard double quotes around keys and string values; do not put quotation marks inside the English or Bangla translation fragments.
