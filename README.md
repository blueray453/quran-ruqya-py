Here is the full `README.md`. The requirements section is built from your code, `pyproject.toml` and the Makefile rather than the old `pip freeze` output. The dependency list is much shorter than your old `requirements.txt` because pip pulls in transitive packages automatically.

````markdown
# Ruqya Quran

A desktop player for Quranic Ruqya recitations, built with PySide6 and Qt Quick.
It plays ayah-by-ayah audio from several reciters, shows the Arabic text with a
translation and optional word-by-word breakdown, and supports A-B looping and a
custom playlist of your own audio files.

The first run downloads text and audio; after that it works offline.

## Features

- Curated Ruqya playlist (Fatiha, Ayatul Kursi, the last three surahs, and more)
- Four reciters and three translations (English, two Bengali), switchable live
- Word-by-word breakdown (English or Bengali)
- A-B loop with a configurable pass count
- Custom playlist ("Duas") from your own audio files
- Light/dark theme, adjustable text size, keyboard shortcuts
- Offline after the first run, with a pre-seedable cache

## Requirements

### System (Debian / Ubuntu)

| Requirement | Why | Package |
|---|---|---|
| Python 3.10+ | Runtime | `python3`, `python3-venv` |
| pipx | Isolated install | `pipx` |
| make | Project commands | `make` |
| desktop-file-utils | Validates and registers the menu entry | `desktop-file-utils` |
| Amiri Quran font | Arabic text | `fonts-hosny-amiri` |
| Noto Sans Bengali font | Bengali text | `fonts-noto-core` |
| XCB cursor library | Qt on X11 | `libxcb-cursor0` |

```bash
sudo apt install python3 python3-venv make pipx desktop-file-utils \
    fonts-hosny-amiri fonts-noto-core libxcb-cursor0
```

Font paths are set in `config.json`. If your fonts live elsewhere, change
`font_file` and `bangla_font_file` there.

### Python dependencies

Declared in `pyproject.toml` (there is no `requirements.txt` to maintain):

| Package | Version |
|---|---|
| PySide6 | >= 6.6.0 |
| requests | >= 2.28.0 |

Development extras (`build`, `ruff`) are installed by `make dev`.

### Network

Needed on first run only, for these services:

- everyayah.com (audio, primary)
- cdn.islamic.network (audio, fallback)
- api.alquran.cloud (text and translations)
- api.quran.com (word-by-word)

## Quick start

```bash
git clone <your-repo-url> ruqya-quran
cd ruqya-quran
make doctor      # check prerequisites
make install     # deploy: pipx + menu entry + icon + extras + cache seed
ruqya-quran      # or launch it from your application menu
```

## Project layout

```
ruqya-quran/
├── Makefile
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── src/
│   └── ruqya_quran/
│       ├── __init__.py              # version lives here
│       ├── __main__.py              # python -m ruqya_quran
│       ├── main.py                  # app logic
│       ├── Main.qml                 # UI
│       ├── config.json              # default config
│       └── custom_playlist.json     # default custom playlist
├── data/
│   ├── ruqya-quran.desktop
│   └── icons/hicolor/256x256/apps/ruqya-quran.png
├── extras/                          # your own audio files
├── seed/                            # optional: pre-downloaded cache
│   ├── audio/
│   ├── metadata/
│   └── wbw/
└── docs/
    └── API.txt
```

## Make commands

Run `make` or `make help` to list everything.

### Development

| Command | What it does |
|---|---|
| `make dev` | Creates `.venv` and installs the project in editable mode with dev tools |
| `make run` | Runs the app from source inside `.venv` (no install needed) |
| `make check` | Lints the code with ruff and validates the `.desktop` file |
| `make build` | Builds an sdist and wheel into `dist/` |

### Deploy to this machine

| Command | What it does |
|---|---|
| `make install` | `pipx install`, then installs the menu entry, icon, extras and cache seed |
| `make install-dev` | Same, but editable: code changes apply without reinstalling |
| `make desktop` | Only the `.desktop` file and icon |
| `make extras` | Only copies `extras/` to `~/.config/ruqya-quran/extras/` |
| `make seed` | Only seeds `~/.cache/ruqya-quran/` from `seed/` |
| `make seed-export` | Snapshots the current `~/.cache/ruqya-quran/` into `seed/` |

Re-running `make install` upgrades an existing install. `extras` and `seed`
never overwrite files that already exist.

### Remove and clean up

| Command | What it does |
|---|---|
| `make uninstall` | Removes the app, menu entry and icon. Keeps your config and cache |
| `make purge` | Deletes `~/.config/ruqya-quran` and `~/.cache/ruqya-quran` (asks first) |
| `make clean` | Removes `build/`, `dist/`, `*.egg-info` and `__pycache__` |
| `make distclean` | `clean` plus removes `.venv` |

### Diagnostics

| Command | What it does |
|---|---|
| `make doctor` | Checks for python3, pipx, desktop-file-validate, fonts, the seed folder, and prints the pipx bin directory |

### Variables

```bash
make seed SEED_DIR=/path/to/seed     # use a different seed source
make desktop PREFIX=/usr/local       # install under a different prefix (may need sudo)
```

The Makefile asks pipx where its bin directory is (`PIPX_BIN_DIR`), so the
`.desktop` file gets the correct absolute `Exec=` path even if pipx is
configured with a custom location.

## Running without make

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m ruqya_quran
```

## Files and locations

| What | Where |
|---|---|
| Executable | pipx bin directory (default `~/.local/bin/ruqya-quran`) |
| Menu entry | `~/.local/share/applications/ruqya-quran.desktop` |
| Icon | `~/.local/share/icons/hicolor/256x256/apps/ruqya-quran.png` |
| Config | `~/.config/ruqya-quran/config.json` |
| Custom playlist | `~/.config/ruqya-quran/custom_playlist.json` |
| Your audio (extras) | `~/.config/ruqya-quran/extras/` |
| Cache | `~/.cache/ruqya-quran/` |

`XDG_CONFIG_HOME` and `XDG_CACHE_HOME` are respected. Defaults are copied from
the package to `~/.config/ruqya-quran/` on first run and never overwritten, so
your edits survive upgrades. To reset, delete the file and restart the app.

### Cache layout

```
~/.cache/ruqya-quran/
├── audio/{reciter}/{surah}_{ayah}.mp3
├── metadata/{edition}/surah_{surah}.json
└── wbw/{lang}/{surah}_{ayah}.json
```

The cache is disposable: delete it and the app re-downloads what it needs.

## Seeding the cache

To avoid the first-run download on a new machine, put a copy of
`audio/`, `metadata/` and `wbw/` into `seed/` and run `make install` (or
`make seed`). To create the seed from a machine that already has a full cache:

```bash
make seed-export
```

## Configuration

Edit `~/.config/ruqya-quran/config.json`:

| Key | Meaning | Default |
|---|---|---|
| `reciters` | Map of reciter id to display name | 4 reciters |
| `default_reciter` | Reciter used at startup | `ar.abdurrahmaansudais` |
| `translations` | Map of edition id to display name | en, bn x2 |
| `default_translation` | Translation used at startup | `en.sahih` |
| `word_by_word_language` | `en`, `bn` or `auto` (follows translation) | `auto` |
| `preload_reciters` | List of reciters to download on warmup, or `"all"` | all |
| `preload_translations` | List of translations to download on warmup, or `"all"` | all |
| `max_workers` | Parallel download threads | 4 |
| `request_timeout` | Seconds per request | 10 |
| `max_retries` | Retries for transient errors | 2 |
| `retry_backoff_base` | Backoff base in seconds | 0.5 |
| `source_fail_threshold` | Consecutive failures before a host is skipped for the session | 3 |
| `font_file` | Path to the Arabic font | Amiri Quran |
| `bangla_font_file` | Path to the Bengali font | Noto Sans Bengali |
| `custom_playlist_separator_label` | Sidebar heading for custom items | `Duas` |

### Custom playlist

Edit `~/.config/ruqya-quran/custom_playlist.json`. Relative paths resolve
against `~/.config/ruqya-quran/`, so files in `extras/` work as `extras/name.mp3`.

```json
[
  {
    "path": "extras/my-dua.mp3",
    "title": "My dua",
    "body": "Arabic text shown on screen",
    "translation": "Optional translation"
  }
]
```

## Keyboard shortcuts

| Key | Action |
|---|---|
| Space | Play / pause |
| Right / Left | Next / previous |
| Shift+Right / Shift+Left | Seek +5s / -5s |
| Up / Down | Volume up / down |
| M | Mute |
| T | Toggle translation |
| W | Toggle word-by-word |
| L | Cycle repeat (off / one / all) |
| P | Toggle playlist sidebar |
| + / - | Larger / smaller text |
| [ and ] | Mark loop start / end |
| Esc | Clear loop |

## Troubleshooting

**Menu entry doesn't appear or won't launch.** Run `make desktop`, then log out
and back in. Check that `Exec=` in `~/.local/share/applications/ruqya-quran.desktop`
is an absolute path that exists.

**`Makefile:NN: *** missing separator`.** Recipe lines must start with a tab,
not spaces.

**Arabic or Bengali text shows as boxes.** The fonts are missing or the paths in
`config.json` are wrong. Run `make doctor`.

**Qt fails with "could not load the Qt platform plugin xcb".** Install
`libxcb-cursor0`.

**Seed or cache not writable.** The directory may be owned by root from an
earlier `sudo` run: `sudo chown -R "$USER": ~/.cache/ruqya-quran`.

**First run is slow.** It downloads every reciter. Restrict it with
`preload_reciters` in `config.json`, or use the seed.

**`pipx: command not found` after install.** Run `pipx ensurepath` and open a
new terminal.

## Releasing

1. Bump `__version__` in `src/ruqya_quran/__init__.py` (the only place).
2. `make check && make build`
3. Artifacts appear in `dist/`.

## License

MIT. See `LICENSE`.
````

You'll need to create a `LICENSE` file, since `pyproject.toml` references it, and replace `<your-repo-url>` with the real one. One thing worth double-checking: I listed `fonts-noto-core` for the Bengali font because that is where Debian ships `NotoSansBengali-Regular.ttf`. Run `make doctor` once to confirm both font paths resolve on your machine.