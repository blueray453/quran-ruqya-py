# Ruqya Quran

A desktop player for Quranic Ruqya recitations, built with PySide6 and
Qt Quick. It plays ayah-by-ayah audio from several reciters, shows the
Arabic text with a translation and optional word-by-word breakdown, and
supports A-B looping, per-ayah/per-section repeats, and **self-contained
`.ruqya` playlists** — a single JSON file plus a `data/` folder that
holds every audio and text file it needs.

Open the folder on another machine and it just works, or let the app
download any missing pieces on first run.

> **Deploy, MIME setup, troubleshooting:**
> [`docs/INSTALL.md`](docs/INSTALL.md)
>
> **Full feature list, keyboard shortcuts, config keys, "make your own
> playlist" walkthrough:** [`docs/REFERENCE.md`](docs/REFERENCE.md)

---

## Features

- Curated Ruqya playlist (Fatiha, Ayatul Kursi, the last three surahs, more)
- Portable `.ruqya` playlists — data travels with the file
- Four reciters, three translations (English, two Bengali), switchable live
- Word-by-word breakdown with a hover-to-translate bar
- A-B loop, per-ayah repeat, per-section repeat, and whole-playlist loop
- Custom audio items (your own `.mp3` duas) mixed in
- Solarized dark/light, adjustable text size
- Offline playback once the playlist's `data/` is populated
- Double-click `.ruqya` files to open them

See [`docs/REFERENCE.md`](docs/REFERENCE.md) for the full keyboard map.

---

## Quick start

```bash
git clone <your-repo-url> ruqya-quran
cd ruqya-quran
make install
ruqya-quran examples/Ruqya/default.ruqya
```

Full deployment details (what `make install` writes, how to verify the
MIME association, how to build a `.deb`) are in
[`docs/INSTALL.md`](docs/INSTALL.md).

---

## The `.ruqya` playlist format

A `.ruqya` file is JSON with a small header and a list of items. All
audio and text live next to it in `data/` (configurable via `data_dir`).

```json
{
  "format": "ruqya-playlist",
  "version": 1,
  "name": "Default Ruqya",
  "reciter": "ar.abdurrahmaansudais",
  "translation": "en.sahih",
  "data_dir": "data",
  "offline": false,
  "items": [
    { "surah": 1, "from": 1, "to": 7, "description": "Surah Fatiha" },
    { "surah": 2, "from": 255, "to": 257,
      "description": "Ayatul Kursi", "group_repeat": 3 },
    { "surah": 112, "from": 1, "to": 4,
      "description": "Surah Ikhlas", "ayah_repeat": 3 },
    { "path": "clips/my-dua.mp3",
      "title": "My dua",
      "body": "Arabic text shown on screen",
      "translation": "Optional translation",
      "section": "Duas" }
  ]
}
```

### Header fields

| Field | Meaning | Default |
|---|---|---|
| `format` | Must be `ruqya-playlist` | — |
| `version` | Format version | `1` |
| `name` | Window title and playlist label | filename stem |
| `reciter` | Reciter id used when the playlist opens | last used |
| `translation` | Translation edition used when the playlist opens | last used |
| `data_dir` | Folder for audio/text/words, relative to the `.ruqya` file | `data` |
| `offline` | If `true`, never touch the network | `false` |
| `preload_reciters` | Reciters to warm on open (overrides config) | config value |
| `preload_translations` | Translations to warm on open (overrides config) | config value |

### Item fields

| Field | Meaning |
|---|---|
| `surah`, `from`, `to` | Range of ayahs to play |
| `description` | Sidebar label |
| `ayah_repeat` | Play each ayah N times before advancing (0 = ∞) |
| `group_repeat` | Play the whole section N times (0 = ∞) |
| `path` | For custom audio: file path, resolved against `data_dir` |
| `title`, `body`, `translation` | For custom audio: label, Arabic text, translation |
| `section` | Sidebar heading for custom items |

Legacy form also accepted: `{"repeat": 3, "repeat_mode": "group"}` is
equivalent to `{"group_repeat": 3}`.

To build your own playlist and add your own duas, see
[`docs/REFERENCE.md`](docs/REFERENCE.md#making-your-own-playlist).

---

## License

MIT. See `LICENSE`.