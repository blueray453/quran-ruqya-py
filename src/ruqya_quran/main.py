#!/usr/bin/env python3
"""
ruqya_quran.main — Quranic Ruqya player (Qt Quick UI).

A playlist is a standalone <name>.ruqya file (JSON) inside a workspace folder:

  Ruqya/
    default.ruqya
    data/
      audio/<reciter>/<surah>_<ayah>.mp3
      text/<edition>/surah_<n>.json
      words/<lang>/<surah>_<ayah>.json
      clips/*.mp3                      # user's own audio

Open with:  ruqya-quran path/to/file.ruqya   (or double-click)

Playlist format (v1):
  {
    "format": "ruqya-playlist",
    "version": 1,
    "name": "Default Ruqya",
    "reciter": "ar.abdurrahmaansudais",         # optional default
    "translation": "en.sahih",                  # optional default
    "data_dir": "data",                         # optional, default "data"
    "offline": false,                           # optional
    "preload_reciters": [],                     # optional overrides
    "preload_translations": [],
    "items": [
      {"surah": 2, "from": 1, "to": 5, "description": "...",
       "ayah_repeat": 1, "group_repeat": 3},    # 0 = ∞
      {"surah": 2, "from": 255, "to": 257,
       "repeat": 3, "repeat_mode": "group"},    # legacy form, also honoured
      {"path": "clips/dua.mp3", "title": "...", "body": "...",
       "translation": "...", "section": "Duas"}
    ]
  }

Persisted (QSettings, shared with QML Settings { category: "ui" }):
  theme, font scale, sidebar, window geometry,
  recentPlaylists, lastPlaylist,
  reciter, translation, volume, showTranslation.

Session-only (reset each launch): wordByWord, ayahRepeat, groupRepeat,
playlistLoop, muted, loop A/B marks, position, current ayah, focus word.
"""

import os
import sys
import json
import time
import hashlib
import shutil
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dataclasses import dataclass, field, replace
from typing import Optional
from importlib.resources import files as _pkg_files

import requests

from PySide6.QtCore import (
    Qt,
    QUrl,
    QThread,
    QTimer,
    Signal,
    Slot,
    Property,
    QObject,
    QAbstractListModel,
    QModelIndex,
    QByteArray,
    QSettings,
)
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("quran_player")
logging.getLogger("qt.qpa.services").setLevel(logging.ERROR)

_GLOBAL_REFS = {}

# ------------------------------------------------------------
# Config directory (only config.json lives here now)
# ------------------------------------------------------------

def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else Path.home() / ".config") / "ruqya-quran"

CONFIG_DIR = _config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"
TEMPLATE_CONFIG_NAME = "config.json"

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

_CFG = _load_config()

# ------------------------------------------------------------
# Configurable values
# ------------------------------------------------------------

RECITERS: dict = _CFG.get(
    "reciters", {
        "ar.abdurrahmaansudais": "Sudais",
        "ar.saoodshuraym": "Shuraym",
        "ar.alafasy": "Mishari Rashid",
        "ar.ghamdi": "Saad al-Ghamdi",
    })
DEFAULT_RECITER = _CFG.get("default_reciter", next(iter(RECITERS)))

TRANSLATIONS: dict = _CFG.get("translations", {
    "en.sahih": "English (Saheeh)",
    "bn.bengali": "বাংলা (Muhiuddin Khan)",
    "bn.hoque": "বাংলা (Zohurul Hoque)",
})
DEFAULT_TRANSLATION = _CFG.get("default_translation", next(iter(TRANSLATIONS)))

WORD_BY_WORD_LANGUAGE = _CFG.get("word_by_word_language", "auto")

def _resolve_preload_list(value, valid_keys):
    if value in (None, "all", []):
        return list(valid_keys)
    if isinstance(value, str):
        value = [value]
    return [k for k in value if k in valid_keys]

PRELOAD_RECITERS = _resolve_preload_list(_CFG.get("preload_reciters"), list(RECITERS))
PRELOAD_TRANSLATIONS = _resolve_preload_list(_CFG.get("preload_translations"), list(TRANSLATIONS))

FONT_FILE = os.path.expanduser(_CFG.get("font_file", "/usr/share/fonts/opentype/fonts-hosny-amiri/AmiriQuran.ttf"))
BANGLA_FONT_FILE = os.path.expanduser(
    _CFG.get("bangla_font_file", "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"))
CUSTOM_PLAYLIST_SEPARATOR_LABEL = _CFG.get("custom_playlist_separator_label", "Duas")
REQUEST_TIMEOUT = float(_CFG.get("request_timeout", 10))
MAX_RETRIES = int(_CFG.get("max_retries", 2))
RETRY_BACKOFF_BASE = float(_CFG.get("retry_backoff_base", 0.5))
MAX_WORKERS = int(_CFG.get("max_workers", 4))
SOURCE_FAIL_THRESHOLD = int(_CFG.get("source_fail_threshold", 3))

BISMILLAH_SURAH = 1
BISMILLAH_AYAH = 1

# ------------------------------------------------------------
# Audio source registry
# ------------------------------------------------------------

AUDIO_SOURCES = {
    "ar.abdurrahmaansudais": ("Abdurrahmaan_As-Sudais_192kbps", "ar.abdurrahmaansudais", 192),
    "ar.saoodshuraym": ("Saood_ash-Shuraym_128kbps", "ar.saoodshuraym", 128),
    "ar.alafasy": ("Mishaari_Raashid_Alafasy_128kbps", "ar.alafasy", 128),
    "ar.ghamdi": ("Ghamadi_40kbps", None, None),
}

def _audio_urls(reciter, surah, ayah, global_ayah_number):
    everyayah_dir, alquran_edition, bitrate = AUDIO_SOURCES.get(reciter, (None, reciter, None))
    urls = []
    if everyayah_dir:
        urls.append(f"https://everyayah.com/data/{everyayah_dir}/{surah:03d}{ayah:03d}.mp3")
    if alquran_edition and global_ayah_number is not None and bitrate is not None:
        urls.append(f"https://cdn.islamic.network/quran/audio/{bitrate}/{alquran_edition}/{global_ayah_number}.mp3")
    return urls

WORD_BY_WORD_URL = ("https://api.quran.com/api/v4/verses/by_key/{surah}:{ayah}"
                    "?words=true"
                    "&word_fields=text_uthmani,translation"
                    "&language={lang}")

# ------------------------------------------------------------
# Source health
# ------------------------------------------------------------

class _SourceHealth:

    def __init__(self, threshold=3):
        self._lock = threading.Lock()
        self._failures = {}
        self._disabled = set()
        self._threshold = threshold

    def is_disabled(self, host):
        with self._lock:
            return host in self._disabled

    def record_success(self, host):
        with self._lock:
            if host in self._failures:
                self._failures[host] = 0

    def record_failure(self, host):
        with self._lock:
            self._failures[host] = self._failures.get(host, 0) + 1
            if self._failures[host] >= self._threshold and host not in self._disabled:
                self._disabled.add(host)
                log.warning("Disabling %s for this session", host)

    def disabled_hosts(self):
        with self._lock:
            return sorted(self._disabled)

_SOURCE_HEALTH = _SourceHealth(threshold=SOURCE_FAIL_THRESHOLD)

# ------------------------------------------------------------
# Workspace (one per .ruqya file)
# ------------------------------------------------------------

class Workspace:
    """Folder of a .ruqya file + its data folder (the source of truth)."""

    def __init__(self, playlist_path: Path, data_dir: str = ""):
        self.playlist_path = playlist_path.resolve()
        self.base_dir = self.playlist_path.parent
        d = Path(data_dir).expanduser() if data_dir else Path("data")
        self.data_dir = d if d.is_absolute() else self.base_dir / d
        self.write_dir = self._pick_write_dir()

    def _pick_write_dir(self) -> Path:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if os.access(self.data_dir, os.W_OK):
                return self.data_dir
        except OSError:
            pass
        digest = hashlib.sha1(str(self.data_dir).encode()).hexdigest()[:12]
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
        fallback = base / "ruqya-quran" / digest
        fallback.mkdir(parents=True, exist_ok=True)
        log.warning("Data folder is read-only; downloads go to %s", fallback)
        return fallback

    def find(self, *parts: str) -> Path:
        """Existing file in data_dir, else where a new file should be written."""
        p = self.data_dir.joinpath(*parts)
        return p if p.exists() else self.write_dir.joinpath(*parts)

_WS: Optional[Workspace] = None
_OFFLINE = False

def set_workspace(ws: Workspace, offline: bool = False) -> None:
    global _WS, _OFFLINE
    _WS, _OFFLINE = ws, offline

def read_playlist_file(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):  # bare list = items only
        data = {"items": data}
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("not a playlist (missing 'items' list)")
    if data.get("format", "ruqya-playlist") != "ruqya-playlist":
        raise ValueError("unknown playlist format")
    try:
        if int(data.get("version", 1)) > 1:
            log.warning("Playlist version %s is newer than supported", data["version"])
    except (TypeError, ValueError):
        pass
    return {
        "name": data.get("name") or path.stem.replace("_", " ").title(),
        "items": data["items"],
        "reciter": data.get("reciter") or "",
        "translation": data.get("translation") or "",
        "data_dir": data.get("data_dir") or "",
        "offline": bool(data.get("offline", False)),
        "preload_reciters": data.get("preload_reciters") or [],
        "preload_translations": data.get("preload_translations") or [],
    }

# ------------------------------------------------------------
# Queue items
# ------------------------------------------------------------

def needs_bismillah(surah: int) -> bool:
    return surah != 1

@dataclass
class QueueItem:
    surah: int
    ayah: int
    description: str
    group_id: str = ""
    lead_bismillah: bool = False
    kind: str = "quran"  # "quran" or "custom"
    custom_path: str = ""
    custom_body: str = ""
    custom_translation: str = ""
    custom_section: str = ""
    ayah_repeat: int = 1  # 0 = ∞
    group_repeat: int = 1  # 0 = ∞

def _resolve_custom_path(raw: str) -> str:
    if not raw:
        return ""
    p = Path(raw).expanduser()
    if p.is_absolute():
        return str(p)
    return str(_WS.data_dir / p)

def _read_repeats(raw: dict) -> tuple[int, int]:
    """Return (ayah_repeat, group_repeat) with 0 meaning ∞.

    Accepts both modern keys and the legacy {"repeat": N, "repeat_mode": "..."} form.
    """
    ayah = raw.get("ayah_repeat", 1)
    group = raw.get("group_repeat", 1)
    if "repeat" in raw:
        if raw.get("repeat_mode", "ayah") == "group":
            group = raw["repeat"]
        else:
            ayah = raw["repeat"]
    try:
        ayah = max(0, int(ayah))
    except (TypeError, ValueError):
        ayah = 1
    try:
        group = max(0, int(group))
    except (TypeError, ValueError):
        group = 1
    return ayah, group

def build_queue_from_items(items: list) -> list:
    queue: list[QueueItem] = []
    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            continue
        if "path" in raw:
            path = _resolve_custom_path(raw.get("path", ""))
            ar, gr = _read_repeats(raw)
            queue.append(
                QueueItem(
                    surah=0,
                    ayah=0,
                    description=raw.get("title") or os.path.basename(path),
                    group_id=f"custom:{idx}",
                    kind="custom",
                    custom_path=path,
                    custom_body=raw.get("body", ""),
                    custom_translation=raw.get("translation", ""),
                    custom_section=raw.get("section") or CUSTOM_PLAYLIST_SEPARATOR_LABEL,
                    ayah_repeat=ar,
                    group_repeat=gr,
                ))
            continue

        if "surah" not in raw:
            continue

        surah = int(raw["surah"])
        from_ayah = int(raw.get("from", 1))
        to_ayah = int(raw.get("to", from_ayah))
        description = raw.get("description") or f"Surah {surah}:{from_ayah}-{to_ayah}"
        ayah_rep, group_rep = _read_repeats(raw)
        group_id = f"g{idx}:{surah}:{from_ayah}-{to_ayah}"

        for ayah in range(from_ayah, to_ayah + 1):
            queue.append(
                QueueItem(
                    surah=surah,
                    ayah=ayah,
                    description=description,
                    group_id=group_id,
                    lead_bismillah=needs_bismillah(surah) and ayah == from_ayah,
                    ayah_repeat=ayah_rep,
                    group_repeat=group_rep,
                ))
    return queue

# ------------------------------------------------------------
# Data models
# ------------------------------------------------------------

@dataclass
class LoadedEntry:
    kind: str
    surah: int
    ayah: int
    description: str
    audio_file: str = ""
    data: dict = field(default_factory=dict)
    surah_data: dict = field(default_factory=dict)
    translation: str = ""
    group_id: str = ""
    lead_bismillah: bool = False
    section: str = ""
    loaded: bool = False
    error: Optional[str] = None
    ayah_repeat: int = 1
    group_repeat: int = 1

def placeholder(item: QueueItem) -> LoadedEntry:
    if item.kind == "custom":
        exists = bool(item.custom_path) and os.path.isfile(item.custom_path)
        return LoadedEntry(
            kind="custom",
            surah=0,
            ayah=0,
            description=item.description,
            audio_file=item.custom_path,
            data={"text": item.custom_body},
            translation=item.custom_translation,
            group_id=item.group_id,
            section=item.custom_section or CUSTOM_PLAYLIST_SEPARATOR_LABEL,
            loaded=True,
            error=None if exists else f"File not found: {item.custom_path}",
            ayah_repeat=item.ayah_repeat,
            group_repeat=item.group_repeat,
        )

    e = LoadedEntry(
        kind="ayah",
        surah=item.surah,
        ayah=item.ayah,
        description=item.description,
        group_id=item.group_id,
        lead_bismillah=item.lead_bismillah,
        ayah_repeat=item.ayah_repeat,
        group_repeat=item.group_repeat,
    )
    e.section = item.description
    return e

# ------------------------------------------------------------
# Data paths (inside the workspace's data folder)
# ------------------------------------------------------------

def audio_path(surah, ayah, reciter):
    return str(_WS.find("audio", reciter, f"{surah}_{ayah}.mp3"))

def text_path(surah, edition):
    return str(_WS.find("text", edition, f"surah_{surah}.json"))

def words_path(surah, ayah, lang):
    return str(_WS.find("words", lang, f"{surah}_{ayah}.json"))

# ------------------------------------------------------------
# Networking
# ------------------------------------------------------------

def request_with_retry(url):
    if _OFFLINE:
        raise RuntimeError("Offline playlist: network disabled")
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            if code is not None and 400 <= code < 500 and code not in (408, 429):
                raise
            last_exc = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE * (2**attempt))
        except requests.RequestException as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE * (2**attempt))
    raise last_exc

def get_cached_surah_metadata(surah, edition):
    path = text_path(surah, edition)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Corrupt text file %s/%s: %s", surah, edition, e)
        return None

def save_cached_surah_metadata(surah, data, edition):
    path = Path(text_path(surah, edition))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_surah_data(surah, edition):
    cached = get_cached_surah_metadata(surah, edition)
    if cached:
        return cached
    log.info("Downloading surah %s metadata (%s)...", surah, edition)
    url = f"https://api.alquran.cloud/v1/surah/{surah}/{edition}"
    data = request_with_retry(url).json()["data"]
    save_cached_surah_metadata(surah, data, edition)
    return data

def ensure_audio_cached(surah, ayah, reciter, ayah_data):
    audio_file = audio_path(surah, ayah, reciter)
    if os.path.exists(audio_file):
        return audio_file, True

    Path(audio_file).parent.mkdir(parents=True, exist_ok=True)

    global_ayah_number = ayah_data.get("number")
    if global_ayah_number is None:
        raise RuntimeError(f"Global ayah number missing for {surah}:{ayah}")

    urls = _audio_urls(reciter, surah, ayah, global_ayah_number)
    if not urls:
        raise RuntimeError(f"No audio source for reciter {reciter}")

    urls = [u for u in urls if not _SOURCE_HEALTH.is_disabled(u.split("/")[2])]
    if not urls:
        raise RuntimeError(f"All audio sources disabled ({surah}:{ayah})")

    last_err = None
    for url in urls:
        host = url.split("/")[2]
        try:
            log.info("Downloading %s:%s from %s...", surah, ayah, host)
            resp = request_with_retry(url)
            with open(audio_file, "wb") as f:
                f.write(resp.content)
            _SOURCE_HEALTH.record_success(host)
            return audio_file, False
        except Exception as e:
            last_err = e
            _SOURCE_HEALTH.record_failure(host)
            log.warning("  %s failed: %s", host, e.__class__.__name__)

    raise last_err or RuntimeError("All audio sources failed")

def build_ayah_lookup(surah_data):
    return {a["numberInSurah"]: a for a in surah_data["ayahs"]}

def get_cached_wbw(surah, ayah, lang):
    path = words_path(surah, ayah, lang)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Corrupt words file %s:%s: %s", surah, ayah, e)
        return None

def save_cached_wbw(surah, ayah, lang, data):
    path = Path(words_path(surah, ayah, lang))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ------------------------------------------------------------
# Warmup
# ------------------------------------------------------------

class WarmupLoader(QThread):
    progress = Signal(int, int, str)
    finished_warmup = Signal()

    def __init__(self, reciters, translations, queue, max_workers=4, parent=None):
        super().__init__(parent)
        self._reciters = list(reciters)
        self._translations = list(translations)
        self._queue = [q for q in queue if q.kind == "quran"]
        self._max_workers = max(1, int(max_workers))

    def run(self):
        surahs = sorted({q.surah for q in self._queue})
        meta_editions = list(dict.fromkeys(self._reciters + self._translations))
        meta_jobs = [(ed, s) for ed in meta_editions for s in surahs]
        audio_jobs = [(r, q.surah, q.ayah) for r in self._reciters for q in self._queue]
        total = len(meta_jobs) + len(audio_jobs)
        current = 0
        current_lock = threading.Lock()
        meta_locks = {}
        meta_locks_lock = threading.Lock()

        def meta_lock(key):
            with meta_locks_lock:
                l = meta_locks.get(key)
                if l is None:
                    l = meta_locks[key] = threading.Lock()
                return l

        def tick(label):
            nonlocal current
            with current_lock:
                current += 1
                c = current
            self.progress.emit(c, total, label)

        def fetch_meta(edition, surah):
            if self.isInterruptionRequested():
                return
            with meta_lock((edition, surah)):
                try:
                    get_surah_data(surah, edition)
                except Exception as e:
                    log.warning("Warmup metadata %s/%s failed: %s", surah, edition, e)
            tick(f"Downloading text · {edition}")

        if meta_jobs:
            with ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="warmup-meta") as pool:
                futures = [pool.submit(fetch_meta, ed, s) for ed, s in meta_jobs]
                for fut in as_completed(futures):
                    if self.isInterruptionRequested():
                        for f in futures:
                            f.cancel()
                        return
                    fut.result()

        def fetch_audio(reciter, surah, ayah):
            if self.isInterruptionRequested():
                return
            try:
                surah_data = get_surah_data(surah, reciter)
                ayah_data = build_ayah_lookup(surah_data).get(ayah)
                if ayah_data is None:
                    return
                ensure_audio_cached(surah, ayah, reciter, ayah_data)
            except Exception as e:
                log.warning("Warmup audio %s:%s (%s) failed: %s", surah, ayah, reciter, e)
            tick(f"Downloading audio · {reciter}")

        if audio_jobs:
            with ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="warmup-audio") as pool:
                futures = [pool.submit(fetch_audio, r, s, a) for r, s, a in audio_jobs]
                for fut in as_completed(futures):
                    if self.isInterruptionRequested():
                        for f in futures:
                            f.cancel()
                        return
                    fut.result()

        self.finished_warmup.emit()

# ------------------------------------------------------------
# Resolver
# ------------------------------------------------------------

class _Resolver:

    def __init__(self, reciter, translation_edition):
        self.reciter = reciter
        self.translation_edition = translation_edition
        self.arabic, self.arabic_lookup = {}, {}
        self.trans, self.trans_lookup = {}, {}
        self.trans_failed = set()
        self._locks = {}
        self._locks_lock = threading.Lock()

    def _surah_lock(self, surah):
        with self._locks_lock:
            lock = self._locks.get(surah)
            if lock is None:
                lock = self._locks[surah] = threading.Lock()
            return lock

    def get_ayah_metadata(self, surah, ayah):
        with self._surah_lock(surah):
            if surah not in self.arabic:
                self.arabic[surah] = get_surah_data(surah, self.reciter)
                self.arabic_lookup[surah] = build_ayah_lookup(self.arabic[surah])
        ayah_data = self.arabic_lookup[surah].get(ayah)
        if ayah_data is None:
            raise ValueError(f"Ayah {ayah} not found in surah {surah}")

        translation = ""
        if self.translation_edition and surah not in self.trans_failed:
            try:
                with self._surah_lock(surah):
                    if surah not in self.trans:
                        self.trans[surah] = get_surah_data(surah, self.translation_edition)
                        self.trans_lookup[surah] = build_ayah_lookup(self.trans[surah])
                t = self.trans_lookup[surah].get(ayah)
                translation = t.get("text", "") if t else ""
            except Exception as e:
                self.trans_failed.add(surah)
                log.warning("Translation unavailable for surah %s: %s", surah, e)
        return ayah_data, self.arabic[surah], translation

    def load(self, surah, ayah):
        ayah_data, surah_data, translation = self.get_ayah_metadata(surah, ayah)
        audio_file, _ = ensure_audio_cached(surah, ayah, self.reciter, ayah_data)
        return ayah_data, surah_data, translation, audio_file

# ------------------------------------------------------------
# Playlist loader
# ------------------------------------------------------------

class PlaylistLoader(QThread):
    bismillah_ready = Signal(object)
    item_loaded = Signal(int, object)
    finished_loading = Signal()

    def __init__(self, jobs, reciter, translation_edition, max_workers=4, parent=None):
        super().__init__(parent)
        self._jobs = jobs
        self._reciter = reciter
        self._translation = translation_edition
        self._max_workers = max(1, int(max_workers))

    def run(self):
        r = _Resolver(self._reciter, self._translation)
        try:
            ayah_data, surah_data, translation, audio = r.load(BISMILLAH_SURAH, BISMILLAH_AYAH)
            self.bismillah_ready.emit(
                LoadedEntry(
                    kind="bismillah",
                    surah=BISMILLAH_SURAH,
                    ayah=BISMILLAH_AYAH,
                    description="Bismillah",
                    audio_file=audio,
                    data=ayah_data,
                    surah_data=surah_data,
                    translation=translation,
                    loaded=True,
                ))
        except Exception as e:
            log.error("Failed to load Bismillah: %s", e)

        if not self._jobs:
            self.finished_loading.emit()
            return

        def fetch_one(job):
            index, item = job
            if item.kind == "custom":
                return index, placeholder(item)
            base = placeholder(item)
            try:
                ayah_data, surah_data, translation, audio = r.load(item.surah, item.ayah)
                return index, replace(base,
                                      audio_file=audio,
                                      data=ayah_data,
                                      surah_data=surah_data,
                                      translation=translation,
                                      loaded=True)
            except Exception as e:
                log.error("Failed to load %s:%s - %s", item.surah, item.ayah, e)
                return index, replace(base, loaded=True, error=str(e))

        pool = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="loader")
        try:
            futures = [pool.submit(fetch_one, job) for job in self._jobs]
            for fut in as_completed(futures):
                if self.isInterruptionRequested():
                    for f in futures:
                        f.cancel()
                    return
                try:
                    index, entry = fut.result()
                    self.item_loaded.emit(index, entry)
                except Exception as e:
                    log.exception("Loader worker crashed: %s", e)
        finally:
            pool.shutdown(wait=False)
        self.finished_loading.emit()

# ------------------------------------------------------------
# Model
# ------------------------------------------------------------

class PlaylistModel(QAbstractListModel):
    LABEL, GROUP, STATUS, ERROR, AYAH_NO = 257, 258, 259, 260, 261

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[LoadedEntry] = []

    def roleNames(self):
        return {
            self.LABEL: QByteArray(b"label"),
            self.GROUP: QByteArray(b"group"),
            self.STATUS: QByteArray(b"status"),
            self.ERROR: QByteArray(b"errorText"),
            self.AYAH_NO: QByteArray(b"ayahNo"),
        }

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._entries)

    @staticmethod
    def _label(e: LoadedEntry) -> str:
        if e.kind == "custom":
            return e.description
        name = e.surah_data.get("englishName") if e.surah_data else None
        return f"{name} · {e.ayah}" if name else f"{e.surah}:{e.ayah}"

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._entries)):
            return None
        e = self._entries[index.row()]
        if role == self.LABEL: return self._label(e)
        if role == self.GROUP: return e.section
        if role == self.STATUS: return "error" if e.error else ("ready" if e.loaded else "loading")
        if role == self.ERROR: return e.error or ""
        if role == self.AYAH_NO: return e.ayah if e.kind == "quran" else 0
        return None

    def reset_entries(self, entries):
        self.beginResetModel()
        self._entries = entries
        self.endResetModel()

    def update(self, row, entry):
        if not (0 <= row < len(self._entries)):
            return
        self._entries[row] = entry
        ix = self.index(row)
        self.dataChanged.emit(ix, ix)

    def entry(self, row) -> Optional[LoadedEntry]:
        return self._entries[row] if 0 <= row < len(self._entries) else None

    def is_playable(self, row) -> bool:
        e = self.entry(row)
        return bool(e and e.loaded and not e.error)

    def first_index(self):
        return next((i for i, e in enumerate(self._entries) if not e.error), None)

    def next_index(self, row):
        for i in range(row + 1, len(self._entries)):
            if not self._entries[i].error:
                return i
        return None

    def prev_index(self, row):
        for i in range(row - 1, -1, -1):
            if self.is_playable(i):
                return i
        return None

# ------------------------------------------------------------
# Controller
# ------------------------------------------------------------

class PlayerController(QObject):
    contentReset = Signal()
    currentIndexChanged = Signal()
    playingChanged = Signal()
    positionChanged = Signal()
    durationChanged = Signal()
    volumeChanged = Signal()
    mutedChanged = Signal()
    translationChanged = Signal()
    loadingChanged = Signal()
    toast = Signal(str)
    loopChanged = Signal()
    reciterChanged = Signal()
    wordByWordChanged = Signal()
    wordsChanged = Signal()
    repeatChanged = Signal()
    initStateChanged = Signal()
    availablePlaylistsChanged = Signal()
    currentPlaylistChanged = Signal()

    def __init__(self, model, font_family, parent=None):
        super().__init__(parent)
        self.model = model
        self._font_family = font_family
        self._bangla_font_family = "Noto Sans Bengali"

        self._settings = QSettings("ruqya-quran", "ruqya-quran")

        # --- playlist (opened from a .ruqya file) ---
        self._playlist: dict = {"name": "", "items": []}
        self._playlist_path = ""
        self._recent: list = self._load_recent()

        # --- persisted: reciter / translation / volume / showTranslation ---
        saved_reciter = self._settings.value("ui/reciter", DEFAULT_RECITER, type=str)
        self._reciter = saved_reciter if saved_reciter in RECITERS else DEFAULT_RECITER

        saved_trans = self._settings.value("ui/translation", DEFAULT_TRANSLATION, type=str)
        self._translation_edition = saved_trans if saved_trans in TRANSLATIONS else DEFAULT_TRANSLATION

        try:
            saved_vol = float(self._settings.value("ui/volume", 1.0, type=float))
        except (TypeError, ValueError):
            saved_vol = 1.0
        self._volume = max(0.0, min(1.0, saved_vol))
        self._muted = False

        self._show_translation = self._settings.value("ui/showTranslation", True, type=bool)

        # --- session-only state ---
        self._word_by_word = False
        self._word_by_word_data: list = []
        self._words_with_state: list = []

        # Repeat: -1 = Auto (use item JSON), 0 = ∞, 1..N = explicit
        self._ayah_repeat = -1
        self._group_repeat = -1
        self._playlist_loop = False

        self._ayah_pass = 0
        self._group_pass = 0
        self._current_group_id = ""

        self._queue: list[QueueItem] = []
        self._loader: Optional[PlaylistLoader] = None
        self._warmup: Optional[WarmupLoader] = None
        self._bismillah: Optional[LoadedEntry] = None

        self._current = -1
        self._stage = "main"
        self._pending = -1
        self._resume_index = -1

        self._position = self._duration = 0
        self._playing = False
        self._loop_a = self._loop_b = -1
        self._loop_total = 3
        self._loop_done = 0
        self._loop_guard = False

        self._loaded = self._total = self._failed = 0
        self._loading = False

        self._initializing = False
        self._init_message = ""
        self._init_current = 0
        self._init_total = 0

        self._title = self._title_ar = self._subtitle = ""
        self._arabic = self._translation = ""

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._apply_volume()
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_player_error)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._on_state)

    # ---------------- QML properties ----------------

    @Property(str, constant=True)
    def fontFamily(self):
        return self._font_family

    @Property(str, constant=True)
    def banglaFontFamily(self):
        return self._bangla_font_family

    @Property(list, constant=True)
    def reciterNames(self):
        return [{"id": k, "name": v} for k, v in RECITERS.items()]

    @Property(list, constant=True)
    def translationNames(self):
        return [{"id": k, "name": v} for k, v in TRANSLATIONS.items()]

    # ---- recent playlists (also exposed as the Picker's model) ----
    def _load_recent(self) -> list:
        try:
            raw = json.loads(self._settings.value("ui/recent", "[]", type=str))
        except (ValueError, TypeError):
            raw = []
        return [r for r in raw if isinstance(r, dict) and os.path.isfile(r.get("path", ""))][:10]

    def _remember(self, path: str, name: str) -> None:
        self._recent = ([{"path": path, "name": name}] + [r for r in self._recent if r["path"] != path])[:10]
        self._settings.setValue("ui/recent", json.dumps(self._recent))
        self._settings.setValue("ui/lastPlaylist", path)
        self.availablePlaylistsChanged.emit()

    @Property(list, notify=availablePlaylistsChanged)
    def availablePlaylists(self):
        return [{"id": r["path"], "name": r["name"]} for r in self._recent]

    @Property(str, notify=currentPlaylistChanged)
    def currentPlaylistId(self):
        return self._playlist_path

    @Property(str, notify=currentPlaylistChanged)
    def playlistName(self):
        return self._playlist.get("name", "")

    @Property(bool, notify=currentPlaylistChanged)
    def hasPlaylist(self):
        return bool(self._playlist_path)

    @Slot(str)
    def setPlaylist(self, playlist_id):
        if playlist_id != self._playlist_path:
            self.openPlaylist(playlist_id)

    @Slot(str, result=bool)
    def openPlaylist(self, location):
        path = (Path(QUrl(location).toLocalFile()) if location.startswith("file:") else Path(location).expanduser())
        try:
            data = read_playlist_file(path)
        except (OSError, ValueError) as e:
            self.toast.emit(f"Can't open playlist: {e}")
            return False

        self.shutdown()
        ws = Workspace(path, data["data_dir"])
        set_workspace(ws, data["offline"])
        self._playlist, self._playlist_path = data, str(ws.playlist_path)
        self._bismillah = None  # belongs to the old reciter

        if data["reciter"] in RECITERS:  # file default; not written back
            self._reciter = data["reciter"]
        if data["translation"] in TRANSLATIONS:
            self._translation_edition = data["translation"]

        self._remember(self._playlist_path, data["name"])
        self.reciterChanged.emit()
        self.translationChanged.emit()
        self.currentPlaylistChanged.emit()
        self._restart_loader(keep_position=False)
        return True

    def openInitial(self, args):
        """argv file first, else last used playlist, else the empty state."""
        for a in args:
            if not a.startswith("-") and self.openPlaylist(a):
                return
        last = self._settings.value("ui/lastPlaylist", "", type=str)
        if last and os.path.isfile(last):
            self.openPlaylist(last)

    # --- reciter / translation ---
    @Property(str, notify=reciterChanged)
    def currentReciter(self):
        return self._reciter

    @Property(str, notify=translationChanged)
    def currentTranslation(self):
        return self._translation_edition

    @Slot(str)
    def setReciter(self, reciter_id):
        if self._initializing: return
        if reciter_id in RECITERS and reciter_id != self._reciter:
            self._reciter = reciter_id
            self._settings.setValue("ui/reciter", reciter_id)
            self.reciterChanged.emit()
            self.toast.emit(f"Reciter: {RECITERS[reciter_id]} — reloading")
            self._restart_loader(keep_position=True)

    @Slot(str)
    def setTranslation(self, edition):
        if self._initializing: return
        if edition in TRANSLATIONS and edition != self._translation_edition:
            self._translation_edition = edition
            self._settings.setValue("ui/translation", edition)
            self.translationChanged.emit()
            self.toast.emit(f"Translation: {TRANSLATIONS[edition]} — reloading")
            self._restart_loader(keep_position=True)
            if self._word_by_word:
                self._fetch_word_by_word()

    # --- word-by-word ---
    @Property(bool, notify=wordByWordChanged)
    def wordByWord(self):
        return self._word_by_word

    @wordByWord.setter
    def wordByWord(self, v):
        v = bool(v)
        if v != self._word_by_word:
            self._word_by_word = v
            if not v:
                self._word_by_word_data = []
                self._words_with_state = []
                self.wordsChanged.emit()
            self.wordByWordChanged.emit()
            if v:
                self._fetch_word_by_word()

    @Property(list, notify=wordsChanged)
    def words(self):
        return self._words_with_state

    # --- core player state ---
    @Property(int, notify=currentIndexChanged)
    def currentIndex(self):
        return self._current

    @Property(bool, notify=playingChanged)
    def isPlaying(self):
        return self._playing

    @Property(int, notify=positionChanged)
    def position(self):
        return self._position

    @Property(int, notify=durationChanged)
    def duration(self):
        return self._duration

    @Property(str, notify=contentReset)
    def title(self):
        return self._title

    @Property(str, notify=contentReset)
    def titleArabic(self):
        return self._title_ar

    @Property(str, notify=contentReset)
    def subtitle(self):
        return self._subtitle

    @Property(str, notify=contentReset)
    def arabicText(self):
        return self._arabic

    @Property(str, notify=contentReset)
    def translationText(self):
        return self._translation

    @Property(bool, notify=loadingChanged)
    def loading(self):
        return self._loading

    @Property(int, notify=loadingChanged)
    def loadedCount(self):
        return self._loaded

    @Property(int, notify=loadingChanged)
    def totalCount(self):
        return self._total

    @Property(int, notify=loadingChanged)
    def failedCount(self):
        return self._failed

    @Property(bool, notify=initStateChanged)
    def initializing(self):
        return self._initializing

    @Property(str, notify=initStateChanged)
    def initMessage(self):
        return self._init_message

    @Property(int, notify=initStateChanged)
    def initCurrent(self):
        return self._init_current

    @Property(int, notify=initStateChanged)
    def initTotal(self):
        return self._init_total

    # --- volume (persisted) ---
    @Property(float, notify=volumeChanged)
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, v):
        v = max(0.0, min(1.0, float(v)))
        if v != self._volume:
            self._volume = v
            self._apply_volume()
            self._settings.setValue("ui/volume", v)
            self.volumeChanged.emit()

    @Property(bool, notify=mutedChanged)
    def muted(self):
        return self._muted

    @muted.setter
    def muted(self, m):
        if bool(m) != self._muted:
            self._muted = bool(m)
            self._audio.setMuted(self._muted)
            self.mutedChanged.emit()

    # --- showTranslation (persisted) ---
    @Property(bool, notify=translationChanged)
    def showTranslation(self):
        return self._show_translation

    @showTranslation.setter
    def showTranslation(self, v):
        v = bool(v)
        if v != self._show_translation:
            self._show_translation = v
            self._settings.setValue("ui/showTranslation", v)
            self.translationChanged.emit()

    # --- loop A-B (session only) ---
    @Property(int, notify=loopChanged)
    def loopStart(self):
        return self._loop_a

    @Property(int, notify=loopChanged)
    def loopEnd(self):
        return self._loop_b

    @Property(int, notify=loopChanged)
    def loopTotal(self):
        return self._loop_total

    @Property(int, notify=loopChanged)
    def loopDone(self):
        return self._loop_done

    @Property(bool, notify=loopChanged)
    def loopActive(self):
        return self._loop_valid()

    # --- repeat (session only) ---
    @Property(int, notify=repeatChanged)
    def ayahRepeat(self):
        return self._ayah_repeat

    @ayahRepeat.setter
    def ayahRepeat(self, v):
        v = max(-1, int(v))
        if v != self._ayah_repeat:
            self._ayah_repeat = v
            self.repeatChanged.emit()

    @Property(int, notify=repeatChanged)
    def groupRepeat(self):
        return self._group_repeat

    @groupRepeat.setter
    def groupRepeat(self, v):
        v = max(-1, int(v))
        if v != self._group_repeat:
            self._group_repeat = v
            self.repeatChanged.emit()

    @Property(bool, notify=repeatChanged)
    def playlistLoop(self):
        return self._playlist_loop

    @playlistLoop.setter
    def playlistLoop(self, v):
        v = bool(v)
        if v != self._playlist_loop:
            self._playlist_loop = v
            self.repeatChanged.emit()

    def _cur_q(self) -> Optional[QueueItem]:
        return self._queue[self._current] if 0 <= self._current < len(self._queue) else None

    def _eff_ayah_repeat(self) -> int:
        if self._ayah_repeat != -1:
            return self._ayah_repeat
        q = self._cur_q()
        return q.ayah_repeat if q else 1

    def _eff_group_repeat(self) -> int:
        if self._group_repeat != -1:
            return self._group_repeat
        q = self._cur_q()
        return q.group_repeat if q else 1

    @Property(int, notify=repeatChanged)
    def playlistAyahRepeat(self):
        q = self._cur_q()
        return q.ayah_repeat if q else 1

    @Property(int, notify=repeatChanged)
    def playlistGroupRepeat(self):
        q = self._cur_q()
        return q.group_repeat if q else 1

    @Property(int, notify=repeatChanged)
    def effAyahRepeat(self):
        return self._eff_ayah_repeat()

    @Property(int, notify=repeatChanged)
    def effGroupRepeat(self):
        return self._eff_group_repeat()

    @Property(int, notify=repeatChanged)
    def ayahPass(self):
        return self._ayah_pass + 1

    @Property(int, notify=repeatChanged)
    def groupPass(self):
        return self._group_pass + 1

    @Slot(int)
    def setAyahRepeat(self, v):
        self.ayahRepeat = v

    @Slot(int)
    def setGroupRepeat(self, v):
        self.groupRepeat = v

    @Slot()
    def cycleAyahRepeat(self):
        opts = (-1, 1, 2, 3, 5, 10, 0)
        i = opts.index(self._ayah_repeat) if self._ayah_repeat in opts else 0
        self.ayahRepeat = opts[(i + 1) % len(opts)]
        self._toast_repeat()

    @Slot()
    def cycleGroupRepeat(self):
        opts = (-1, 1, 2, 3, 5, 10, 0)
        i = opts.index(self._group_repeat) if self._group_repeat in opts else 0
        self.groupRepeat = opts[(i + 1) % len(opts)]
        self._toast_repeat()

    @Slot()
    def togglePlaylistLoop(self):
        self.playlistLoop = not self._playlist_loop

    def _toast_repeat(self):

        def f(n):
            return "∞" if n == 0 else str(n)

        a = self._eff_ayah_repeat()
        g = self._eff_group_repeat()
        self.toast.emit(f"Each ayah ×{f(a)} · Section ×{f(g)}")

    def _apply_volume(self):
        self._audio.setVolume(self._volume**2)

    # ---------------- Load ----------------

    def _preload_reciters(self) -> list:
        want = [r for r in self._playlist.get("preload_reciters", []) if r in RECITERS]
        return want or PRELOAD_RECITERS

    def _preload_translations(self) -> list:
        want = [t for t in self._playlist.get("preload_translations", []) if t in TRANSLATIONS]
        return want or PRELOAD_TRANSLATIONS

    def _restart_loader(self, keep_position: bool = True):
        keep_index = self._current if (keep_position and self._current >= 0) else -1
        self.shutdown()
        self._player.stop()
        self._current = -1
        self._stage = "main"
        self._pending = -1
        self._resume_index = keep_index
        self._current_group_id = ""
        self._ayah_pass = self._group_pass = 0
        self._position = 0
        self._duration = 0
        self._word_by_word_data = []
        self._words_with_state = []
        self.clearLoop()
        self.currentIndexChanged.emit()
        self.positionChanged.emit()
        self.durationChanged.emit()
        self.wordsChanged.emit()
        self.start()

    def start(self):
        if _WS is None:
            return
        self._queue = build_queue_from_items(self._playlist["items"])
        if not self._queue:
            self.model.reset_entries([])
            self._current = -1
            self.currentIndexChanged.emit()
            self.contentReset.emit()
            return
        if _OFFLINE or self._is_data_complete(self._queue):
            log.info("Data complete or offline — skipping warmup")
            self._begin_playlist_load()
            return
        self._start_warmup()

    def _is_data_complete(self, queue) -> bool:
        quran_items = [q for q in queue if q.kind == "quran"]
        surahs = {q.surah for q in quran_items}
        reciters = set(self._preload_reciters()) | {self._reciter}
        editions = (reciters | set(self._preload_translations()) | {self._translation_edition})
        for edition in editions:
            for surah in surahs:
                if not os.path.exists(text_path(surah, edition)):
                    return False
        for reciter in reciters:
            for q in quran_items:
                if not os.path.exists(audio_path(q.surah, q.ayah, reciter)):
                    return False
        return True

    def _start_warmup(self):
        self._initializing = True
        self._init_message = "Preparing audio for all reciters…"
        self._init_current = 0
        self._init_total = 0
        self.initStateChanged.emit()

        self._warmup = WarmupLoader(self._preload_reciters(),
                                    self._preload_translations(),
                                    self._queue,
                                    max_workers=MAX_WORKERS)
        self._warmup.progress.connect(self._on_warmup_progress)
        self._warmup.finished_warmup.connect(self._on_warmup_finished)
        self._warmup.start()

    def _on_warmup_progress(self, current, total, message):
        self._init_current = current
        self._init_total = total
        self._init_message = message
        self.initStateChanged.emit()

    def _on_warmup_finished(self):
        log.info("Warmup finished. Disabled sources: %s", _SOURCE_HEALTH.disabled_hosts() or "none")
        self._initializing = False
        self.initStateChanged.emit()
        self._begin_playlist_load()

    def _begin_playlist_load(self):
        entries = [placeholder(q) for q in self._queue]
        self.model.reset_entries(entries)
        quran_jobs = [(i, q) for i, q in enumerate(self._queue) if q.kind == "quran"]
        custom_count = len(self._queue) - len(quran_jobs)
        self._loaded = custom_count
        self._failed = sum(1 for i, _ in enumerate(self._queue) if self.model.entry(i) and self.model.entry(i).error)
        self._total = len(self._queue)
        if quran_jobs:
            self._run_loader(quran_jobs)
        else:
            self._on_load_finished()

    def _run_loader(self, jobs):
        self._loader = PlaylistLoader(jobs, self._reciter, self._translation_edition, max_workers=MAX_WORKERS)
        self._loader.bismillah_ready.connect(self._on_bismillah)
        self._loader.item_loaded.connect(self._on_item_loaded)
        self._loader.finished_loading.connect(self._on_load_finished)
        self._loading = True
        self.loadingChanged.emit()
        self._loader.start()

    @Slot()
    def retry(self):
        if self._loading or self._initializing:
            return
        jobs = []
        for i, item in enumerate(self._queue):
            e = self.model.entry(i)
            if e and e.error and item.kind == "quran":
                self.model.update(i, placeholder(item))
                jobs.append((i, item))
        if jobs:
            self._loaded, self._failed, self._total = 0, 0, len(jobs)
            self._run_loader(jobs)

    def _on_bismillah(self, entry):
        self._bismillah = entry

    def _on_item_loaded(self, index, entry):
        try:
            self.model.update(index, entry)
            self._loaded += 1
            if entry.error:
                self._failed += 1
            self.loadingChanged.emit()
            if self._current < 0 and self.model.is_playable(index) and self._resume_index < 0:
                self._select(index)
            if index == self._pending:
                self._pending = -1
                self.play(index)
        except Exception as e:
            log.exception("_on_item_loaded failed: %s", e)

    def _on_load_finished(self):
        self._loading = False
        self.loadingChanged.emit()
        if self._current < 0 and self._resume_index >= 0 and self.model.is_playable(self._resume_index):
            idx = self._resume_index
            self._resume_index = -1
            self.play(idx)
            return
        self._resume_index = -1
        if self._current < 0:
            for i in range(self.model.rowCount()):
                if self.model.is_playable(i):
                    self._select(i)
                    break

    def shutdown(self):
        if self._warmup is not None and self._warmup.isRunning():
            self._warmup.requestInterruption()
            self._warmup.wait(3000)
        if self._loader is not None and self._loader.isRunning():
            self._loader.requestInterruption()
            if not self._loader.wait(3000):
                self._loader.terminate()
                self._loader.wait()

    # ---------------- Word-by-word ----------------

    def _wbw_language(self) -> str:
        if WORD_BY_WORD_LANGUAGE in ("en", "bn"):
            return WORD_BY_WORD_LANGUAGE
        ed = (self._translation_edition or "").lower()
        return "bn" if ed.startswith("bn") else "en"

    def _fetch_word_by_word(self):
        self._word_by_word_data = []
        self._words_with_state = []
        self.wordsChanged.emit()

        if self._initializing or self._current < 0:
            return
        e = self.model.entry(self._current)
        if not e or e.kind == "custom" or not e.surah:
            return
        if self._stage == "bismillah":
            return
        if e.surah == 1 and e.ayah == 1:
            return

        lang = self._wbw_language()
        want_bangla = (lang == "bn")
        surah, ayah = e.surah, e.ayah

        def work():
            cached = get_cached_wbw(surah, ayah, lang)
            if cached is not None:
                self._word_by_word_data = cached
                self._rebuild_words_with_state()
                return
            try:
                url = WORD_BY_WORD_URL.format(surah=surah, ayah=ayah, lang=lang)
                resp = request_with_retry(url)
                words = resp.json().get("verse", {}).get("words", [])
                out = []
                have_bangla = False
                for w in words:
                    trans = w.get("translation", {}) or {}
                    trans_lang = (trans.get("language_name") or "").lower()
                    text = trans.get("text", "") or ""
                    is_bn = trans_lang in ("bengali", "bangla", "bn")
                    arabic = w.get("text_uthmani", "") or ""
                    if is_bn:
                        have_bangla = True
                        out.append({"arabic": arabic, "english": "", "bangla": text})
                    else:
                        out.append({"arabic": arabic, "english": text, "bangla": ""})
                if want_bangla and not have_bangla:
                    try:
                        bn_data = get_surah_data(surah, "bn.bengali")
                        bn_ayah = build_ayah_lookup(bn_data).get(ayah, {}).get("text", "")
                        if bn_ayah:
                            out.append({"arabic": "", "english": "", "bangla": bn_ayah})
                    except Exception as ex:
                        log.warning("Bangla ayah fallback failed: %s", ex)
                if out:
                    try:
                        save_cached_wbw(surah, ayah, lang, out)
                    except OSError as ex:
                        log.warning("Could not write words cache: %s", ex)
                self._word_by_word_data = out
            except Exception as exc:
                log.warning("Word-by-word fetch failed: %s", exc)
                self._word_by_word_data = []
            self._rebuild_words_with_state()

        threading.Thread(target=work, daemon=True).start()

    def _rebuild_words_with_state(self):
        out = []
        for i, w in enumerate(self._word_by_word_data):
            out.append({
                "index": i,
                "arabic": w.get("arabic", ""),
                "english": w.get("english", ""),
                "bangla": w.get("bangla", ""),
            })
        self._words_with_state = out
        self.wordsChanged.emit()

    # ---------------- Selection / display ----------------

    def _select(self, index):
        self._current = index
        self._stage = "main"
        self.currentIndexChanged.emit()
        self.repeatChanged.emit()
        self._refresh_display()
        if self._word_by_word:
            self._fetch_word_by_word()

    def _refresh_display(self):
        e = self.model.entry(self._current)
        t = ta = sub = ar = tr = ""
        if e and e.loaded and not e.error:
            if self._stage == "bismillah" and self._bismillah:
                t = "Bismillah"
                sub = f"Before {e.description}"
                ar = self._bismillah.data.get("text", "")
                tr = self._bismillah.translation
            elif e.kind == "custom":
                t = e.description
                sub = e.section or CUSTOM_PLAYLIST_SEPARATOR_LABEL
                ar = e.data.get("text", "")
                tr = e.translation
            else:
                t = e.surah_data.get("englishName", "")
                ta = e.surah_data.get("name", "")
                sub = f"Ayah {e.ayah}"
                ar = e.data.get("text", "")
                tr = e.translation
        self._title, self._title_ar, self._subtitle = t, ta, sub
        self._arabic, self._translation = ar, tr
        self.contentReset.emit()

    # ---------------- Playback ----------------

    def _bismillah_ok(self):
        b = self._bismillah
        return bool(b and not b.error and os.path.exists(b.audio_file))

    def _start_audio(self, path):
        if not os.path.exists(path):
            self.toast.emit(f"Audio file not found: {path}")
            return
        url = QUrl.fromLocalFile(path)
        if url == self._player.source():
            self._player.setPosition(0)
        else:
            self._player.setSource(url)
        self._refresh_display()
        self._player.play()

    def _first_in_group(self, group_id):
        for i, q in enumerate(self._queue):
            if q.group_id == group_id:
                return i
        return None

    def _enter_playback(self, index):
        item = self._queue[index] if 0 <= index < len(self._queue) else None
        if not item:
            return
        if item.group_id != self._current_group_id:
            self._current_group_id = item.group_id
            self._group_pass = 0
        self._ayah_pass = 0
        self.repeatChanged.emit()

    @Slot(int)
    def play(self, index):
        if self._initializing: return
        entry = self.model.entry(index)
        if entry is None: return
        if entry.error:
            self.toast.emit("This item couldn't be loaded")
            return
        if not entry.loaded:
            self._pending = index
            self.toast.emit("Downloading — it will play as soon as it's ready")
            return
        self._pending = -1
        if index != self._current:
            self.clearLoop()
            self._current = index
            self.currentIndexChanged.emit()
        self._enter_playback(index)
        self._stage = "main"
        path = entry.audio_file
        if entry.lead_bismillah and self._bismillah_ok():
            self._stage = "bismillah"
            path = self._bismillah.audio_file
        self._start_audio(path)
        if self._word_by_word:
            self._fetch_word_by_word()
        else:
            self._rebuild_words_with_state()

    def _replay_current(self):
        entry = self.model.entry(self._current)
        if not entry: return
        self._stage = "main"
        self._start_audio(entry.audio_file)

    @Slot()
    def toggle(self):
        if self._initializing: return
        if self._playing:
            self._player.pause()
        elif (self._current >= 0 and self._player.source().isValid()
              and self._player.mediaStatus() != QMediaPlayer.MediaStatus.EndOfMedia):
            self._player.play()
        else:
            target = self._current if self._current >= 0 else self.model.first_index()
            if target is not None:
                self.play(target)

    @Slot()
    def playNext(self):
        if self._initializing: return
        if self._current < 0:
            first = self.model.first_index()
            if first is not None: self.play(first)
            return
        nxt = self.model.next_index(self._current)
        if nxt is None and self._playlist_loop:
            nxt = self.model.first_index()
            self._current_group_id = ""
        if nxt is None:
            self.toast.emit("End of playlist")
        else:
            self.play(nxt)

    @Slot()
    def playPrevious(self):
        if self._initializing: return
        if self._current < 0: return
        if self._position > 3000:
            self.seek(0)
            return
        prev = self.model.prev_index(self._current)
        if prev is None: self.seek(0)
        else: self.play(prev)

    @Slot(int)
    def seek(self, ms):
        self._player.setPosition(max(0, int(ms)))

    @Slot(int)
    def seekBy(self, delta_ms):
        end = self._duration or (self._position + abs(delta_ms))
        self.seek(max(0, min(end, self._position + int(delta_ms))))

    # ---------------- A-B loop ----------------

    def _loop_valid(self):
        return self._loop_a >= 0 and self._loop_b > self._loop_a

    def _loop_running(self):
        return self._stage == "main" and self._loop_valid()

    def _loop_hit(self):
        self._loop_done += 1
        if self._loop_total and self._loop_done >= self._loop_total:
            self.clearLoop()
            self.toast.emit("Loop finished")
            return False
        self.loopChanged.emit()
        self._loop_guard = True
        self._player.setPosition(self._loop_a)
        return True

    def _can_mark(self):
        return (self._stage == "main" and self._current >= 0 and self._player.source().isValid())

    @Slot()
    def markStart(self):
        if not self._can_mark(): return
        self._loop_a = self._position
        if self._loop_b <= self._loop_a: self._loop_b = -1
        self._loop_done = 0
        self._loop_guard = False
        self.loopChanged.emit()

    @Slot()
    def markEnd(self):
        if not self._can_mark(): return
        if self._loop_a < 0: self._loop_a = 0
        if self._position - self._loop_a < 300:
            self.toast.emit("The end must come after the start")
            return
        self._loop_b = self._position
        self._loop_done = 0
        self.loopChanged.emit()
        self._loop_guard = True
        self._player.setPosition(self._loop_a)
        self._player.play()

    @Slot()
    def clearStart(self):
        self._loop_a = -1
        if self._loop_a < 0:
            self._loop_b = -1
        self._loop_guard = False
        self.loopChanged.emit()

    @Slot()
    def clearEnd(self):
        self._loop_b = -1
        self._loop_guard = False
        self.loopChanged.emit()

    @Slot()
    def clearLoop(self):
        self._loop_a = self._loop_b = -1
        self._loop_done = 0
        self._loop_guard = False
        self.loopChanged.emit()

    @Slot()
    def cycleLoopCount(self):
        opts = (3, 5, 7, 10, 0)
        i = opts.index(self._loop_total) if self._loop_total in opts else 0
        self._loop_total = opts[(i + 1) % len(opts)]
        self.loopChanged.emit()

    # ---------------- Player signals ----------------

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            QTimer.singleShot(0, self._on_finished)

    def _on_finished(self):
        entry = self.model.entry(self._current)
        if entry is None: return

        if self._stage == "bismillah":
            self._stage = "main"
            self._start_audio(entry.audio_file)
            return

        if self._loop_running() and self._loop_hit():
            self._player.play()
            return

        self._ayah_pass += 1
        n = self._eff_ayah_repeat()
        if n == 0 or self._ayah_pass < n:
            self.repeatChanged.emit()
            self._replay_current()
            return

        nxt = self.model.next_index(self._current)
        if nxt is None and self._playlist_loop:
            nxt = self.model.first_index()

        leaving = (nxt is None or nxt <= self._current or self._queue[nxt].group_id != self._current_group_id)

        if leaving:
            self._group_pass += 1
            g = self._eff_group_repeat()
            if g == 0 or self._group_pass < g:
                first = self._first_in_group(self._current_group_id)
                if first is not None and self.model.is_playable(first):
                    self.repeatChanged.emit()
                    self.play(first)
                    return
            self._group_pass = 0

        if nxt is None:
            self.toast.emit("End of playlist")
            return
        self.play(nxt)

    def _on_position(self, pos):
        if pos != self._position:
            self._position = int(pos)
            self.positionChanged.emit()
        if not self._loop_running(): return
        if self._loop_guard:
            if pos < self._loop_b: self._loop_guard = False
            return
        if pos >= self._loop_b:
            self._loop_hit()

    def _on_duration(self, dur):
        self._duration = int(dur)
        self.durationChanged.emit()

    def _on_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        if playing != self._playing:
            self._playing = playing
            self.playingChanged.emit()

    def _on_player_error(self, error, message=""):
        log.error("Player error: %s %s", error, message)
        self.toast.emit(f"Playback error: {message or error.name}")

# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

def load_quran_font() -> str:
    family = "Arial"
    if os.path.exists(FONT_FILE):
        font_id = QFontDatabase.addApplicationFont(FONT_FILE)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families: family = families[0]
    log.info("Using Arabic font: %s", family)
    return family

def load_bangla_font() -> str:
    if os.path.exists(BANGLA_FONT_FILE):
        font_id = QFontDatabase.addApplicationFont(BANGLA_FONT_FILE)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families: return families[0]
    return "Noto Sans Bengali"

def main():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("ruqya-quran")
    app.setApplicationDisplayName("Ruqya Quran")
    app.setOrganizationName("ruqya-quran")
    app.setDesktopFileName("ruqya-quran")

    font_family = load_quran_font()
    bangla_font = load_bangla_font()

    model = PlaylistModel(parent=app)
    controller = PlayerController(model, font_family, parent=app)
    controller._bangla_font_family = bangla_font

    engine = QQmlApplicationEngine(parent=app)
    _GLOBAL_REFS.update(app=app, model=model, controller=controller, engine=engine)

    ctx = engine.rootContext()
    ctx.setContextProperty("player", controller)
    ctx.setContextProperty("playlistModel", model)

    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    if not engine.rootObjects():
        log.error("QML failed to load")
        sys.exit(1)

    app.aboutToQuit.connect(controller.shutdown)
    controller.openInitial(sys.argv[1:])
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
