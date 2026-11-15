# Test status — v6

- Python syntax / compilation: passed.
- Unit and regression suite: 10 tests passed.
- Offline full Al-Mulk replay: passed; 30 ayahs, 333 Arabic words, 213 chunks.
- Offline QA: 0 failures, 0 warnings; source integrity and Bangla word-by-word coverage passed.
- Reader-data generation: passed for English and Bangla.
- Required live pilot sample configured: 45 unique ayahs / 1,208 words.
- Required anchors present: 2:255, 2:282, 2:286, 4:176, 5:106, 5:107.
- Complete Surah Al-Mulk present: 67:1–30 (30 ayahs).
- Length-stratified sampling: two examples per sufficiently populated 10-word band; sparse bands are reported honestly.
- Attempt/retry logging: tested with a synthetic invalid first response followed by a successful retry; both raw responses and full prompts were archived and linked.
- Source trace: exact numbered Arabic text, English/Bangla WBW glosses, and full-ayah references are embedded in validated raw results and can be exported beside final chunks.
- Historical v5 retries: four retry-resolved validation failures recorded; original raw model payloads were not present in the uploaded historical archive and are explicitly marked unavailable.
- Live v6 OpenRouter run: not run during packaging; requires the user's `OPENROUTER_API_KEY`.
