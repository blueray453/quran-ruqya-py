# ---------------------------------------------------------------------------
# Ruqya Quran — top-level Makefile
#
# Each playlist is self-contained: <name>.ruqya + <data_dir>/ next to it.
# `make bundle` populates the example playlist's data folder.
#
#   make help          list all targets
#   make dev           create .venv and install editable with dev tools
#   make bundle        build the example playlist's data folder (~2.5 GB)
#   make bundle-fast   build JSON only (fast; validates tokenization)
#   make bundle-one    bundle a specific playlist: make bundle-one PL=path.ruqya
#   make run           run from source (respects .venv)
#   make install       deploy: pipx + menu entry + icon + MIME registration
#   make uninstall     remove app, menu entry, icon, MIME registration
#   make deb           build a .deb into dist/
#
# Variables (override on the command line):
#   PREFIX   install prefix, default ~/.local
#   ARGS     arguments passed to `make run`
#   PL       playlist path for `make bundle-one`
# ---------------------------------------------------------------------------

APP       := ruqya-quran
PKG       := ruqya_quran
VENV      := .venv
PY        := $(VENV)/bin/python
VERSION   := $(shell sed -n 's/^__version__ *= *"\(.*\)"/\1/p' src/$(PKG)/__init__.py)
DEB_FILE  := dist/$(APP)_$(VERSION)_all.deb

PREFIX    ?= $(HOME)/.local
APPS_DIR  := $(PREFIX)/share/applications
ICON_DIR  := $(PREFIX)/share/icons/hicolor/256x256/apps
MIME_ROOT := $(PREFIX)/share/mime
MIME_DIR  := $(MIME_ROOT)/packages
CONF_DIR  := $(or $(XDG_CONFIG_HOME),$(HOME)/.config)/$(APP)

RAW_DIR      := tools/raw
DESKTOP_FILE := data/$(APP).desktop
ICON_FILE    := data/icons/hicolor/256x256/apps/$(APP).png
MIME_FILE    := data/$(APP)-playlist.xml
EXAMPLE      := examples/Ruqya/ruqya.ruqya
EX_DATA      := examples/Ruqya/data

BIN_DIR := $(shell pipx environment --value PIPX_BIN_DIR 2>/dev/null || echo $(HOME)/.local/bin)

.DEFAULT_GOAL := help
.PHONY: help dev run run-empty bundle bundle-fast bundle-one bundle-clean combined \
        install install-dev desktop mime uninstall purge \
        check fix build clean distclean doctor \
        deb-deps deb-version deb deb-lint deb-install deb-uninstall deb-clean

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | \
	  awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

$(VENV)/.stamp: pyproject.toml
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -e '.[dev]'
	touch $@

dev: $(VENV)/.stamp  ## Create .venv and install editable with dev tools

run: dev  ## Run from source. Default: example playlist.
	$(PY) -m $(PKG) $(or $(ARGS),$(EXAMPLE))

run-empty: dev  ## Run from source with no playlist (fresh empty state)
	@$(PY) -c "from PySide6.QtCore import QSettings; \
	  QSettings('ruqya-quran','ruqya-quran').remove('ui/lastPlaylist')"
	$(PY) -m $(PKG) $(ARGS)

bundle: dev  ## Build example playlist's data (downloads MP3s once; ~2.5 GB)
	@[ -d $(RAW_DIR) ] || { echo "$(RAW_DIR)/ missing — drop QUL JSONs there first"; exit 1; }
	$(PY) tools/fetch_qul.py --src $(RAW_DIR) --playlist $(EXAMPLE)

bundle-fast: dev  ## Build JSON only for example playlist (fast, validates)
	@[ -d $(RAW_DIR) ] || { echo "$(RAW_DIR)/ missing — drop QUL JSONs there first"; exit 1; }
	$(PY) tools/fetch_qul.py --src $(RAW_DIR) --playlist $(EXAMPLE) --skip-audio

bundle-one: dev  ## Bundle a specific playlist: make bundle-one PL=path/to/foo.ruqya
	@[ -n "$(PL)" ] || { echo "PL=path/to/foo.ruqya required"; exit 1; }
	$(PY) tools/fetch_qul.py --src $(RAW_DIR) --playlist $(PL)

bundle-sudais: dev  ## Bundle ONLY Sudais (for testing; removes other reciters first)
	$(PY) tools/fetch_qul.py --src $(RAW_DIR) --playlist $(EXAMPLE) \
	  --only-reciter ar.abdurrahmaansudais --prune-others

bundle-reciter: dev  ## Bundle one reciter: make bundle-reciter R=ar.alafasy
	@[ -n "$(R)" ] || { echo "R=reciter_id required"; exit 1; }
	$(PY) tools/fetch_qul.py --src $(RAW_DIR) --playlist $(EXAMPLE) --only-reciter $(R)


bundle-clean:  ## Delete example playlist's data (asks first; frees ~2.5 GB)
	@read -p "Delete $(EX_DATA)/? [y/N] " a; \
	  [ "$$a" = y ] && rm -rf $(EX_DATA) && echo removed || echo aborted

combined:  ## Build combined.txt for LLM context
	@python3 tools/combine.py combined.txt

# ---------------------------------------------------------------------------
# Deploy to this machine
# ---------------------------------------------------------------------------

install:  ## Deploy: pipx + menu entry + icon + MIME registration
	pipx install --force .
	$(MAKE) desktop mime
	@echo
	@echo "Installed. Launch with '$(APP)' or from the application menu."
	@echo "Open a playlist with:  $(APP) $(EXAMPLE)"
	@echo
	@echo "Note: each playlist needs its own <data_dir>/ populated by"
	@echo "      tools/fetch_qul.py --playlist <name>.ruqya."

install-dev:  ## Same as install, but editable (code changes apply live)
	pipx install --force --editable .
	$(MAKE) desktop mime

desktop:  ## Install .desktop file and icon (Exec= rewritten to pipx bin dir)
	desktop-file-validate $(DESKTOP_FILE)
	install -d $(APPS_DIR)
	sed 's|^Exec=.*|Exec=$(BIN_DIR)/$(APP) %f|' $(DESKTOP_FILE) > $(APPS_DIR)/$(APP).desktop
	chmod 644 $(APPS_DIR)/$(APP).desktop
	install -Dm644 $(ICON_FILE) $(ICON_DIR)/$(APP).png
	-update-desktop-database $(APPS_DIR)
	-gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor

mime:  ## Register application/x-ruqya-playlist and *.ruqya association
	@command -v xmllint >/dev/null && xmllint --noout $(MIME_FILE) || true
	install -Dm644 $(MIME_FILE) $(MIME_DIR)/$(APP)-playlist.xml
	-update-mime-database $(MIME_ROOT)
	-xdg-mime default $(APP).desktop application/x-ruqya-playlist

uninstall:  ## Remove pipx app, menu entry, icon, MIME registration
	-pipx uninstall $(APP)
	rm -f $(APPS_DIR)/$(APP).desktop $(ICON_DIR)/$(APP).png
	rm -f $(MIME_DIR)/$(APP)-playlist.xml
	-update-desktop-database $(APPS_DIR)
	-gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor
	-update-mime-database $(MIME_ROOT)
	@echo "Config ($(CONF_DIR)) kept. 'make purge' removes it."
	@echo "Playlist data folders (e.g. $(EX_DATA)/) are never touched."

purge:  ## Delete user config (asks first). Playlists are never touched.
	@read -p "Delete $(CONF_DIR)? [y/N] " a; \
	  [ "$$a" = y ] && rm -rf "$(CONF_DIR)" && echo removed || echo aborted

# ---------------------------------------------------------------------------
# Debian package
# ---------------------------------------------------------------------------

deb-deps:  ## Install tools needed to build the .deb (uses sudo)
	sudo apt install build-essential devscripts debhelper dh-python \
	  pybuild-plugin-pyproject python3-all python3-setuptools lintian

deb-version:  ## Add a debian/changelog entry for the current __version__
	@[ -n "$(VERSION)" ] || { echo "could not read version"; exit 1; }
	@if head -1 debian/changelog | grep -q "($(VERSION))"; then \
	  echo "changelog already at $(VERSION)"; \
	else \
	  dch --newversion $(VERSION) --distribution unstable "Release $(VERSION)"; \
	fi

deb:  ## Build the .deb into dist/
	@[ -z "$$VIRTUAL_ENV" ] || { echo "deactivate your venv first"; exit 1; }
	@[ -n "$(VERSION)" ] || { echo "could not read version"; exit 1; }
	@head -1 debian/changelog | grep -q "($(VERSION))" || \
	  { echo "debian/changelog is not at $(VERSION). Run: make deb-version"; exit 1; }
	@echo "Note: .deb ships the app only. Playlist data folders are per-playlist."
	chmod +x debian/rules
	dpkg-buildpackage -us -uc -b
	mkdir -p dist
	mv -f ../$(APP)_$(VERSION)_* dist/
	@echo "Built: $(DEB_FILE)"

deb-lint:  ## Run lintian on the built package
	lintian --info dist/$(APP)_$(VERSION)_*.changes

deb-install:  ## Install the built .deb (resolves dependencies via apt)
	@[ -f "$(DEB_FILE)" ] || { echo "$(DEB_FILE) not found. Run: make deb"; exit 1; }
	sudo apt install ./$(DEB_FILE)

deb-uninstall:  ## Remove the .deb (keeps user config and playlists)
	sudo apt remove $(APP)

deb-clean:  ## Remove debian build leftovers
	rm -rf debian/.debhelper debian/$(APP) debian/files debian/*.substvars \
	       debian/*.debhelper.log debian/debhelper-build-stamp .pybuild

# ---------------------------------------------------------------------------
# Quality and packaging
# ---------------------------------------------------------------------------

check: dev  ## Lint code, validate .desktop, sanity-check MIME xml
	$(VENV)/bin/ruff check src
	desktop-file-validate $(DESKTOP_FILE)
	@command -v xmllint >/dev/null && xmllint --noout $(MIME_FILE) && echo "mime xml: ok" || true

fix: dev  ## Auto-fix lint problems where safe
	$(VENV)/bin/ruff check --fix src

build: dev  ## Build sdist + wheel into dist/ (for pip users)
	$(PY) -m build

clean: deb-clean  ## Remove build artifacts (does NOT delete playlist data)
	rm -rf build dist src/*.egg-info
	find . -name __pycache__ -prune -exec rm -rf {} +
	rm -f combined.txt

distclean: clean  ## clean + remove .venv (does NOT delete playlist data)
	rm -rf $(VENV)

# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

doctor:  ## Check system prerequisites
	@echo "--- tools ---"
	@for c in python3 pipx wget desktop-file-validate xdg-mime update-mime-database; do \
	  command -v $$c >/dev/null && echo "ok      $$c" || echo "MISSING $$c"; done
	@for c in dpkg-buildpackage dch lintian; do \
	  command -v $$c >/dev/null && echo "ok      $$c (deb)" || echo "MISSING $$c (only needed for make deb)"; done
	@echo "--- fonts ---"
	@for f in /usr/share/fonts/opentype/fonts-hosny-amiri/AmiriQuran.ttf \
	          /usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf; do \
	  [ -f $$f ] && echo "ok      $$f" || echo "MISSING $$f"; done
	@echo "--- project ---"
	@[ -f $(DESKTOP_FILE) ] && echo "ok      $(DESKTOP_FILE)" || echo "MISSING $(DESKTOP_FILE)"
	@[ -f $(ICON_FILE) ]    && echo "ok      $(ICON_FILE)"    || echo "MISSING $(ICON_FILE)"
	@[ -f $(MIME_FILE) ]    && echo "ok      $(MIME_FILE)"    || echo "MISSING $(MIME_FILE)"
	@[ -f $(EXAMPLE) ]      && echo "ok      example playlist" || echo "MISSING $(EXAMPLE)"
	@[ -f tools/combine.py ]  && echo "ok      tools/combine.py" || echo "MISSING tools/combine.py"
	@[ -f tools/fetch_qul.py ] && echo "ok      tools/fetch_qul.py" || echo "MISSING tools/fetch_qul.py"
	@echo "--- source files ---"
	@[ -f src/$(PKG)/main.py ] && echo "ok      main.py" || echo "MISSING main.py"
	@[ -f src/$(PKG)/Main.qml ] && echo "ok      Main.qml" || echo "MISSING Main.qml"
	@[ -f src/$(PKG)/__init__.py ] && echo "ok      __init__.py" || echo "MISSING __init__.py"
	@[ -f src/$(PKG)/__main__.py ] && echo "ok      __main__.py" || echo "MISSING __main__.py"
	@echo "--- example playlist data ---"
	@[ -f $(EX_DATA)/VERSION ] && echo "ok      $(EX_DATA)" || echo "MISSING $(EX_DATA) (run 'make bundle-fast' then 'make bundle')"
	@n=$$(ls $(EX_DATA)/recitations/*.json 2>/dev/null | wc -l); \
	  [ "$$n" -gt 0 ] && echo "ok      recitations: $$n" || echo "MISSING recitations"
	@if [ -d $(EX_DATA)/audio ]; then \
	  du -sh $(EX_DATA)/audio | sed 's/^/ok      audio: /'; \
	else echo "MISSING audio (run 'make bundle')"; fi
	@echo "--- version ---"
	@echo "version: $(VERSION)"
	@echo "pipx bin dir: $(BIN_DIR)"
	@echo "prefix: $(PREFIX)"