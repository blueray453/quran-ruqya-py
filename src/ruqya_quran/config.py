"""User config (config.json) and the values derived from it. No Qt, no network."""

import json
import logging
import os
import shutil
from importlib.resources import files as _pkg_files
from pathlib import Path

log = logging.getLogger("ruqya.config")

TEMPLATE_CONFIG_NAME = "config.json"

def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else Path.home() / ".config") / "ruqya-quran"

CONFIG_DIR = _config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"

def _copy_pkg_file(rel: str, dst: Path) -> bool:
    try:
        node = _pkg_files(__package__)
        for part in Path(rel).parts:
            node = node.joinpath(part)
        with node.open("rb") as fsrc, open(dst, "wb") as fdst:
            shutil.copyfileobj(fsrc, fdst)
        return True
    except (OSError, AttributeError) as e:
        log.warning("Could not copy %s: %s", rel, e)
        return False

def _ensure_user_files() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        _copy_pkg_file(TEMPLATE_CONFIG_NAME, CONFIG_PATH)

def _load_config() -> dict:
    _ensure_user_files()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Config unreadable (%s); using packaged defaults", e)
        try:
            node = _pkg_files(__package__).joinpath(TEMPLATE_CONFIG_NAME)
            return json.loads(node.read_text(encoding="utf-8"))
        except Exception:
            return {}

CFG = _load_config()

# ------------------------------------------------------------
# Configurable values
# ------------------------------------------------------------

RECITERS: dict = CFG.get(
    "reciters", {
        "ar.abdurrahmaansudais": "Sudais",
        "ar.saoodshuraym": "Shuraym",
        "ar.alafasy": "Mishari Rashid",
        "ar.ghamdi": "Saad al-Ghamdi",
        "ar.husary": "Mahmoud Khalil Al-Husary (Murattal)",
        "ar.husarymuallim": "Mahmoud Khalil Al-Husary (Muallim)",
    })
DEFAULT_RECITER = CFG.get("default_reciter", next(iter(RECITERS)))

TRANSLATIONS: dict = CFG.get("translations", {
    "en.sahih": "English (Saheeh)",
    "bn.bengali": "বাংলা (Muhiuddin Khan)",
    "bn.hoque": "বাংলা (Zohurul Hoque)",
})
DEFAULT_TRANSLATION = CFG.get("default_translation", next(iter(TRANSLATIONS)))

WORD_BY_WORD_LANGUAGE = CFG.get("word_by_word_language", "auto")

def _resolve_preload_list(value, valid_keys):
    if value in (None, "all", []):
        return list(valid_keys)
    if isinstance(value, str):
        value = [value]
    return [k for k in value if k in valid_keys]

PRELOAD_RECITERS = _resolve_preload_list(CFG.get("preload_reciters"), list(RECITERS))
PRELOAD_TRANSLATIONS = _resolve_preload_list(CFG.get("preload_translations"), list(TRANSLATIONS))

FONT_FILE = os.path.expanduser(CFG.get("font_file", "/usr/share/fonts/opentype/fonts-hosny-amiri/AmiriQuran.ttf"))
BANGLA_FONT_FILE = os.path.expanduser(
    CFG.get("bangla_font_file", "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"))
CUSTOM_PLAYLIST_SEPARATOR_LABEL = CFG.get("custom_playlist_separator_label", "Duas")
MAX_WORKERS = int(CFG.get("max_workers", 4))

# Network-only keys (request_timeout, max_retries, retry_backoff_base,
# source_fail_threshold) are read by fetcher.FetchSettings.from_cfg(CFG).
