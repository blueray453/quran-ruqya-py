# Installing, deploying, and troubleshooting Ruqya Quran

This file covers requirements, the full `make install` chain, how the
`*.ruqya` file association works, verification steps, and every Make
target. For what the app *is* and how to author a playlist, see
[`../README.md`](../README.md).

---

## Table of contents

1. [Requirements](#requirements)
2. [Deploy — the short version](#deploy--the-short-version)
3. [What `make install` actually does](#what-make-install-actually-does)
4. [Verifying the install](#verifying-the-install)
5. [How double-click works](#how-double-click-works)
6. [Full Make command reference](#full-make-command-reference)
7. [Troubleshooting](#troubleshooting)
8. [Debian package](#debian-package)

---

## Requirements

### System packages (Debian / Ubuntu)

| Package | Why |
|---|---|
| `python3`, `python3-venv` | Runtime and venv support |
| `pipx` | Isolated install — the recommended deploy path |
| `make` | All project commands |
| `desktop-file-utils` | `desktop-file-validate`, `update-desktop-database` |
| `shared-mime-info` | `update-mime-database` — registers `*.ruqya` |
| `xdg-utils` | `xdg-mime` — sets the default handler |
| `libxml2-utils` | Optional: `xmllint` sanity-checks the MIME XML |
| `fonts-hosny-amiri` | Arabic text (Amiri Quran) |
| `fonts-noto-core` | Bengali text (Noto Sans Bengali) |
| `libxcb-cursor0` | Qt 6 on X11 |

```bash
sudo apt install python3 python3-venv make pipx desktop-file-utils \
    shared-mime-info xdg-utils libxml2-utils \
    fonts-hosny-amiri fonts-noto-core libxcb-cursor0
```

Font paths are read from `~/.config/ruqya-quran/config.json`, which is
created on first launch from the packaged defaults. The two relevant
keys are `font_file` (Arabic) and `bangla_font_file` (Bengali). If your
fonts live elsewhere, edit those keys and restart the app.

The same file also holds the reciter and translation lists (`reciters`,
`translations`), the default selections (`default_reciter`,
`default_translation`), the preload sets (`preload_reciters`,
`preload_translations`), the word-by-word language
(`word_by_word_language`), download tuning (`request_timeout`,
`max_retries`, `retry_backoff_base`, `source_fail_threshold`,
`max_workers`), and the custom-item sidebar label
(`custom_playlist_separator_label`). `make purge` deletes it and
regenerates the packaged defaults on next launch.

### Python dependencies

Declared in `pyproject.toml`:

| Package | Version |
|---|---|
| PySide6 | ≥ 6.6.0 |
| requests | ≥ 2.28.0 |

Development extras (`build`, `ruff`) are installed by `make dev` — you
don't need them to deploy.

### Network

Needed **only** when a playlist's `data/` folder is missing files, for:

- `everyayah.com` — audio (primary)
- `cdn.islamic.network` — audio (fallback)
- `api.alquran.cloud` — text and translations
- `api.quran.com` — word-by-word

A playlist with `"offline": true` never touches the network.

---

## Deploy — the short version

```bash
git clone <your-repo-url> ruqya-quran
cd ruqya-quran
make doctor                       # checks prerequisites
make install                      # deploy everything (see below)
ruqya-quran examples/Ruqya/ruqya.ruqya
```

After `make install` you have, from every angle:

- **Application menu** — "Ruqya Quran" appears
- **Command line** — `ruqya-quran` works (if `~/.local/bin` is on `PATH`)
- **Double-click** — any `.ruqya` file opens in Ruqya Quran
- **File → Open** in the app — opens any `.ruqya` file

Re-running `make install` upgrades an existing install without touching
your config or your playlists.

---

## What `make install` actually does

`make install` runs three things in order. Nothing is silent.

```make
install:
	pipx install --force .
	$(MAKE) desktop mime
```

### Step 1 — `pipx install --force .`

Installs the Python package into an isolated venv managed by pipx.

| What | Where |
|---|---|
| venv | `~/.local/share/pipx/venvs/ruqya-quran/` |
| Executable symlink | `~/.local/bin/ruqya-quran` → `~/.local/share/pipx/venvs/ruqya-quran/bin/ruqya-quran` |
| Registry entry | `~/.local/share/pipx/pipx_metadata.json` |

The Makefile asks pipx for its bin dir with
`pipx environment --value PIPX_BIN_DIR`, so this works even if you've
configured pipx to use a custom location.

### Step 2 — `make desktop`

Installs the launcher and icon, with `Exec=` rewritten to point at the
binary pipx just installed. The trailing `%f` is what makes double-click
work — the file manager replaces it with the path of the file you clicked.

| What | Where |
|---|---|
| Menu entry | `~/.local/share/applications/ruqya-quran.desktop` |
| Icon | `~/.local/share/icons/hicolor/256x256/apps/ruqya-quran.png` |
| Menu cache | `~/.local/share/applications/mimeinfo.cache` (regenerated) |
| Icon cache | `~/.local/share/icons/hicolor/icon-theme.cache` (regenerated) |

Example of the resulting line:

```ini
Exec=/home/you/.local/bin/ruqya-quran %f
```

### Step 3 — `make mime`

Registers the `application/x-ruqya-playlist` MIME type and associates
`.ruqya` files with Ruqya Quran.

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
  <glob pattern="*.ruqya"/>
  <icon name="ruqya-quran"/>
</mime-type>
```

`xdg-mime default` then writes to `~/.config/mimeapps.list`:

```ini
[Default Applications]
application/x-ruqya-playlist=ruqya-quran.desktop;
```

That's the whole association. Your existing defaults for other file types
are untouched.

### What does **not** get touched

- Your playlists — wherever you keep `.ruqya` files, `make install` never
  reads or writes them
- Your config — `~/.config/ruqya-quran/config.json` is only created if
  missing; an existing file is never overwritten, so reciter/translation
  additions shipped in a new release won't appear in your pickers until
  you edit it by hand or run `make purge` (see
  [Troubleshooting](#troubleshooting))
- Your other defaults in `~/.config/mimeapps.list` for other file types
- Any files at `/usr/` — everything is per-user under `~/.local/` and `~/.config/`

---

## Verifying the install

If `make install` was clean, these five commands prove it end-to-end. Stop
at the first failure.

### 1. Binary exists and runs

```bash
which ruqya-quran
# → /home/you/.local/bin/ruqya-quran

readlink -f ~/.local/bin/ruqya-quran
# → /home/you/.local/share/pipx/venvs/ruqya-quran/bin/ruqya-quran
```

If `which` returns nothing, `~/.local/bin` isn't on `$PATH`. Fix once with
`pipx ensurepath`, then open a new terminal. The desktop launcher and
double-click still work — they use the absolute path.

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
`make desktop` — the Makefile asks pipx for the bin dir at that moment.

### 3. MIME type is registered

```bash
xdg-mime query filetype examples/Ruqya/ruqya.ruqya
```

Expected:

```
application/x-ruqya-playlist
```

If this returns `text/plain` or `application/octet-stream`, the MIME XML
isn't being read. Re-run `make mime`, then check:

```bash
ls -l ~/.local/share/mime/packages/ruqya-quran-playlist.xml
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
gio open examples/Ruqya/ruqya.ruqya
```

This is exactly what your file manager does on double-click. If the
window opens and loads the playlist, double-click in your file manager
will too.

If step 5 fails but 1–4 all passed, your file manager is caching the old
association. Log out and back in, or restart the file manager
(`nautilus -q` / `dolphin --replace` / `thunar -q`).

---

## How double-click works

Understanding the chain makes any failure obvious. When you double-click
a `.ruqya` file, the system walks five links:

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

**"Does double-click work with pipx install?"** — Yes, because:

- `make install` runs `pipx install` **and then** `make desktop` **and then** `make mime`
- `make desktop` rewrites `Exec=` to the pipx bin dir at that moment
- `make mime` writes the association

The only way it breaks is if pipx's bin dir changes *after* `make install`.
In that case, re-run `make desktop`.

---

## Full Make command reference

Run `make` or `make help` to list everything from the terminal.

### Development

| Command | What it does |
|---|---|
| `make dev` | Creates `.venv` and installs editable with dev tools (`build`, `ruff`) |
| `make run` | Runs from source inside `.venv`, default to `examples/Ruqya/ruqya.ruqya` |
| `make run-empty` | Same, but clears the last-playlist memory first |
| `make data` | Downloads every missing audio/text file a playlist needs (`make data ARGS="a.ruqya b.ruqya"`) |
| `make data-all` | Same, for every `.ruqya` in the example folder |
| `make check` | Lints with ruff, validates `.desktop`, sanity-checks the MIME XML |
| `make fix` | Auto-fixes lint problems where safe |
| `make build` | Builds an sdist and wheel into `dist/` |
| `make combined` | Builds `combined.txt` (project dump for LLM context) |

### Deploy to this machine

| Command | What it does |
|---|---|
| `make install` | **The full deploy**: `pipx install` + `make desktop` + `make mime` |
| `make install-dev` | Same, but editable — code changes apply without reinstalling |
| `make desktop` | Only install the menu entry and icon |
| `make mime` | Only register the `*.ruqya` MIME type and default association |
| `make uninstall` | Remove app, menu entry, icon, and MIME registration. **Keeps config and playlists** |
| `make purge` | Delete `~/.config/ruqya-quran` (asks first). Playlists are not touched |
| `make clean` | Remove `build/`, `dist/`, `*.egg-info`, `__pycache__`, `combined.txt` |
| `make distclean` | `clean` + remove `.venv` |
| `make doctor` | Check every prerequisite |

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
make run ARGS="~/Ruqya/my.ruqya"    # run against a specific playlist
make data ARGS="~/Ruqya/my.ruqya"   # fetch all data for one playlist
```

`PREFIX` defaults to `$(HOME)/.local`. The Makefile queries pipx for its
bin dir at build time, so `Exec=` is always the correct absolute path.

---

## Troubleshooting

**`make install` finishes but `ruqya-quran` isn't found.**
`~/.local/bin` isn't on `$PATH`. Run `pipx ensurepath` and open a new
terminal. The menu entry and double-click still work — they use the
absolute path.

**Menu entry doesn't appear.**
Run `make desktop`, then log out and back in (or
`update-desktop-database ~/.local/share/applications`). Confirm:

```bash
grep ^Exec= ~/.local/share/applications/ruqya-quran.desktop
# → Exec=/home/you/.local/bin/ruqya-quran %f
```

The path in `Exec=` must exist. If you moved pipx or reinstalled it
elsewhere, re-run `make desktop`.

**Double-click on `.ruqya` doesn't open Ruqya Quran.**
Walk the chain in [How double-click works](#how-double-click-works):

```bash
# 1. MIME type registered?
xdg-mime query filetype examples/Ruqya/ruqya.ruqya
# → application/x-ruqya-playlist

# 2. Handler associated?
xdg-mime query default application/x-ruqya-playlist
# → ruqya-quran.desktop

# 3. Desktop file exists and has Exec=?
grep ^Exec= ~/.local/share/applications/ruqya-quran.desktop

# 4. Simulate the double-click
gio open examples/Ruqya/ruqya.ruqya
```

Whichever step returns the wrong thing is the fix. For 1 or 2, `make
mime`. For 3, `make desktop`. If all pass but double-click still fails,
log out — your file manager cached the old association.

**`xdg-mime default` set the right association but Nautilus still opens the editor.**
Nautilus caches preferences per user. `nautilus -q` and reopen. If that
fails, log out and back in once.

**Reciter or translation pickers don't show an edition added in a recent release.**
`~/.config/ruqya-quran/config.json` is only created on first install; an
existing file is never overwritten by `make install`. New reciters (for
example the two Husary variants) or new translations will not appear
until you either edit the `reciters` / `translations` maps by hand, or
run `make purge` and restart the app to regenerate the file from the
packaged defaults. `make purge` does not touch your playlists. If your
existing config has no `preload_reciters` key, the default set is the
list in your config's `reciters` — so even a hand-edit that adds the
reciters won't pre-warm them unless you also update `preload_reciters`
or delete the key.

**`Makefile:NN: *** missing separator`.**
Recipe lines must begin with a **tab**, not spaces. Your editor may have
converted them.

**Arabic or Bengali text shows as boxes.**
Fonts missing, or `font_file` / `bangla_font_file` in
`~/.config/ruqya-quran/config.json` wrong. Run `make doctor`.

**Qt fails with "could not load the Qt platform plugin xcb".**
Install `libxcb-cursor0`.

**Playlist data folder not writable.**
If you opened a playlist from a read-only location, downloads go to
`~/.local/share/ruqya-quran/<hash>/` instead. A warning is logged. To
keep everything together, copy the folder to a writable location.

**First open is slow.**
It warms every reciter in `preload_reciters` — six by default. Set the
playlist's `preload_reciters` (or the config's) to just the reciter you
use. Or copy a populated `data/` folder next to the `.ruqya` file. If
`make data` was already run for the playlist, the warm-up is skipped
entirely.

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
- The MIME type **is** registered system-wide by the package:
  `debian/ruqya-quran.install` ships
  `data/ruqya-quran-playlist.xml` to `/usr/share/mime/packages/`, and the
  `shared-mime-info` dpkg trigger runs `update-mime-database
  /usr/share/mime` automatically on install and removal. No `postinst`,
  `prerm`, or manual command is needed.
- The Debian package ships its **own** `/etc`-level config path (via the
  packaged default in `src/ruqya_quran/config.json`), and each user still
  gets a fresh `~/.config/ruqya-quran/config.json` on first launch. The
  upgrade caveat above applies equally here: existing user configs are
  not overwritten by a package upgrade.

