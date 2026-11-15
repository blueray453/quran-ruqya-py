# Test status

## Offline pipeline replay

- `./smoke_test_offline.sh`
- 30 Al-Mulk ayahs replayed from the bundled reviewed prototype
- 333 Arabic words and 213 flat chunks
- exact ordered source-word coverage
- English/Bangla chunk spans match
- QA: zero failures
- chunker boundary comparison is diagnostic only
- reader data build completes

## Live OpenRouter model smoke test

- `./smoke_test.sh` uses `openai/gpt-6-luna` via OpenRouter
- Includes 2:255, 2:282, 2:286, 4:176, 5:106–107 and stratified ayahs by 10-word length band
- Requires the user's `OPENROUTER_API_KEY` and OpenRouter account credits
- Not run in the packaging environment because no user API key is available
- The script checks validated outputs, source coverage, overlays, QA, reports, and build output
