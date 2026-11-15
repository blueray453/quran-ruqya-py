# Chunker cross-check

| surah | ayahs | checked | ayahs failing | chunk ends OK | PHRASE-END | INSIDE-PHRASE | clause ends also in chunker |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 5 | 5 | 3 | 51 | 7 | 1 | 86% |
| 67 | 30 | 30 | 0 | 56 | 0 | 0 | 51% |
| 78 | 40 | 40 | 0 | 42 | 0 | 0 | 54% |
| 81 | 29 | 29 | 0 | 27 | 0 | 0 | 77% |
| 91 | 15 | 15 | 0 | 16 | 0 | 0 | 46% |

**Total:** 119 ayahs checked (0 without chunker coverage, 0 misaligned); 192/200 chunk ends land on clause ends; 3 ayah(s) violate the fence.

## Violations

### 2:255
- chunker ends at word 24 → **PHRASE-END** — Arabic …الَّذِىۡ يَشۡفَعُ عِنۡدَهٗۤ اِلَّا بِاِذۡنِهٖؕ…; phrase 23-24: "that can intercede with Him"
- chunker ends at word 37 → **PHRASE-END** — Arabic …بِشَىۡءٍ مِّنۡ عِلۡمِهٖۤ اِلَّا بِمَا…; phrase 35-37: "anything of His knowledge"
- clauses: 1-1 "Allah" | 2-5 "there is no deity except Him," | 6-7 "the Ever-Living, the Sustainer of all that exists." | 8-12 "Neither overtakes Him drowsiness nor sleep." | 13-19 "To Him belongs whatever is in the heavens and whatever is on the earth." | 20-26 "Who is it that can intercede with Him except by His permission?" | 27-32 "He knows what is before them and what is behind them." | 33-40 "And they do not encompass anything of His knowledge except what He wills." | 41-44 "His Kursī extends over the heavens and the earth," | 45-47 "and their preservation does not tire Him, the guarding of both of them." | 48-50 "And He is the Most High, the Most Great."

### 2:282
- chunker ends at word 42 → **PHRASE-END** — Arabic …سَفِيۡهًا اَوۡ ضَعِيۡفًا اَوۡ لَا…; phrase 41-42: "or weak,"
- chunker ends at word 81 → **PHRASE-END** — Arabic …تَسۡـــَٔمُوۡۤا اَنۡ تَكۡتُبُوۡهُ صَغِيۡرًا اَوۡ…; phrase 80-81: "to write it,"
- chunker ends at word 93 → **INSIDE-PHRASE** — Arabic …وَاَقۡوَمُ لِلشَّهَادَةِ وَاَدۡنٰۤى اَلَّا تَرۡتَابُوۡٓا…; phrase 93-95: "and more likely to prevent doubt"
- chunker ends at word 95 → **PHRASE-END** — Arabic …وَاَدۡنٰۤى اَلَّا تَرۡتَابُوۡٓا اِلَّاۤ اَنۡ…; phrase 93-95: "and more likely to prevent doubt"
- chunker ends at word 100 → **PHRASE-END** — Arabic …تَكُوۡنَ تِجَارَةً حَاضِرَةً تُدِيۡرُوۡنَهَا بَيۡنَكُمۡ…; phrase 96-100: "except when it is an immediate transaction"
- clauses: 1-3 "O you who have believed," | 4-9 "when you contract a debt for a specified term," | 10-10 "then write it down." | 11-14 "And let write between you a scribe in justice." | 15-22 "Let no scribe refuse to write as Allah has taught him." | 23-23 "So let him write," | 24-27 "and let dictate the one who bears the obligation" | 28-30 "and let him fear Allah, his Lord," | 31-34 "and not diminish anything from it." | 35-39 "But if the one who bears the obligation" | 40-48 "is of limited understanding, or weak, or unable to dictate himself," | 49-51 "then let his guardian dictate in justice." | 52-55 "And call two witnesses from among your men." | 56-59 "And if there are not two men," | 60-65 "then a man and two women from those whom you accept as witnesses," | 66-71 "so that if one of them errs, then the other can remind her." | 72-77 "And let not the witnesses refuse when they are called." | 78-86 "And do not be weary to write it, whether it is small or large, for its term." | 87-92 "That is more just in the sight of Allah and stronger as evidence," | 93-102 "and more likely to prevent doubt except when it is an immediate transaction which you conduct among yourselves," | 103-107 "then there is no blame upon you if you do not write it." | 108-110 "And take witnesses when you conclude a contract." | 111-115 "Let no scribe be harmed or any witness." | 116-120 "For if you do so, indeed, it is grave disobedience in you." | 121-122 "And fear Allah." | 123-124 "And Allah teaches you." | 125-128 "And Allah is Knowing of all things."

### 2:286
- chunker ends at word 24 → **PHRASE-END** — Arabic …تَحۡمِلۡ عَلَيۡنَاۤ اِصۡرًا كَمَا حَمَلۡتَهٗ…; phrase 20-24: "Our Lord, and do not lay upon us a burden"
- clauses: 1-6 "Allah does not burden any soul beyond its capacity." | 7-12 "It has what it earned, and against it is what it earned." | 13-19 "“Our Lord, do not take us to task if we forget or err." | 20-30 "Our Lord, and do not lay upon us a burden like that which You laid upon those before us." | 31-38 "Our Lord, and burden us not with what we have no ability to bear." | 39-43 "And pardon us, and forgive us, and have mercy upon us." | 44-45 "You are our protector." | 46-49 "So give us victory over the disbelieving people.”"

