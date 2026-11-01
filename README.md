# `README.md`

# Ruqya Quran

A desktop player for Quranic Ruqya recitations, built with PySide6 and
Qt Quick. It plays ayah-by-ayah audio from several reciters, shows the
Arabic text with a translation and optional word-by-word breakdown, and
supports A-B looping, per-ayah/per-section repeats, and **self-contained
`.ruqya` playlists** — a single JSON file plus a `data/` folder that
holds every audio and text file it needs.

Open the folder on another machine and it just works.

> **Deploy, MIME setup, troubleshooting:** [`docs/INSTALL.md`](docs/INSTALL.md)
>
> **Data folder contract (what `data/` must contain):** [`docs/DATA-SCHEMA.md`](docs/DATA-SCHEMA.md)
>
> **Full feature list, keyboard shortcuts, config keys, "make your own
> playlist" walkthrough:** [`docs/REFERENCE.md`](docs/REFERENCE.md)

---

## Features

- Curated Ruqya playlist (Fatiha, Ayatul Kursi, the last three surahs, more)
- Portable `.ruqya` playlists — data travels with the file
- Six reciters, three translations (English, two Bengali), switchable live
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
ruqya-quran /path/to/Ruqya/ruqya.ruqya
```

Where `/path/to/Ruqya/` holds a `.ruqya` file and a sibling `data/`
folder. The path is whatever you like — the app carries no default.

Full deployment details (what `make install` writes, how to verify the
MIME association, how to build a `.deb`) are in
[`docs/INSTALL.md`](docs/INSTALL.md).

### Don't have a `.ruqya` playlist yet?

The repo ships **no data** — it's a player, not a download. Two ways to
get a working playlist:

1. **Grab one from elsewhere.** Copy any `.ruqya` file plus its
   `data/` folder to your machine and open it.
2. **Build one.** You need QUL JSON exports in `tools/raw/`, then:

   ```bash
   export RUQYA_DATA_ROOT=~/Ruqya     # where your playlist + data will live
   make dev && make init
   make bundle-fast                   # JSON only — fast
   make bundle                        # + MP3s (~2.5 GB) — slow
   make run                           # opens $RUQYA_DATA_ROOT/ruqya.ruqya
   ```

   `RUQYA_DATA_ROOT` is a **developer convenience** — see
   [Where the data lives](#where-the-data-lives) and
   [Development](#development).

---

## Where the data lives

Every `.ruqya` file is self-contained. The `data_dir` field inside it
(default `data`) points at the folder holding its audio, words, and
translations — **resolved relative to the `.ruqya` file itself**. The
app has no global data path.

```
/path/to/Ruqya/
├── ruqya.ruqya       ← playlist (JSON)
└── data/             ← everything it plays
    ├── VERSION
    ├── audio/
    │   └── <reciter>/<surah>_<ayah>.mp3
    ├── meta/
    │   └── surahs.json
    ├── recitations/
    │   └── <reciter>.json
    ├── script/
    │   └── words.json
    ├── translations/
    │   └── <edition>.json
    └── wbw/
        ├── en.json
        └── bn.json
```

Copy that whole folder to another machine and open the `.ruqya` file —
same app, same experience. No environment variables at runtime, no
default install path, no network required.

`RUQYA_DATA_ROOT` is read **only** by `tools/fetch_qul.py`,
`tools/combine.py`, and the `Makefile`'s `bundle*` targets. The shipped
application never reads it. If you're not building data, ignore it.

The full data folder contract — every JSON key the app reads — is in
[`docs/DATA-SCHEMA.md`](docs/DATA-SCHEMA.md).

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
| `data_dir` | Folder for audio/text/words, **resolved relative to the `.ruqya` file** | `data` |
| `offline` | If `true`, never touch the network | `false` |
| `preload_reciters` | Reciters to warm on open (overrides config) | config value |
| `preload_translations` | Translations to warm on open (overrides config) | config value |

`data_dir` may also be an absolute path if you want the playlist to
point outside its own folder — useful for sharing one large `data/`
across multiple playlists on the same machine.

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

## Building the bundled data

The `data/` folder is a **derived artifact** — generated once by
`tools/fetch_qul.py` from QUL JSON exports. It's not meant to be edited
by hand.

### Prerequisites

QUL JSON exports in `tools/raw/`. Exactly what to download from where
is in [`tools/raw/DATA_SOURCE.adoc`](tools/raw/DATA_SOURCE.adoc).

### Build

```bash
export RUQYA_DATA_ROOT=~/Ruqya

make dev             # create .venv, install editable + dev tools
make init            # write $RUQYA_DATA_ROOT/ruqya.ruqya if missing
make bundle-fast     # JSON only — fast, validates tokenization
make bundle          # JSON + MP3s (~2.5 GB) — slow
```

The build is resume-safe: `.mp3.part` files are renamed on completion and
resumed via HTTP Range requests.

### One reciter for smoke tests

```bash
make bundle-sudais    # only Sudais; removes other reciters first
make bundle-reciter R=ar.alafasy
```

### Validate without re-bundling

```bash
.venv/bin/python tools/fetch_qul.py --validate-only
```

Checks that recitation segments align with `script/words.json`. Warnings
here are **harmless** — see [`docs/KNOWN-NON-ISSUES.md`](docs/KNOWN-NON-ISSUES.md).

### Clean up

```bash
make bundle-clean    # delete $RUQYA_DATA_ROOT/data/ (asks first)
```

---

## Development

Requires Python 3.10+.

```bash
make dev          # create .venv, install editable + dev tools
make run          # run from source
make check        # ruff + validate .desktop + xmllint on MIME xml
make combined     # build combined.txt (project dump for LLM context)
make doctor       # check every prerequisite
```

### `RUQYA_DATA_ROOT`

One variable, one purpose: tell the **build tools** where your dev
playlist and its `data/` live. It is read by:

- the `Makefile` (`init`, `bundle`, `bundle-fast`, `bundle-one`,
  `bundle-sudais`, `bundle-reciter`, `bundle-clean`, `run`)
- `tools/fetch_qul.py` (when no `--playlist` / `--out` is given)
- `tools/combine.py` (when no explicit CLI arg is given)

The shipped app never reads it. `ruqya-quran foo.ruqya` resolves
`data_dir` next to the playlist, always.

### Overrides

Every build target accepts an explicit argument when you don't want to
export `RUQYA_DATA_ROOT`:

```bash
make bundle RUQYA_DATA_ROOT=/media/ismail/8TBRaid0/_IslamQuranApp
python3 tools/fetch_qul.py --playlist /media/.../ruqya.ruqya
python3 tools/fetch_qul.py --out      /media/.../data
python3 tools/combine.py combined.txt 500 /media/.../data
```

`make run` with `RUQYA_DATA_ROOT` unset starts the app in empty state
(no playlist auto-opened). Passing a playlist path explicitly always
works and ignores the env var:

```bash
make run ARGS=/media/ismail/8TBRaid0/_IslamQuranApp/ruqya.ruqya
```

### Debian package

```bash
sudo apt install build-essential devscripts debhelper dh-python \
    pybuild-plugin-pyproject python3-all python3-setuptools lintian
export DEBFULLNAME="Your Name" DEBEMAIL="you@example.com"
make deb-version
make deb-deps
make check
make deb
make deb-lint
```

See [`docs/INSTALL.md`](docs/INSTALL.md#debian-package) for the full
flow, including the "deactivate your venv first" caveat.

---

## Config

`~/.config/ruqya-quran/config.json` is created on first launch from
packaged defaults and never overwritten. It holds reciter/translation
lists, font paths, download tuning, and the word-by-word language. Full
key list is in [`docs/INSTALL.md`](docs/INSTALL.md#requirements) and
[`docs/REFERENCE.md`](docs/REFERENCE.md).

`make purge` deletes it (asks first). Playlists are never touched.

---

## License

MIT. See `LICENSE`.

---