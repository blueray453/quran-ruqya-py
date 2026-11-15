# Chunker cross-check

| surah | ayahs | checked | ayahs failing | chunk ends OK | PHRASE-END | INSIDE-PHRASE | clause ends also in chunker |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 5 | 5 | 2 | 53 | 5 | 1 | 73% |
| 67 | 30 | 30 | 0 | 56 | 0 | 0 | 58% |
| 78 | 40 | 40 | 0 | 42 | 0 | 0 | 63% |
| 81 | 29 | 29 | 0 | 27 | 0 | 0 | 68% |
| 91 | 15 | 15 | 0 | 16 | 0 | 0 | 84% |

**Total:** 119 ayahs checked (0 without chunker coverage, 0 misaligned); 194/200 chunk ends land on clause ends; 2 ayah(s) violate the fence.

## Violations

### 2:255
- chunker ends at word 24 → **PHRASE-END** — Arabic …الَّذِىۡ يَشۡفَعُ عِنۡدَهٗۤ اِلَّا بِاِذۡنِهٖؕ…; phrase 23-24: "can intercede with Him"
- clauses: 1-1 "Allah:" | 2-5 "there is no god except Him," | 6-7 "the Ever-Living, the Sustainer of all existence." | 8-12 "Neither overtakes Him drowsiness nor sleep." | 13-19 "To Him belongs whatever is in the heavens and whatever is on the earth." | 20-26 "Who is the one who can intercede with Him except by His permission?" | 27-32 "He knows what is before them and what is behind them," | 33-37 "and they do not encompass anything of His knowledge" | 38-40 "except what He wills." | 41-44 "Extends His Throne-Seat over the heavens and the earth," | 45-47 "and it does not burden Him to guard them both." | 48-50 "And He is the Most High, the Most Great."

### 2:282
- chunker ends at word 30 → **PHRASE-END** — Arabic …وَلۡيَتَّقِ اللّٰهَ رَبَّهٗ وَلَا يَبۡخَسۡ…; phrase 28-30: "and let him fear Allah, his Lord,"
- chunker ends at word 42 → **PHRASE-END** — Arabic …سَفِيۡهًا اَوۡ ضَعِيۡفًا اَوۡ لَا…; phrase 41-42: "or weak"
- chunker ends at word 81 → **PHRASE-END** — Arabic …تَسۡـــَٔمُوۡۤا اَنۡ تَكۡتُبُوۡهُ صَغِيۡرًا اَوۡ…; phrase 78-81: "And do not be weary of writing it,"
- chunker ends at word 93 → **INSIDE-PHRASE** — Arabic …وَاَقۡوَمُ لِلشَّهَادَةِ وَاَدۡنٰۤى اَلَّا تَرۡتَابُوۡٓا…; phrase 93-95: "and more likely that you do not doubt."
- chunker ends at word 100 → **PHRASE-END** — Arabic …تَكُوۡنَ تِجَارَةً حَاضِرَةً تُدِيۡرُوۡنَهَا بَيۡنَكُمۡ…; phrase 96-100: "Except when it is an immediate transaction"
- clauses: 1-3 "O you who have believed," | 4-9 "when you contract a debt for a specified term," | 10-10 "then write it down." | 11-14 "And let write between you a scribe in justice." | 15-17 "And let not refuse any scribe" | 18-22 "to write as Allah has taught him." | 23-23 "So let him write," | 24-27 "and let dictate the one upon whom is the obligation" | 28-34 "and let him fear Allah, his Lord, and not leave anything out of it." | 35-39 "But if the one upon whom is the obligation" | 40-48 "is of limited understanding or weak or unable to dictate himself," | 49-51 "then let his guardian dictate in justice." | 52-55 "And call to witness two witnesses from your men." | 56-59 "And if there are not two men," | 60-61 "then a man and two women" | 62-65 "from those whom you accept as witnesses," | 66-68 "so that if one of them errs," | 69-71 "then the other can remind her." | 72-77 "And let not the witnesses refuse when they are called upon." | 78-86 "And do not be weary of writing it, whether small or large, until its term." | 87-90 "That is more just in the sight of Allah," | 91-92 "and firmer as evidence," | 93-95 "and more likely that you do not doubt." | 96-102 "Except when it is an immediate transaction which you conduct among yourselves," | 103-107 "then there is no blame upon you if you do not write it." | 108-110 "And take witnesses when you conclude a contract." | 111-115 "Let no scribe be harmed or any witness." | 116-120 "For if you do so, indeed, it is [grave] disobedience in you." | 121-122 "And fear Allah." | 123-124 "And Allah teaches you." | 125-128 "And Allah is Knowing of all things."

