# Known non-issues

> **To LLM reviewers:** these look like bugs from the source alone but are intentional.

---

## Surah 9 has no Bismillah prelude

`needs_bismillah(surah)` returns `surah not in (1, 9)`.

- Surah 1 already begins with the Bismillah as ayah 1, so playing a prelude would double-play it.
- Surah 9 (At-Tawbah) has no Bismillah by tradition.
- QUL audio never embeds a Bismillah in the first-ayah file, so the prelude is the sole source for other surahs.

Do not revert to `surah != 1`.

---

## Bismillah prelude uses the reciter's 1:1 audio

`PlaylistLoader` loads `(1, 1)` as the prelude. It is not a special file — it is the reciter's own Fatiha ayah 1, which is the Bismillah. Playing it before a section naturally matches the reciter's voice.

---

## Custom items have no word-level timing

`clips/*.mp3` items have no segments or script. Underline, hover tooltips, and word marks are unavailable for them. Playback, repeat, and A-B loop still work at the clip level. This is intentional — no reliable external timing source exists for user-supplied audio.