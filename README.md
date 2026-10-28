# Ruqya Quran

A desktop player for Quranic Ruqya recitations, built with PySide6 and Qt Quick.
It plays ayah-by-ayah audio from several reciters, shows the Arabic text with a
translation and optional word-by-word breakdown, and supports A-B looping,
per-ayah/per-section repeats, and **self-contained `.ruqya` playlists** you can
carry around — a single JSON file plus a `data/` folder that holds every audio
and text file it needs.

Open the folder on another machine and it just works, or let the app download
any missing pieces on first run.

---

## Table of contents

1. [Requirements](#requirements)
2. [Deploy — the short version](#deploy--the-short-version)
3. [What `make install` actually does](#what-make-install-actually-does)
4. [Verifying the install — the double-click test](#verifying-the-install--the-double-click-test)
5. [How double-click works (the MIME chain)](#how-double-click-works-the-mime-chain)
6. [The `.ruqya` playlist format](#the-ruqya-playlist-format)
7. [Full Make command reference](#full-make-command-reference)
8. [Files and locations](#files-and-locations)
9. [Configuration](#configuration)
10. [Keyboard shortcuts](#keyboard-shortcuts)
11. [Troubleshooting](#troubleshooting)
12. [Debian package](#debian-package)
13. [License](#license)

---

## Requirements

### System packages (Debian / Ubuntu)

| Package | Why |
|---|---|
| `python3`, `python3-venv` | Runtime and venv support |
| `pipx` | Isolated install — the recommended deploy path |
| `make` | All project commands |
| `desktop-file-utils` | `desktop-file-validate` and `update-desktop-database` |
| `shared-mime-info` | `update-mime-database` — registers the `*.ruqya` MIME type |
| `xdg-utils` | `xdg-mime` — sets the default handler for `.ruqya` |
| `libxml2-utils` | Optional: `xmllint` sanity-checks the MIME XML |
| `fonts-hosny-amiri` | Arabic text (Amiri Quran) |
| `fonts-noto-core` | Bengali text (Noto Sans Bengali) |
| `libxcb-cursor0` | Qt 6 on X11 |

```bash
sudo apt install python3 python3-venv make pipx desktop-file-utils \
    shared-mime-info xdg-utils libxml2-utils \
    fonts-hosny-amiri fonts-noto-core libxcb-cursor0
```

### Python dependencies

Declared in `pyproject.toml` — there is no `requirements.txt` to maintain.

| Package | Version |
|---|---|
| PySide6 | ≥ 6.6.0 |
| requests | ≥ 2.28.0 |

Development extras (`build`, `ruff`) are installed by `make dev`; you don't need
them to deploy.

### Network

Needed **only** when a playlist's `data/` folder is missing files, for:

- `everyayah.com` — audio (primary)
- `cdn.islamic.network` — audio (fallback)
- `api.alquran.cloud` — text and translations
- `api.quran.com` — word-by-word

A playlist with `"offline": true` never touches the network; missing items
appear as errors in the sidebar instead.

---

## Deploy — the short version

```bash
git clone <your-repo-url> ruqya-quran
cd ruqya-quran
make doctor                       # checks prerequisites
make install                      # deploy everything (see below)
ruqya-quran examples/Ruqya/default.ruqya
```

After `make install` you have, from every angle:

- **Application menu** — "Ruqya Quran" appears
- **Command line** — `ruqya-quran` works (if `~/.local/bin` is on `PATH`)
- **Double-click** — any `.ruqya` file opens in Ruqya Quran
- **File → Open** in the app — opens any `.ruqya` file

Re-running `make install` upgrades an existing install without touching your
config or your playlists.

---

## What `make install` actually does

`make install` runs three things in order. Nothing is silent — this is
everything that touches your disk.

```make
install:
	pipx install --force .
	$(MAKE) desktop mime
```

### Step 1 — `pipx install --force .`

Installs the Python package into an isolated venv managed by pipx.

| What | Where |
|---|---|
| venv | `~/.local/pipx/venvs/ruqya-quran/` |
| Executable symlink | `~/.local/bin/ruqya-quran` → `~/.local/pipx/venvs/ruqya-quran/bin/ruqya-quran` |
| Registry entry | `~/.local/pipx/pipx_metadata.json` |

`pipx` puts the executable in a dedicated bin dir — the Makefile asks pipx
where that is with `pipx environment --value PIPX_BIN_DIR`, so this works even
if you've configured pipx to use a custom location.

### Step 2 — `make desktop`

Installs the launcher and icon, with the `Exec=` path rewritten to point at the
binary pipx just installed.

```make
desktop:
	desktop-file-validate data/ruqya-quran.desktop
	install -d $(APPS_DIR)
	sed 's|^Exec=.*|Exec=$(BIN_DIR)/ruqya-quran %f|' \
	  data/ruqya-quran.desktop > $(APPS_DIR)/ruqya-quran.desktop
	install -Dm644 data/icons/hicolor/256x256/apps/ruqya-quran.png \
	  $(ICON_DIR)/ruqya-quran.png
	-update-desktop-database $(APPS_DIR)
	-gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor
```

| What | Where |
|---|---|
| Menu entry | `~/.local/share/applications/ruqya-quran.desktop` |
| Icon | `~/.local/share/icons/hicolor/256x256/apps/ruqya-quran.png` |
| Menu cache | `~/.local/share/applications/mimeinfo.cache` (regenerated) |
| Icon cache | `~/.local/share/icons/hicolor/icon-theme.cache` (regenerated) |

The **`Exec=` line is filled in from the pipx bin dir**, so the menu entry
launches exactly the binary pipx installed. The trailing `%f` is what makes
double-click work — it's the placeholder the file manager replaces with the
path of the file you double-clicked.

Example of the resulting line:

```ini
Exec=/home/you/.local/bin/ruqya-quran %f
```

### Step 3 — `make mime`

Registers the `application/x-ruqya-playlist` MIME type and associates `.ruqya`
files with Ruqya Quran.

```make
mime:
	install -Dm644 data/ruqya-quran-playlist.xml \
	  ~/.local/share/mime/packages/ruqya-quran-playlist.xml
	-update-mime-database ~/.local/share/mime
	-xdg-mime default ruqya-quran.desktop application/x-ruqya-playlist
```

| What | Where |
|---|---|
| MIME type definition | `~/.local/share/mime/packages/ruqya-quran-playlist.xml` |
| MIME database | `~/.local/share/mime/` (regenerated) |
| Default handler | `~/.config/mimeapps.list` (updated by `xdg-mime`) |

The XML file declares:

```xml
<mime-type type="application/x-ruqya-playlist">
  <comment>Ruqya playlist</comment>
  <sub-class-of type="application/json"/>
  <glob pattern="*.ruqya"/>       <!-- ← this is what makes double-click work -->
  <icon name="ruqya-quran"/>
</mime-type>
```

`xdg-mime default` then writes to `~/.config/mimeapps.list`:

```ini
[Default Applications]
application/x-ruqya-playlist=ruqya-quran.desktop;
```

That's the whole association. Your existing defaults for other file types are
untouched.

### What does **not** get touched

- Your playlists — wherever you keep `.ruqya` files, `make install` never
  reads or writes them
- Your config — `~/.config/ruqya-quran/config.json` is only created if missing
- Your other defaults in `~/.config/mimeapps.list` for other file types
- Any files at `/usr/` — everything is per-user under `~/.local/` and `~/.config/`

---

## Verifying the install — the double-click test

If `make install` was clean, these five commands prove it end-to-end. Run them
in order and stop at the first failure.

### 1. Binary exists and runs

```bash
which ruqya-quran
# → /home/you/.local/bin/ruqya-quran

readlink -f ~/.local/bin/ruqya-quran
# → /home/you/.local/pipx/venvs/ruqya-quran/bin/ruqya-quran
```

If `which` returns nothing, `~/.local/bin` isn't on `$PATH`. Fix once with:

```bash
pipx ensurepath
# open a new terminal (or `exec $SHELL -l`)
```

The desktop launcher works regardless — it uses the absolute path.

### 2. Menu entry exists and has the right `Exec=`

```bash
grep -E '^(Exec|MimeType)=' ~/.local/share/applications/ruqya-quran.desktop
```

Expected:

```ini
Exec=/home/you/.local/bin/ruqya-quran %f
MimeType=application/x-ruqya-playlist;
```

The `Exec=` path must match the symlink from step 1. If it doesn't, re-run
`make desktop` (the Makefile asks pipx for the bin dir at that moment).

### 3. MIME type is registered

```bash
xdg-mime query filetype examples/Ruqya/default.ruqya
```

Expected:

```
application/x-ruqya-playlist
```

If this returns `text/plain` or `application/octet-stream`, the MIME XML isn't
being read. Re-run `make mime` and check:

```bash
ls -l ~/.local/share/mime/packages/ruqya-quran-playlist.xml
# should exist
update-mime-database ~/.local/share/mime
```

### 4. Default app is associated

```bash
xdg-mime query default application/x-ruqya-playlist
```

Expected:

```
ruqya-quran.desktop
```

If empty, `xdg-mime default` didn't run — re-run `make mime`.

### 5. End-to-end: simulate the double-click

```bash
gio open examples/Ruqya/default.ruqya
```

This is exactly what your file manager does on double-click. If the window
opens and loads the playlist, double-click in your file manager will too.

If step 5 fails but 1–4 all passed, your file manager is caching the old
association. Log out and back in, or restart the file manager
(`nautilus -q` / `dolphin --replace` / `thunar -q`).

---

## How double-click works (the MIME chain)

Understanding the chain makes any failure obvious. When you double-click a
`.ruqya` file, the system walks five links:

```
┌───────────────────────┐
│  ~/.local/share/mime/ │  shared-mime-info reads this
│  packages/…-playlist  │  sees <glob pattern="*.ruqya"/>
│  .xml                 │  → registers application/x-ruqya-playlist
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  query filetype       │  "what MIME is foo.ruqya?"
│  foo.ruqya            │  → application/x-ruqya-playlist
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  ~/.config/           │  "who handles application/x-ruqya-playlist?"
│  mimeapps.list        │  → ruqya-quran.desktop
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│  ~/.local/share/      │  reads Exec=
│  applications/        │  → /home/you/.local/bin/ruqya-quran %f
│  ruqya-quran.desktop  │  (that's the pipx-installed binary)
└──────────┬────────────┘
           │
           ▼
   launches: ruqya-quran /path/to/foo.ruqya
```

Each link fails in a distinct, testable way:

| Link broken | Symptom | Fix |
|---|---|---|
| 1 — MIME XML missing | `xdg-mime query filetype` returns wrong type | `make mime` |
| 2 — glob wrong | Correct type but wrong extension | Check `<glob pattern="*.ruqya"/>` |
| 3 — no default app | `xdg-mime query default` empty | `make mime` (runs `xdg-mime default`) |
| 4 — `.desktop` missing or `Exec=` bad | App not in menu, or launches nothing | `make desktop` |
| 5 — file manager cache | All the above correct but still not opening | Log out / restart FM |

`make install` covers links 1–4 in one go. Link 5 is on your file manager.

**Answer to "does double-click work with pipx install?"** — Yes, because:

- `make install` runs `pipx install` **and then** `make desktop` **and then** `make mime`
- `make desktop` rewrites `Exec=` to the pipx bin dir at that moment
- `make mime` writes the association

The only way it breaks is if pipx's bin dir changes *after* `make install`
(e.g. you reinstall pipx configured for a different path). In that case,
just re-run `make desktop`.

---

## The `.ruqya` playlist format

A `.ruqya` file is JSON with a small header and a list of items. All audio and
text live next to it in `data/` (configurable via `data_dir`).

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

The whole folder is portable — copy it to another machine and it just works.
Missing audio/text is downloaded on first open unless `"offline": true`.

---

## Full Make command reference

Run `make` or `make help` to list everything from the terminal.

### Development

| Command | What it does |
|---|---|
| `make dev` | Creates `.venv` and installs editable with dev tools (`build`, `ruff`) |
| `make run` | Runs the app from source inside `.venv` — no install needed |
| `make check` | Lints with ruff, validates `.desktop`, sanity-checks the MIME XML |
| `make fix` | Auto-fixes lint problems where safe |
| `make build` | Builds an sdist and wheel into `dist/` |

### Deploy to this machine

| Command | What it does |
|---|---|
| `make install` | **The full deploy**: `pipx install` + `make desktop` + `make mime` |
| `make install-dev` | Same, but editable — code changes apply without reinstalling |
| `make desktop` | Only install the menu entry and icon |
| `make mime` | Only register the `*.ruqya` MIME type and default association |
| `make uninstall` | Remove the app, menu entry, icon, and MIME registration. **Keeps your config and playlists** |
| `make purge` | Delete `~/.config/ruqya-quran` (asks first). Your playlists are not touched — they live wherever you put them |
| `make clean` | Remove `build/`, `dist/`, `*.egg-info`, `__pycache__` |
| `make distclean` | `clean` + remove `.venv` |
| `make doctor` | Check every prerequisite: `python3`, `pipx`, `desktop-file-validate`, `xdg-mime`, `update-mime-database`, fonts, the desktop/icon/MIME sources, and the example playlist |

### Debian package

| Command | What it does |
|---|---|
| `make deb-deps` | Installs build tools via apt (uses sudo) |
| `make deb-version` | Adds a `debian/changelog` entry for the current `__version__` |
| `make deb` | Builds the `.deb` into `dist/` |
| `make deb-lint` | Runs `lintian` on the built package |
| `make deb-install` | Installs the built `.deb` via `apt` |
| `make deb-uninstall` | Removes the `.deb` (keeps user config) |
| `make deb-clean` | Removes Debian build leftovers |

### Variables

```bash
make install PREFIX=/usr/local      # system-wide install (needs sudo)
make desktop PREFIX=/usr/local
```

`PREFIX` defaults to `$(HOME)/.local`. The Makefile queries pipx for its bin
dir at build time, so `Exec=` is always the correct absolute path.

---

## Files and locations

| What | Where |
|---|---|
| Executable | pipx bin dir — default `~/.local/bin/ruqya-quran` |
| Menu entry | `~/.local/share/applications/ruqya-quran.desktop` |
| Icon | `~/.local/share/icons/hicolor/256x256/apps/ruqya-quran.png` |
| MIME definition | `~/.local/share/mime/packages/ruqya-quran-playlist.xml` |
| Default handler | `~/.config/mimeapps.list` — managed by `xdg-mime` |
| Global config | `~/.config/ruqya-quran/config.json` |
| Playlists | Anywhere you keep `.ruqya` files |
| Playlist data | `<folder-of-.ruqya>/<data_dir>/` |

`XDG_CONFIG_HOME` and `XDG_DATA_HOME` are respected. `config.json` is created
on first run and never overwritten. To reset, delete it and restart the app.

### Playlist data folder

```
<folder-of-playlist>/
├── default.ruqya
└── data/
    ├── audio/{reciter}/{surah}_{ayah}.mp3
    ├── text/{edition}/surah_{n}.json
    ├── words/{lang}/{surah}_{ayah}.json
    └── clips/*.mp3
```

The `data/` folder is disposable — delete a subfolder and the app re-downloads
on next open (unless the playlist is offline).

If `data_dir` is not writable (e.g. mounted read-only), downloads fall back to
`~/.local/share/ruqya-quran/<hash>/` and a warning is logged. This lets you
open playlists from read-only media without corrupting the originals.

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
session only. Changing them in the Settings dialog updates the global config,
not the playlist file.

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

## Troubleshooting

**`make install` finishes but `ruqya-quran` isn't found.**
`~/.local/bin` isn't on `$PATH`. Run `pipx ensurepath`, open a new terminal.
The menu entry and double-click still work — they use the absolute path.

**Menu entry doesn't appear.**
Run `make desktop`, then log out and back in (or `update-desktop-database
~/.local/share/applications`). Confirm:

```bash
grep ^Exec= ~/.local/share/applications/ruqya-quran.desktop
# → Exec=/home/you/.local/bin/ruqya-quran %f
```

The path in `Exec=` must exist. If you moved pipx or reinstalled it elsewhere,
re-run `make desktop`.

**Double-click on `.ruqya` doesn't open Ruqya Quran.**
Walk the chain in [How double-click works](#how-double-click-works-the-mime-chain):

```bash
# 1. MIME type registered?
xdg-mime query filetype examples/Ruqya/default.ruqya
# → application/x-ruqya-playlist

# 2. Handler associated?
xdg-mime query default application/x-ruqya-playlist
# → ruqya-quran.desktop

# 3. Desktop file exists and has Exec=?
grep ^Exec= ~/.local/share/applications/ruqya-quran.desktop

# 4. Simulate the double-click
gio open examples/Ruqya/default.ruqya
```

Whichever step returns the wrong thing is the fix. For 1 or 2, `make mime`.
For 3, `make desktop`. If all pass but double-click still fails, log out —
your file manager cached the old association.

**`xdg-mime default` set the right association but Nautilus still opens the editor.**
Nautilus caches preferences per user. `nautilus -q` and reopen. If that fails,
log out and back in once.

**`Makefile:NN: *** missing separator`.**
Recipe lines must begin with a **tab**, not spaces. Your editor may have
converted them.

**Arabic or Bengali text shows as boxes.**
Fonts missing, or `font_file` / `bangla_font_file` in `config.json` wrong.
Run `make doctor`.

**Qt fails with "could not load the Qt platform plugin xcb".**
Install `libxcb-cursor0`.

**Playlist data folder not writable.**
If you opened a playlist from a read-only location, downloads go to
`~/.local/share/ruqya-quran/<hash>/` instead. A warning is logged. To keep
everything together, copy the folder to a writable location.

**First open is slow.**
It warms every reciter in `preload_reciters`. Set the playlist's
`preload_reciters` (or the config's) to just the reciter you use. Or copy a
populated `data/` folder next to the `.ruqya` file.

**`pipx: command not found` after install.**
Run `pipx ensurepath` and open a new terminal.

---

## Debian package

The `.deb` builds on top of the `debian/` control files. Full flow:

```bash
# 1. Install build tools (once)
sudo apt install build-essential devscripts debhelper dh-python \
    pybuild-plugin-pyproject python3-all python3-setuptools lintian

# 2. Create the changelog (once)
dch --create -v 0.1.0 --package ruqya-quran

# 3. Set your identity (add to ~/.bashrc or ~/.zshrc)
export DEBFULLNAME="Ismail"
export DEBEMAIL="your@email.com"

# 4. Build
deactivate                # leave any active venv
make deb-version
make deb-deps
make check
make deb
make deb-lint

# 5. Install
make uninstall            # remove the pipx version first
make deb-install
```

Notes:

- The `.deb` installs to `/usr/bin/ruqya-quran` and
  `/usr/lib/python3/dist-packages/ruqya_quran/`
- `.desktop` and icon go to `/usr/share/applications/` and
  `/usr/share/icons/hicolor/256x256/apps/`
- To also register the MIME type **system-wide**, add
  `data/ruqya-quran-playlist.xml` to `debian/ruqya-quran.install` under
  `/usr/share/mime/packages/`, and run `update-mime-database /usr/share/mime`
  in `debian/ruqya-quran.postinst`. This is optional — the pipx route
  (`make install`) already handles MIME per-user
- `make seed` and `make extras` no longer exist — seed data lives in the
  example workspace under `examples/Ruqya/data/`

---

## License

MIT. See `LICENSE`.

---

## Notes on what I changed

**New sections:**
- "What `make install` actually does" — traces all three sub-targets (`pipx install`, `desktop`, `mime`) with exact paths written
- "Verifying the install — the double-click test" — five commands, one per link in the chain
- "How double-click works (the MIME chain)" — ASCII diagram + failure table, so any breakage is self-diagnosable

**Answers your specific concern about pipx + double-click:**
The README now explicitly explains *why* `make install` keeps double-click working: `pipx install` runs first, `make desktop` reads pipx's bin dir at that moment and writes the correct absolute `Exec=`, `make mime` writes the association. If pipx's bin dir changes later, just re-run `make desktop`.

**Removed/rewrote from old README:**
- All references to `~/.cache/ruqya-quran/` → workspace `data/`
- `custom_playlist.json` section → `.ruqya` items
- `make seed` / `make seed-export` / `make extras` tables → gone (targets deleted)
- `extras/` and `seed/` in project layout → `examples/Ruqya/data/`
- "Files and locations" — now accurate to workspace model
- Debian notes — no longer references deleted targets

**One thing to verify on first run** — after `make install`, run the five commands in "Verifying the install". If step 5 (`gio open examples/Ruqya/default.ruqya`) opens the app, you're done. If it doesn't, the output of step 1–4 tells you which `make` target to re-run.