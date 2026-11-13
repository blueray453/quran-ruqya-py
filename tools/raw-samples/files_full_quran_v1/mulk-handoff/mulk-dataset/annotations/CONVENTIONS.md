# Annotation conventions

## Task
You receive Quran ayahs as numbered Arabic words, each with word-by-word glosses and two reference translations
(English: Sahih International, Bangla: Dr. Abu Bakr Muhammad Zakaria). For each ayah, split it into CLAUSES and PHRASES
and write English and Bangla for every phrase.

## Definitions
- **Phrase**: the smallest run of consecutive Arabic words that forms a natural, meaningful English unit. It is not a word-by-word
  gloss. Examples: "in the creation of the Most Merciful", "the One who", "a harsh roar". Keep together what only makes sense together
  (a preposition with its noun, a possessive construction, a verb with its attached pronoun, a fixed expression).
- **Clause**: a consecutive run of phrases that forms a clause-sized idea (a statement, a condition, a result, a relative clause,
  a question, a command, a quoted speech act). Decide by meaning, not by length.
- **Tiling**: phrases cover words 1..N of the ayah exactly once, in order, with no gaps or overlaps. Clauses tile the ayah the same way.

## How to decide boundaries
Decide only by meaning and by what reads naturally in English. Do not treat any particular particle, conjunction or punctuation mark as an
automatic boundary. The English phrases of an ayah, joined with single spaces, must read as natural English; the Bangla phrases joined the same way
must read as natural Bangla.

## Order
Phrases always follow Arabic word order; never reorder phrases relative to each other. Inside ONE phrase you may reorder words when the
language needs it (e.g. "a group is thrown into it"). If Arabic order cannot read naturally across two phrases, merge them into one phrase.

## English
- Capitalise at the start of a sentence only. Put punctuation (, . ; : ? !) at the end of the phrase it follows.
- Quotation marks: outer “ ” and inner ‘ ’. If speech opened in an earlier ayah is still open (see "Quotes still open"), do not re-open it; if speech continues past this ayah, leave it open.
- "Allah" for الله; "the Most Merciful" for الرحمن; capitalise pronouns that refer to Allah ("He", "His", "Him").
- Use the word glosses and reference translation as hints only. Do not copy them mechanically.

## Bangla
- Phrases follow Arabic order (as above); the Bangla must still read naturally when joined.
- Respectful forms: a single person addressed respectfully (the Prophet, or a general "you" in the singular) uses আপনি; قُلْ is বলুন. A group addressed uses তোমরা.
- End sentences with । (or ? / !). Quotation marks: outer ‘ ’ and inner “ ”. Bengali script only; no Latin letters.
- Prefer the vocabulary of the Zakaria reference (আল্লাহ, রব, রহমান, আসমান, যমীন, রিযিক, নাযিল, ঈমান).

## Consistency
The same Arabic phrase gets the same English and Bangla wording every time, unless its referent really differs.

## Output format
Return ONLY one JSON object, no prose, no code fences. One key per requested ayah ("surah:ayah"). The value is a list of clauses;
a clause is a list of phrases; a phrase is [word_start, word_end, "English", "Bangla"] (word numbers as given, 1-based).

## Worked examples
(Drafts from Al-Mulk; replace with reviewed examples after the pilot.)

Input words for 67:15: 1 هُوَ | 2 ٱلَّذِي | 3 جَعَلَ | 4 لَكُمُ | 5 ٱلۡأَرۡضَ | 6 ذَلُولٗا | 7 فَٱمۡشُواْ | 8 فِي | 9 مَنَاكِبِهَا | 10 وَكُلُواْ | 11 مِن | 12 رِّزۡقِهِۦۖ | 13 وَإِلَيۡهِ | 14 ٱلنُّشُورُ
Output:
{"67:15":[[[1,2,"He is the One who","তিনিই যিনি"]],[[3,3,"made","বানিয়েছেন"],[4,6,"the earth manageable for you,","তোমাদের জন্য যমীনকে সুগম,"]],[[7,7,"so walk","অতএব তোমরা বিচরণ কর"],[8,9,"through its regions","এর দিক-দিগন্তে"]],[[10,10,"and eat","এবং তোমরা আহার কর"],[11,12,"from His provision;","তাঁর দেয়া রিযিক থেকে;"]],[[13,13,"and to Him","আর তাঁরই কাছে"],[14,14,"is the resurrection.","পুনরুত্থান।"]]]}

Input words for 67:23: 1 قُلۡ | 2 هُوَ | 3 ٱلَّذِيٓ | 4 أَنشَأَكُمۡ | 5 وَجَعَلَ | 6 لَكُمُ | 7 ٱلسَّمۡعَ | 8 وَٱلۡأَبۡصَٰرَ | 9 وَٱلۡأَفۡـِٔدَةَۚ | 10 قَلِيلٗا | 11 مَّا | 12 تَشۡكُرُونَ
Output:
{"67:23":[[[1,1,"Say,","বলুন,"],[2,3,"“He is the One who","‘তিনিই যিনি"],[4,4,"created you","তোমাদেরকে সৃষ্টি করেছেন"]],[[5,5,"and made","এবং দিয়েছেন"],[6,6,"for you","তোমাদের জন্য"],[7,7,"hearing,","শ্রবণশক্তি,"],[8,8,"sight,","দৃষ্টিশক্তি"],[9,9,"and hearts;","ও অন্তঃকরণ;"]],[[10,11,"how little","খুব অল্পই"],[12,12,"you give thanks!”","তোমরা কৃতজ্ঞতা প্রকাশ কর।’"]]]}

Input words for 67:9: 1 قَالُواْ | 2 بَلَىٰ | 3 قَدۡ | 4 جَآءَنَا | 5 نَذِيرٞ | 6 فَكَذَّبۡنَا | 7 وَقُلۡنَا | 8 مَا | 9 نَزَّلَ | 10 ٱللَّهُ | 11 مِن | 12 شَيۡءٍ | 13 إِنۡ | 14 أَنتُمۡ | 15 إِلَّا | 16 فِي | 17 ضَلَٰلٖ | 18 كَبِيرٖ
Output:
{"67:9":[[[1,1,"They will say,","তারা বলবে,"],[2,2,"“Yes,","‘হ্যাঁ,"]],[[3,5,"a warner did come to us,","অবশ্যই আমাদের কাছে সতর্ককারী এসেছিল,"]],[[6,6,"but we denied","তখন আমরা মিথ্যারোপ করেছিলাম"],[7,7,"and said,","এবং বলেছিলাম,"]],[[8,10,"‘Allah has not sent down","“আল্লাহ নাযিল করেননি"],[11,12,"anything.","কিছুই,"]],[[13,15,"You are only","তোমরা কেবল"],[16,18,"in great error.’”","মহাবিভ্রান্তিতে রয়েছ।”’"]]]}
