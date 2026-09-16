#!/usr/bin/env bash
#
# install-desktop.sh — install the desktop entry and icon for ruqya-quran
#
# Usage:
#   bash install-desktop.sh
#   bash install-desktop.sh --uninstall
#
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DESKTOP_NAME="ruqya-quran.desktop"
ICON_NAME="quran.png"

DESKTOP_SRC="$SRC/$DESKTOP_NAME"
ICON_SRC="$SRC/icons/$ICON_NAME"

APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
ICON_FLAT_DIR="$HOME/.local/share/icons"
ICON_THEME_DIR="$HOME/.local/share/icons/hicolor"

die()  { echo "[FATAL] $*" >&2; exit 1; }
info() { echo "[INFO]  $*"; }

refresh_caches() {
    command -v update-desktop-database >/dev/null 2>&1 && \
        update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && \
        gtk-update-icon-cache -f -t "$ICON_THEME_DIR" >/dev/null 2>&1 || true
}

if [[ "${1:-}" == "--uninstall" ]]; then
    info "Removing installed desktop entry and icon…"
    rm -f "$APPS_DIR/$DESKTOP_NAME"
    rm -f "$ICON_DIR/$ICON_NAME"
    rm -f "$ICON_FLAT_DIR/$ICON_NAME"
    refresh_caches
    info "Done."
    exit 0
fi

[[ -f "$DESKTOP_SRC" ]] || die "Desktop file not found: $DESKTOP_SRC"
[[ -f "$ICON_SRC"    ]] || die "Icon not found:         $ICON_SRC"

chmod 777 "$DESKTOP_SRC" 2>/dev/null || true

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$DESKTOP_SRC" || die "Desktop file failed validation"
fi

mkdir -p "$APPS_DIR" "$ICON_DIR" "$ICON_FLAT_DIR" "$ICON_THEME_DIR"

cp -f "$DESKTOP_SRC" "$APPS_DIR/$DESKTOP_NAME"
chmod 777 "$APPS_DIR/$DESKTOP_NAME"

cp -f "$ICON_SRC" "$ICON_DIR/$ICON_NAME"
cp -f "$ICON_SRC" "$ICON_FLAT_DIR/$ICON_NAME"

refresh_caches

info "Desktop entry → $APPS_DIR/$DESKTOP_NAME"
info "Icon (theme)  → $ICON_DIR/$ICON_NAME"
info "Icon (flat)   → $ICON_FLAT_DIR/$ICON_NAME"
echo
info "The launcher should now appear in your application menu."
info "To uninstall:  bash $(basename "$0") --uninstall"
