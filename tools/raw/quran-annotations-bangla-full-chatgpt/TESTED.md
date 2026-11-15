# Test status — v5

- Python syntax check: passed.
- Smoke sample generation: passed; 45 unique ayahs, 1,208 Arabic words.
- Required anchors present: 2:255, 2:282, 2:286, 4:176, 5:106, 5:107.
- Full Surah Al-Mulk present: 67:1–30 (30 ayahs).
- Length-stratified sampling: at least two ayahs per available 10-word band; sparse bands are reported honestly.
- New model contract: inclusive one-based word-position ranges (`words`), no Arabic transcription.
- Bangla recovery: targeted repair of missing Bangla fragments without changing chunk spans.
- Offline replay and QA: see smoke test result in package validation.
- Live OpenRouter run: not run during packaging; requires the user's `OPENROUTER_API_KEY`.
