# Chunker cross-check

| surah | ayahs | checked | ayahs failing | chunk ends OK | PHRASE-END | INSIDE-PHRASE | clause ends also in chunker |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 4 | 4 | 1 | 30 | 1 | 0 | 71% |
| 67 | 30 | 30 | 0 | 56 | 0 | 0 | 58% |
| 78 | 40 | 40 | 0 | 42 | 0 | 0 | 63% |
| 81 | 29 | 29 | 0 | 27 | 0 | 0 | 68% |
| 91 | 15 | 15 | 0 | 16 | 0 | 0 | 84% |

**Total:** 118 ayahs checked (0 without chunker coverage, 0 misaligned); 171/172 chunk ends land on clause ends; 1 ayah(s) violate the fence.

## Violations

### 2:255
- chunker ends at word 24 → **PHRASE-END** — Arabic …الَّذِىۡ يَشۡفَعُ عِنۡدَهٗۤ اِلَّا بِاِذۡنِهٖؕ…; phrase 23-24: "can intercede with Him"
- clauses: 1-1 "Allah:" | 2-5 "there is no god except Him," | 6-7 "the Ever-Living, the Sustainer of all existence." | 8-12 "Neither overtakes Him drowsiness nor sleep." | 13-19 "To Him belongs whatever is in the heavens and whatever is on the earth." | 20-26 "Who is the one who can intercede with Him except by His permission?" | 27-32 "He knows what is before them and what is behind them," | 33-37 "and they do not encompass anything of His knowledge" | 38-40 "except what He wills." | 41-44 "Extends His Throne-Seat over the heavens and the earth," | 45-47 "and it does not burden Him to guard them both." | 48-50 "And He is the Most High, the Most Great."

