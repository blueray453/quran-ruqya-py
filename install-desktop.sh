#!/usr/bin/env bash
#
# install-desktop.sh — install the desktop entry, icon, and seed the cache
#
# Usage:
#   bash install-desktop.sh                   # install + seed cache
#   bash install-desktop.sh --no-seed         # install, skip cache seeding
#   bash install-desktop.sh --uninstall       # remove desktop entry + icon
#
# Environment:
#   SOURCE_CACHE=/path/to/cache/ruqya-quran   # override the seed source
#   XDG_CACHE_HOME=/path                      # override the destination root
#
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DESKTOP_NAME="ruqya-quran.desktop"
ICON_NAME="quran.png"

DESKTOP_SRC="$SRC/$DESKTOP_NAME"
ICON_SRC="$SRC/icons/$ICON_NAME"

# Cache source (the working tree's cache/ruqya-quran)
SOURCE_CACHE="${SOURCE_CACHE:-$SRC/cache/ruqya-quran}"

# Cache destination (XDG-compliant, matches main.py's _cache_dir())
CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}"
DEST_CACHE="$CACHE_ROOT/ruqya-quran"

APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
ICON_FLAT_DIR="$HOME/.local/share/icons"
ICON_THEME_DIR="$HOME/.local/share/icons/hicolor"

SEED_CACHE=1

die()  { echo "[FATAL] $*" >&2; exit 1; }
info() { echo "[INFO]  $*"; }
warn() { echo "[WARN]  $*" >&2; }

refresh_caches() {
    command -v update-desktop-database >/dev/null 2>&1 && \
        update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && \
        gtk-update-icon-cache -f -t "$ICON_THEME_DIR" >/dev/null 2>&1 || true
}

count_files() {
    if [[ -d "$1" ]]; then
        find "$1" -type f 2>/dev/null | wc -l
    else
        echo 0
    fi
}

seed_cache() {
    if [[ "$SEED_CACHE" -eq 0 ]]; then
        info "Cache seeding skipped (--no-seed)."
        return
    fi
    if [[ ! -d "$SOURCE_CACHE" ]]; then
        info "No seed cache at $SOURCE_CACHE — skipping."
        return
    fi
    if [[ -d "$DEST_CACHE" && ! -w "$DEST_CACHE" ]]; then
        warn "$DEST_CACHE is not writable — skipping cache seed."
        warn "  (HINT: is it owned by another user, e.g. from a prior sudo run?)"
        return
    fi

    info "Seeding cache → $DEST_CACHE"
    mkdir -p "$DEST_CACHE"

    local total_new=0
    local subdir s d before after added

    # Only merge known subtrees. Skips the Qt runtime junk
    # at $SOURCE_CACHE/"Ruqya Quran"/ (qmlcache, qtpipelinecache, …).
    for subdir in audio metadata wbw; do
        s="$SOURCE_CACHE/$subdir"
        d="$DEST_CACHE/$subdir"
        [[ -d "$s" ]] || continue
        mkdir -p "$d"

        before=$(count_files "$d")

        if command -v rsync >/dev/null 2>&1; then
            rsync -a --ignore-existing "$s/" "$d/"
        else
            cp -rn "$s/." "$d/" 2>/dev/null || true
        fi

        after=$(count_files "$d")
        added=$(( after - before ))
        total_new=$(( total_new + added ))
        info "  $subdir: +$added file(s) (destination now has $after)"
    done

    if [[ "$total_new" -eq 0 ]]; then
        info "Cache already complete — no files copied."
    else
        info "Copied $total_new file(s) into the cache."
    fi
}

show_help() {
    cat <<'EOF'
install-desktop.sh — install the desktop entry, icon, and seed the cache

Usage:
  bash install-desktop.sh                   Install entry, icon, and seed cache
  bash install-desktop.sh --no-seed         Install entry + icon only
  bash install-desktop.sh --uninstall       Remove entry + icon (leaves cache intact)

Environment:
  SOURCE_CACHE=PATH     Where to seed the cache from
                        (default: <repo>/cache/ruqya-quran)
  XDG_CACHE_HOME=PATH   Where to install the cache
                        (default: $HOME/.cache)
EOF
}

# -------------------- uninstall --------------------
if [[ "${1:-}" == "--uninstall" ]]; then
    info "Removing installed desktop entry and icon…"
    rm -f "$APPS_DIR/$DESKTOP_NAME"
    rm -f "$ICON_DIR/$ICON_NAME"
    rm -f "$ICON_FLAT_DIR/$ICON_NAME"
    refresh_caches
    info "Done."
    echo
    info "The runtime cache at $DEST_CACHE was NOT removed."
    info "  To remove it manually:  rm -rf '$DEST_CACHE'"
    exit 0
fi

# -------------------- parse flags --------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-seed)  SEED_CACHE=0; shift ;;
        -h|--help)  show_help; exit 0 ;;
        *)          die "Unknown option: $1" ;;
    esac
done

# -------------------- install --------------------
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

seed_cache

echo
info "The launcher should now appear in your application menu."
info "To uninstall:  bash $(basename "$0") --uninstall"