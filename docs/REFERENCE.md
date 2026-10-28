# Reference

Detailed tables and step-by-step recipes for Ruqya Quran. For what the
project is and how the playlist format works, see
[`../README.md`](../README.md). For installation and deployment, see
[`INSTALL.md`](INSTALL.md).

---

## Features

- Curated Ruqya playlist (Fatiha, Ayatul Kursi, the last three surahs, more)
- Portable `.ruqya` playlists — data travels with the file
- Four reciters and three translations (English, two Bengali), switchable live
- Word-by-word breakdown (English or Bengali) with a hover-to-translate bar
- A-B loop with a configurable pass count
- Per-ayah repeat (×N), per-section repeat (×N), and whole-playlist loop
- Custom audio items (your own `.mp3` duas) mixed into a playlist
- Light/dark theme (Solarized), adjustable text size
- Offline playback once the playlist's `data/` folder is populated
- Double-click `.ruqya` files to open them

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

## Configuration

Edit `~/.config/ruqya-quran/config.json`. The file is created on first
run and never overwritten — delete it to reset to packaged defaults.

| Key | Meaning | Default |
|---|---|---|
| `reciters` | Map of reciter id to display name | 4 reciters |
| `default_reciter` | Used when a playlist doesn't set one | `ar.abdurrahmaansudais` |
| `translations` | Map of edition id to display name | en, bn ×2 |
| `default_translation` | Used when a playlist doesn't set one | `en.sahih` |
| `word_by_word_language` | `en`, `bn`, or `auto` (follows translation) | `auto` |
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

## Making your own playlist

1. Copy `examples/Ruqya/` somewhere writable (e.g. `~/Ruqya/`).
2. Edit `default.ruqya` — rename `name`, add or remove items, change
   `data_dir` if you want the data folder somewhere else.
3. Drop your own `.mp3` duas into `data/clips/` and reference them with
   `"path": "clips/my-dua.mp3"`.
4. Open with `ruqya-quran ~/Ruqya/default.ruqya` or double-click it.

The whole folder is portable — copy it to another machine and it just
works. Missing audio and text is downloaded on first open unless the
playlist is marked `"offline": true`.

For the full `.ruqya` field reference (header + item keys), see the
"The `.ruqya` playlist format" section of [`../README.md`](../README.md).

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

See [`INSTALL.md`](INSTALL.md) for where the executable, menu entry,
icon, and MIME registration live.
