APP       := ruqya-quran
PKG       := ruqya_quran
VENV      := .venv
PY        := $(VENV)/bin/python

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
        uninstall purge check build clean distclean doctor

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | \
	  awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

# ---------- local development ----------
$(VENV)/.stamp: pyproject.toml
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -e '.[dev]'
	touch $@

dev: $(VENV)/.stamp  ## Create venv and install in editable mode

run: dev  ## Run from source (no install)
	$(PY) -m $(PKG)

# ---------- deploy to this machine ----------
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

uninstall:  ## Remove app, menu entry, icon (keeps config and cache)
	-pipx uninstall $(APP)
	rm -f $(APPS_DIR)/$(APP).desktop $(ICON_DIR)/$(APP).png
	-update-desktop-database $(APPS_DIR)
	-gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor
	@echo "Config ($(CONF_DIR)) and cache ($(CACHE_DIR)) kept. 'make purge' removes them."

purge:  ## Delete user config and cache (asks first)
	@read -p "Delete $(CONF_DIR) and $(CACHE_DIR)? [y/N] " a; \
	  [ "$$a" = y ] && rm -rf "$(CONF_DIR)" "$(CACHE_DIR)" && echo removed || echo aborted

# ---------- quality / packaging ----------
check: dev  ## Lint code and validate .desktop
	$(VENV)/bin/ruff check src
	desktop-file-validate data/$(APP).desktop

build: dev  ## Build sdist + wheel into dist/
	$(PY) -m build

clean:  ## Remove build artifacts
	rm -rf build dist src/*.egg-info
	find . -name __pycache__ -prune -exec rm -rf {} +

distclean: clean  ## clean + remove .venv
	rm -rf $(VENV)

doctor:  ## Check system prerequisites
	@for c in python3 pipx desktop-file-validate; do \
	  command -v $$c >/dev/null && echo "ok      $$c" || echo "MISSING $$c"; done
	@for f in /usr/share/fonts/opentype/fonts-hosny-amiri/AmiriQuran.ttf \
	          /usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf; do \
	  [ -f $$f ] && echo "ok      $$f" || echo "MISSING $$f"; done
	@[ -d "$(SEED_DIR)" ] && echo "ok      seed dir ($(SEED_DIR))" || echo "MISSING seed dir ($(SEED_DIR))"
	@echo "pipx bin dir: $(BIN_DIR)"