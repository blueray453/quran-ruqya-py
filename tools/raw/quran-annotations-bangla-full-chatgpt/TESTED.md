# Local validation performed for this package

The following checks were run with Python 3 and no OpenRouter API key:

- `python -m compileall -q qa.py build.py ayah_length_counter.py tools`
- `python qa.py --surah 67`
- `./smoke_test.sh`

Smoke-test result:

- 30 Al-Mulk ayahs replayed from the bundled reviewed sample.
- 333 Arabic words aligned and covered exactly once.
- 213 flat chunks produced.
- English and Bangla chunk spans matched.
- QA: 0 FAIL.
- Chunker comparison generated as a diagnostic only.
- English and Bangla reader data built successfully.
- No model API calls and no API cost.

This replay validates the software path and data contract. It does not benchmark the quality
of a live LLM's segmentation decisions.
