# Ruqya Quran

A desktop player for Quranic Ruqya recitations, built with PySide6 and
Qt Quick. It plays ayah-by-ayah audio from several reciters, shows the
Arabic text with a translation and optional word-by-word breakdown, and
supports A-B looping, per-ayah/per-section repeats, and **self-contained
`.ruqya` playlists** — a single JSON file plus a `data/` folder that
holds every audio and text file it needs.

Open the folder on another machine and it just works, or let the app
download any missing pieces on first run.

> **Installation, deployment, MIME setup, and troubleshooting** live in
> [`docs/INSTALL.md`](docs/INSTALL.md).

---

## Features

- Curated Ruqya playlist (Fatiha, Ayatul Kursi, the last three surahs, more)
- Portable `.ruqya` playlists — data travels with the file
- Four reciters and three translations (English, two Bengali), switchable live
- Word-by-word breakdown (English or Bengali) with a hover-to-translate bar
- A-B loop with a configurable pass count
- Per-ayah repeat (×N), per-section repeat (×N), and whole-playlist loop
- Custom audio items (your own `.mp3` duas) mixed into a playlist
- Light/dark theme (Solarized), adjustable text size, keyboard shortcuts
- Offline playback once the playlist's `data/` folder is populated
- Double-click `.ruqya` files to open them

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

### Making your own playlist

1. Copy `examples/Ruqya/` somewhere writable (e.g. `~/Ruqya/`).
2. Edit `default.ruqya` — rename `name`, add/remove items, change `data_dir`.
3. Drop your own `.mp3` duas into `data/clips/` and reference them with
   `"path": "clips/my-dua.mp3"`.
4. Open with `ruqya-quran ~/Ruqya/default.ruqya` or double-click.

The whole folder is portable — copy it to another machine and it just
works. Missing audio/text is downloaded on first open unless the playlist
is offline.

---

## Configuration

Edit `~/.config/ruqya-quran/config.json`:

| Key | Meaning | Default |
|---|---|---|
| `reciters` | Map of reciter id to display name | 4 reciters |
| `default_reciter` | Used when a playlist doesn't set one | `ar.abdurrahmaansudais` |
| `translations` | Map of edition id to display name | en, bn ×2 |
| `default_translation` | Used when a playlist doesn't set one | `en.sahih` |
| `word_by_word_language` | `en`, `bn`, or `auto` | `auto` |
| `preload_reciters` | Reciters to warm on open, or `"all"` | all |
| `preload_translations` | Translations to warm on open, or `"all"` | all |
| `max_workers` | Parallel download threads | 4 |
| `request_timeout` | Seconds per request | 10 |
| `max_retries` | Retries for transient errors | 2 |
| `retry_backoff_base` | Backoff base in seconds | 0.5 |
| `source_fail_threshold` | Consecutive failures before a host is skipped for the session | 3 |
| `font_file` | Path to the Arabic font | Amiri Quran |
| `bangla_font_file` | Path to the Bengali font | Noto Sans Bengali |
| `custom_playlist_separator_label` | Sidebar heading for custom items | `Duas` |

Playlist `reciter` / `translation` override the config defaults for that
session only. Changing them in the Settings dialog updates the global
config, not the playlist file.

---

## Keyboard shortcuts

| Key | Action |
|---|---|
| `Space` | Play / pause |
| `→` / `←` | Next / previous |
| `Shift+→` / `Shift+←` | Seek +5s / -5s |
| `↑` / `↓` | Volume up / down |
| `M` | Mute |
| `T` | Toggle translation |
| `W` | Toggle word-by-word |
| `L` | Toggle playlist loop |
| `R` | Cycle ayah repeat (Auto → 1 → 2 → 3 → 5 → 10 → ∞) |
| `G` | Cycle section repeat |
| `O` | Open playlist |
| `P` | Toggle playlist sidebar |
| `D` | Light / dark theme |
| `+` / `-` | Larger / smaller text |
| `[` / `]` | Mark loop start / end |
| `Esc` | Clear loop |

---

## Files and locations

| What | Where |
|---|---|
| Global config | `~/.config/ruqya-quran/config.json` (created on first run) |
| Playlists | Anywhere you keep `.ruqya` files |
| Playlist data | `<folder-of-.ruqya>/<data_dir>/` (default `<folder>/data/`) |

`XDG_CONFIG_HOME` and `XDG_DATA_HOME` are respected. `config.json` is
never overwritten — delete it to reset to packaged defaults.

Playlist data folder:

```
<folder-of-playlist>/
├── default.ruqya
└── data/
    ├── audio/{reciter}/{surah}_{ayah}.mp3
    ├── text/{edition}/surah_{n}.json
    ├── words/{lang}/{surah}_{ayah}.json
    └── clips/*.mp3
```

The `data/` folder is disposable — delete a subfolder and the app
re-downloads on next open (unless the playlist is offline).

See [`docs/INSTALL.md`](docs/INSTALL.md) for where the executable, menu
entry, icon, and MIME registration live.

---

## License

MIT. See `LICENSE`.