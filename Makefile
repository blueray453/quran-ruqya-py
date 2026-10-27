APP       := ruqya-quran
PKG       := ruqya_quran
VENV      := .venv
PY        := $(VENV)/bin/python
VERSION   := $(shell sed -n 's/^__version__ *= *"\(.*\)"/\1/p' src/$(PKG)/__init__.py)
DEB_FILE  := dist/$(APP)_$(VERSION)_all.deb

PREFIX    ?= $(HOME)/.local
APPS_DIR  := $(PREFIX)/share/applications
ICON_DIR  := $(PREFIX)/share/icons/hicolor/256x256/apps
CONF_DIR  := $(or $(XDG_CONFIG_HOME),$(HOME)/.config)/$(APP)
CACHE_DIR := $(or $(XDG_CACHE_HOME),$(HOME)/.cache)/$(APP)

# Seed source: must contain audio/, metadata/, wbw/ (override: make seed SEED_DIR=/path)
SEED_DIR  ?= seed
SEED_SUBS := audio metadata wbw

# wherever pipx is configured to put executables
BIN_DIR    = $(shell pipx environment --value PIPX_BIN_DIR 2>/dev/null || echo $(HOME)/.local/bin)

.DEFAULT_GOAL := help
.PHONY: help dev run install install-dev desktop extras seed seed-export \
        uninstall purge check build deb deb-version deb-lint deb-install \
        deb-uninstall deb-clean clean distclean doctor

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | \
	  awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

# ---------- local development ----------
$(VENV)/.stamp: pyproject.toml
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -e '.[dev]'
	touch $@

dev: $(VENV)/.stamp  ## Create venv and install in editable mode

run: dev  ## Run from source (no install)
	$(PY) -m $(PKG)

# ---------- deploy to this machine (pipx) ----------
install:  ## Install via pipx + menu entry + icon + extras + cache seed
	pipx install --force .
	$(MAKE) desktop extras seed
	@echo "Installed. Launch with '$(APP)' or from the app menu."

install-dev:  ## Same as install, but editable (code changes apply live)
	pipx install --force --editable .
	$(MAKE) desktop extras seed

desktop:  ## Install .desktop file and icon (absolute Exec path)
	desktop-file-validate data/$(APP).desktop
	install -d $(APPS_DIR)
	sed 's|^Exec=.*|Exec=$(BIN_DIR)/$(APP)|' data/$(APP).desktop > $(APPS_DIR)/$(APP).desktop
	chmod 644 $(APPS_DIR)/$(APP).desktop
	install -Dm644 data/icons/hicolor/256x256/apps/$(APP).png $(ICON_DIR)/$(APP).png
	-update-desktop-database $(APPS_DIR)
	-gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor

extras:  ## Copy extras/ to ~/.config/ruqya-quran/extras (never overwrites)
	mkdir -p "$(CONF_DIR)/extras"
	cp -rn extras/. "$(CONF_DIR)/extras/"

seed:  ## Seed ~/.cache/ruqya-quran from $(SEED_DIR)/ (never overwrites)
	@if [ ! -d "$(SEED_DIR)" ]; then \
	  echo "seed: '$(SEED_DIR)/' not found, skipping"; exit 0; fi; \
	for d in $(SEED_SUBS); do \
	  [ -d "$(SEED_DIR)/$$d" ] || continue; \
	  mkdir -p "$(CACHE_DIR)/$$d"; \
	  before=$$(find "$(CACHE_DIR)/$$d" -type f | wc -l); \
	  cp -rn "$(SEED_DIR)/$$d/." "$(CACHE_DIR)/$$d/"; \
	  after=$$(find "$(CACHE_DIR)/$$d" -type f | wc -l); \
	  echo "seed: $$d +$$((after - before)) file(s) (now $$after)"; \
	done

seed-export:  ## Snapshot current ~/.cache/ruqya-quran into $(SEED_DIR)/
	@for d in $(SEED_SUBS); do \
	  [ -d "$(CACHE_DIR)/$$d" ] || continue; \
	  mkdir -p "$(SEED_DIR)/$$d"; \
	  cp -rn "$(CACHE_DIR)/$$d/." "$(SEED_DIR)/$$d/"; \
	  echo "exported $$d"; \
	done

uninstall:  ## Remove pipx app, menu entry, icon (keeps config and cache)
	-pipx uninstall $(APP)
	rm -f $(APPS_DIR)/$(APP).desktop $(ICON_DIR)/$(APP).png
	-update-desktop-database $(APPS_DIR)
	-gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor
	@echo "Config ($(CONF_DIR)) and cache ($(CACHE_DIR)) kept. 'make purge' removes them."

purge:  ## Delete user config and cache (asks first)
	@read -p "Delete $(CONF_DIR) and $(CACHE_DIR)? [y/N] " a; \
	  [ "$$a" = y ] && rm -rf "$(CONF_DIR)" "$(CACHE_DIR)" && echo removed || echo aborted

# ---------- Debian package ----------
deb-version:  ## Add a debian/changelog entry for the current __version__
	@[ -n "$(VERSION)" ] || { echo "could not read version"; exit 1; }
	dch --newversion $(VERSION) --distribution unstable "Release $(VERSION)"

deb:  ## Build the .deb into dist/
	@[ -n "$(VERSION)" ] || { echo "could not read version"; exit 1; }
	@head -1 debian/changelog | grep -q "($(VERSION))" || \
	  { echo "debian/changelog is not at $(VERSION). Run: make deb-version"; exit 1; }
	chmod +x debian/rules
	dpkg-buildpackage -us -uc -b
	mkdir -p dist
	mv -f ../$(APP)_$(VERSION)_* dist/
	@echo "Built: $(DEB_FILE)"

deb-lint: ## Run lintian on the built package
	lintian --info dist/$(APP)_$(VERSION)_*.changes

deb-install:  ## Install the built .deb (resolves dependencies via apt)
	sudo apt install ./$(DEB_FILE)

deb-uninstall:  ## Remove the .deb (keeps user config and cache)
	sudo apt remove $(APP)

deb-clean:  ## Remove debian build leftovers
	rm -rf debian/.debhelper debian/$(APP) debian/files debian/*.substvars \
	       debian/*.debhelper.log debian/debhelper-build-stamp .pybuild

# ---------- quality / packaging ----------
check: dev  ## Lint code and validate .desktop
	$(VENV)/bin/ruff check src
	desktop-file-validate data/$(APP).desktop

build: dev  ## Build Python sdist + wheel into dist/ (for pip users)
	$(PY) -m build

clean: deb-clean  ## Remove build artifacts
	rm -rf build dist src/*.egg-info
	find . -name __pycache__ -prune -exec rm -rf {} +

distclean: clean  ## clean + remove .venv
	rm -rf $(VENV)

doctor:  ## Check system prerequisites
	@for c in python3 pipx desktop-file-validate; do \
	  command -v $$c >/dev/null && echo "ok      $$c" || echo "MISSING $$c"; done
	@for c in dpkg-buildpackage dch lintian; do \
	  command -v $$c >/dev/null && echo "ok      $$c (deb)" || echo "MISSING $$c (only needed for make deb)"; done
	@for f in /usr/share/fonts/opentype/fonts-hosny-amiri/AmiriQuran.ttf \
	          /usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf; do \
	  [ -f $$f ] && echo "ok      $$f" || echo "MISSING $$f"; done
	@[ -d "$(SEED_DIR)" ] && echo "ok      seed dir ($(SEED_DIR))" || echo "MISSING seed dir ($(SEED_DIR))"
	@echo "version: $(VERSION)"
	@echo "pipx bin dir: $(BIN_DIR)"