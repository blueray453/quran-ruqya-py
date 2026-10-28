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

DESKTOP_FILE := data/$(APP).desktop
ICON_FILE    := data/icons/hicolor/256x256/apps/$(APP).png
MIME_FILE    := data/$(APP)-playlist.xml

BIN_DIR    = $(shell pipx environment --value PIPX_BIN_DIR 2>/dev/null || echo $(HOME)/.local/bin)

.DEFAULT_GOAL := help
.PHONY: help dev run install install-dev desktop mime uninstall purge \
        check fix build deb-deps deb-version deb deb-lint deb-install deb-uninstall deb-clean \
        clean distclean doctor

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
install:  ## Install via pipx + menu entry + icon + MIME type
	pipx install --force .
	$(MAKE) desktop mime
	@echo "Installed. Launch with '$(APP)' or from the app menu."

install-dev:  ## Same as install, but editable (code changes apply live)
	pipx install --force --editable .
	$(MAKE) desktop mime

desktop:  ## Install .desktop file and icon (absolute Exec path, %f preserved)
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
	@echo "Note: 'xdg-mime' entry in ~/.config/mimeapps.list is left behind (harmless)."

purge:  ## Delete user config (asks first)
	@read -p "Delete $(CONF_DIR)? [y/N] " a; \
	  [ "$$a" = y ] && rm -rf "$(CONF_DIR)" && echo removed || echo aborted

# ---------- Debian package ----------
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

deb-uninstall:  ## Remove the .deb (keeps user config)
	sudo apt remove $(APP)

deb-clean:  ## Remove debian build leftovers
	rm -rf debian/.debhelper debian/$(APP) debian/files debian/*.substvars \
	       debian/*.debhelper.log debian/debhelper-build-stamp .pybuild

# ---------- quality / packaging ----------
check: dev  ## Lint code, validate .desktop and MIME xml
	$(VENV)/bin/ruff check src
	desktop-file-validate $(DESKTOP_FILE)
	@command -v xmllint >/dev/null && xmllint --noout $(MIME_FILE) && echo "mime xml: ok" || true

fix: dev  ## Auto-fix lint problems where safe
	$(VENV)/bin/ruff check --fix src

build: dev  ## Build Python sdist + wheel into dist/ (for pip users)
	$(PY) -m build

clean: deb-clean  ## Remove build artifacts
	rm -rf build dist src/*.egg-info
	find . -name __pycache__ -prune -exec rm -rf {} +

distclean: clean  ## clean + remove .venv
	rm -rf $(VENV)

doctor:  ## Check system prerequisites
	@for c in python3 pipx desktop-file-validate xdg-mime update-mime-database; do \
	  command -v $$c >/dev/null && echo "ok      $$c" || echo "MISSING $$c"; done
	@for c in dpkg-buildpackage dch lintian; do \
	  command -v $$c >/dev/null && echo "ok      $$c (deb)" || echo "MISSING $$c (only needed for make deb)"; done
	@for f in /usr/share/fonts/opentype/fonts-hosny-amiri/AmiriQuran.ttf \
	          /usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf; do \
	  [ -f $$f ] && echo "ok      $$f" || echo "MISSING $$f"; done
	@[ -f $(DESKTOP_FILE) ] && echo "ok      $(DESKTOP_FILE)" || echo "MISSING $(DESKTOP_FILE)"
	@[ -f $(ICON_FILE) ]    && echo "ok      $(ICON_FILE)"    || echo "MISSING $(ICON_FILE)"
	@[ -f $(MIME_FILE) ]    && echo "ok      $(MIME_FILE)"    || echo "MISSING $(MIME_FILE)"
	@[ -f examples/Ruqya/default.ruqya ] && echo "ok      example workspace" || echo "MISSING examples/Ruqya/default.ruqya"
	@echo "version: $(VERSION)"
	@echo "pipx bin dir: $(BIN_DIR)"