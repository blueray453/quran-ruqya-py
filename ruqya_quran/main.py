#!/usr/bin/env python3
"""
ruqya_quran.main — Quranic Ruqya player (Qt Quick UI).

User files (created on first run by copying packaged templates):
  ~/.config/ruqya-quran/config.json
  ~/.config/ruqya-quran/custom_playlist.json

Cache (regenerated as needed):
  ~/.cache/ruqya-quran/metadata/
  ~/.cache/ruqya-quran/audio/

Run:  ruqya-quran
"""

import os
import sys
import json
import time
import shutil
import logging
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
)
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("quran_player")

# ------------------------------------------------------------
# XDG paths
# ------------------------------------------------------------

def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "ruqya-quran"

def _cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "ruqya-quran"

CONFIG_DIR = _config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"
CUSTOM_PLAYLIST_PATH = CONFIG_DIR / "custom_playlist.json"

CACHE_DIR = _cache_dir()
METADATA_CACHE_DIR = CACHE_DIR / "metadata"
AUDIO_CACHE_DIR = CACHE_DIR / "audio"

TEMPLATE_CONFIG_NAME = "config.json"
TEMPLATE_PLAYLIST_NAME = "custom_playlist.json"

def _ensure_user_files() -> None:
    """On first run, copy the packaged templates into ~/.config/ruqya-quran/."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    for target, name, label in (
        (CONFIG_PATH, TEMPLATE_CONFIG_NAME, "config"),
        (CUSTOM_PLAYLIST_PATH, TEMPLATE_PLAYLIST_NAME, "custom playlist"),
    ):
        if target.exists():
            continue
        try:
            src = _pkg_files(__package__).joinpath(name)
            with src.open("rb") as fsrc, open(target, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
            log.info("Created default %s at %s", label, target)
        except OSError as e:
            log.warning("Could not create %s: %s", target, e)

def _load_config() -> dict:
    _ensure_user_files()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Config unreadable (%s); using packaged defaults", e)
        src = _pkg_files(__package__).joinpath(TEMPLATE_CONFIG_NAME)
        return json.loads(src.read_text(encoding="utf-8"))

_CFG = _load_config()

# ------------------------------------------------------------
# Configurable values (all overridable in config.json)
# ------------------------------------------------------------

RECITER = _CFG.get("reciter", "ar.abdurrahmaansudais")
TRANSLATION_EDITION = _CFG.get("translation_edition", "en.sahih")
FONT_FILE = os.path.expanduser(_CFG.get("font_file", "/usr/share/fonts/opentype/fonts-hosny-amiri/AmiriQuran.ttf"))
CUSTOM_PLAYLIST_SEPARATOR_LABEL = _CFG.get("custom_playlist_separator_label", "Duas")
REQUEST_TIMEOUT = float(_CFG.get("request_timeout", 10))
MAX_RETRIES = int(_CFG.get("max_retries", 2))
RETRY_BACKOFF_BASE = float(_CFG.get("retry_backoff_base", 0.5))

# ------------------------------------------------------------
# Fixed constants
# ------------------------------------------------------------

BISMILLAH_SURAH = 1
BISMILLAH_AYAH = 1

# ------------------------------------------------------------
# Playlist definition
# ------------------------------------------------------------
PLAYLIST = [
    (1, 1, 7, "Surah Fatiha (Full)"),
    (2, 1, 5, "Surah Al Baqarah 1-5"),
    (2, 102, 103, "Surah Al Baqarah 102"),
    (2, 163, 164, "Surah Al Baqarah 163"),
    (2, 255, 257, "Ayatul Kursi & following"),
    (2, 285, 286, "Surah Al Baqarah 285"),
    (3, 18, 19, "Surah Al Imran 18-19"),
    (3, 26, 27, "Surah Al Imran 26-27"),
    (3, 160, 160, "Surah Al Imran 160"),
    (4, 76, 76, "Surah Al Nisaa 76"),
    (5, 118, 118, "Surah Al Maaidah 118"),
    (6, 17, 18, "Surah Al Anaam 17-18"),
    (7, 23, 23, "Surah Al Araaf 23"),
    (7, 115, 122, "Surah Al Araaf 115-122"),
    (7, 179, 179, "Surah Al Araaf 179"),
    (9, 51, 51, "Surah Al Tawbah 51"),
    (10, 76, 82, "Surah Al Yunus 76-82"),
    (10, 107, 107, "Surah Al Yunus 107"),
    (13, 28, 29, "Surah Raad 28-29"),
    (17, 32, 32, "Surah Al Isra 32"),
    (17, 81, 82, "Surah Al Isra 81-82"),
    (17, 97, 97, "Surah Al Isra 97"),
    (20, 25, 28, "Surah Al Taha 25-28"),
    (20, 65, 76, "Surah Al Taha 65-76"),
    (21, 87, 87, "Surah Al Anbiya 87"),
    (23, 115, 118, "Surah Al Muminun 115-118"),
    (28, 24, 24, "Surah Al Qasas 24"),
    (31, 27, 27, "Surah Al Luqman 27"),
    (32, 13, 14, "Surah Al Sajdah 13-14"),
    (35, 2, 2, "Surah Al Fatir 2"),
    (35, 36, 37, "Surah Al Fatir 36-37"),
    (36, 1, 10, "Surah Al Yaseen 1-10"),
    (37, 1, 10, "Surah Al Saffat 1-10"),
    (40, 59, 60, "Surah Al Ghafir 59-60"),
    (54, 10, 10, "Surah Al Qamar 10"),
    (55, 33, 36, "Surah Al Rahman 33-36"),
    (58, 19, 21, "Surah Al Mujadila 19-21"),
    (59, 18, 24, "Surah Al Hashr 18-24"),
    (72, 1, 28, "Surah Al Jinn (Full)"),
    (85, 1, 22, "Surah Al Burooj (Full)"),
    (99, 1, 8, "Surah Al Zalzalah (Full)"),
    (109, 1, 6, "Surah Al-Kafirun (Full)"),
    (112, 1, 4, "Surah Ikhlas (Full)"),
    (113, 1, 5, "Surah Falaq (Full)"),
    (114, 1, 6, "Surah An-Nas (Full)"),
]

def needs_bismillah(surah: int) -> bool:
    return surah != 1

def normalize_playlist_entry(entry):
    if len(entry) == 5:
        surah, start_ayah, end_ayah, description, repeat_count = entry
    else:
        surah, start_ayah, end_ayah, description = entry
        repeat_count = 1
    repeat_count = max(1, int(repeat_count))
    return surah, start_ayah, end_ayah, description, repeat_count

# ------------------------------------------------------------
# Data models
# ------------------------------------------------------------

@dataclass
class QueueItem:
    surah: int
    ayah: int
    description: str
    repeat_index: int = 1
    repeat_total: int = 1
    lead_bismillah: bool = False  # play the Bismillah before this ayah

@dataclass
class LoadedEntry:
    kind: str  # "ayah" | "custom" | "bismillah"
    surah: int
    ayah: int
    description: str
    audio_file: str = ""
    data: dict = field(default_factory=dict)
    surah_data: dict = field(default_factory=dict)
    translation: str = ""
    repeat_index: int = 1
    repeat_total: int = 1
    lead_bismillah: bool = False
    section: str = ""
    loaded: bool = False
    error: Optional[str] = None

def repeat_suffix(entry: LoadedEntry) -> str:
    if entry.repeat_total and entry.repeat_total > 1:
        return f" (Repeat {entry.repeat_index}/{entry.repeat_total})"
    return ""

def placeholder(item: QueueItem) -> LoadedEntry:
    e = LoadedEntry(
        kind="ayah",
        surah=item.surah,
        ayah=item.ayah,
        description=item.description,
        repeat_index=item.repeat_index,
        repeat_total=item.repeat_total,
        lead_bismillah=item.lead_bismillah,
    )
    e.section = f"{item.description}{repeat_suffix(e)}"
    return e

def build_queue():
    """One queue item per ayah. The Bismillah is a flag, not a separate row."""
    queue = []
    for raw_entry in PLAYLIST:
        surah, start_ayah, end_ayah, description, repeat_count = normalize_playlist_entry(raw_entry)
        for rep in range(1, repeat_count + 1):
            for ayah in range(start_ayah, end_ayah + 1):
                queue.append(
                    QueueItem(
                        surah=surah,
                        ayah=ayah,
                        description=description,
                        repeat_index=rep,
                        repeat_total=repeat_count,
                        lead_bismillah=needs_bismillah(surah) and ayah == start_ayah,
                    ))
    return queue

# ------------------------------------------------------------
# Caching + networking
# ------------------------------------------------------------

def ensure_dirs():
    METADATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_audio_cache_path(surah, ayah):
    return str(AUDIO_CACHE_DIR / f"{surah}_{ayah}.mp3")

def get_metadata_cache_path(surah, edition=RECITER):
    return str(METADATA_CACHE_DIR / f"surah_{surah}_{edition}.json")

def request_with_retry(url):
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE * (2**attempt))
    raise last_exc

def get_cached_surah_metadata(surah, edition=RECITER):
    path = get_metadata_cache_path(surah, edition)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Corrupt metadata cache for surah %s (%s), refetching: %s", surah, edition, e)
        return None

def save_cached_surah_metadata(surah, data, edition=RECITER):
    ensure_dirs()
    with open(get_metadata_cache_path(surah, edition), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_surah_data(surah, edition=RECITER):
    cached = get_cached_surah_metadata(surah, edition)
    if cached:
        return cached
    log.info("Downloading surah %s metadata (%s)...", surah, edition)
    url = f"https://api.alquran.cloud/v1/surah/{surah}/{edition}"
    data = request_with_retry(url).json()["data"]
    save_cached_surah_metadata(surah, data, edition)
    return data

def ensure_audio_cached(surah, ayah, audio_url):
    audio_file = get_audio_cache_path(surah, ayah)
    if os.path.exists(audio_file):
        return audio_file, True
    ensure_dirs()
    log.info("Downloading audio for %s:%s...", surah, ayah)
    resp = request_with_retry(audio_url)
    with open(audio_file, "wb") as f:
        f.write(resp.content)
    return audio_file, False

def build_ayah_lookup(surah_data):
    return {a["numberInSurah"]: a for a in surah_data["ayahs"]}

def load_custom_entries():
    """Load user's custom_playlist.json. Relative paths resolve against its directory."""
    if not CUSTOM_PLAYLIST_PATH.exists():
        return []
    try:
        with open(CUSTOM_PLAYLIST_PATH, "r", encoding="utf-8") as f:
            items = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Corrupt custom playlist json, skipping: %s", e)
        return []

    playlist_dir = CUSTOM_PLAYLIST_PATH.parent
    entries = []
    for item in items:
        raw_path = item.get("path", "")
        path = raw_path if os.path.isabs(raw_path) else str(playlist_dir / raw_path)
        title = item.get("title") or os.path.basename(path)
        exists = os.path.isfile(path)
        entries.append(
            LoadedEntry(
                kind="custom",
                surah=0,
                ayah=0,
                description=title,
                audio_file=path,
                data={"text": item.get("body", "")},
                translation=item.get("translation", ""),
                section=CUSTOM_PLAYLIST_SEPARATOR_LABEL,
                loaded=True,
                error=None if exists else f"File not found: {path}",
            ))
        if not exists:
            log.warning("Custom playlist file missing: %s", path)
    return entries

# ------------------------------------------------------------
# Background loader
# ------------------------------------------------------------

class _Resolver:
    """Per-run caches so each surah's metadata is parsed once."""

    def __init__(self):
        self.arabic, self.arabic_lookup = {}, {}
        self.trans, self.trans_lookup = {}, {}
        self.trans_failed = set()

    def load(self, surah, ayah):
        if surah not in self.arabic:
            self.arabic[surah] = get_surah_data(surah)
            self.arabic_lookup[surah] = build_ayah_lookup(self.arabic[surah])
        ayah_data = self.arabic_lookup[surah].get(ayah)
        if ayah_data is None:
            raise ValueError(f"Ayah {ayah} not found in surah {surah}")

        translation = ""
        if TRANSLATION_EDITION and surah not in self.trans_failed:
            try:
                if surah not in self.trans:
                    self.trans[surah] = get_surah_data(surah, TRANSLATION_EDITION)
                    self.trans_lookup[surah] = build_ayah_lookup(self.trans[surah])
                t = self.trans_lookup[surah].get(ayah)
                translation = t.get("text", "") if t else ""
            except Exception as e:
                self.trans_failed.add(surah)
                log.warning("Translation unavailable for surah %s: %s", surah, e)

        audio_url = ayah_data.get("audio") or (
            f"https://cdn.alquran.cloud/media/audio/ayah/{RECITER}/{surah}_{ayah}.mp3")
        audio_file, was_cached = ensure_audio_cached(surah, ayah, audio_url)
        log.info("Loaded %s:%s (%s)", surah, ayah, "cached" if was_cached else "downloaded")
        return ayah_data, self.arabic[surah], translation, audio_file

class PlaylistLoader(QThread):
    bismillah_ready = Signal(object)
    item_loaded = Signal(int, object)
    finished_loading = Signal()

    def __init__(self, jobs, parent=None):
        super().__init__(parent)
        self._jobs = jobs  # list[(row_index, QueueItem)]

    def run(self):
        r = _Resolver()

        try:
            ayah_data, surah_data, translation, audio = r.load(BISMILLAH_SURAH, BISMILLAH_AYAH)
            self.bismillah_ready.emit(
                LoadedEntry(kind="bismillah",
                            surah=BISMILLAH_SURAH,
                            ayah=BISMILLAH_AYAH,
                            description="Bismillah",
                            audio_file=audio,
                            data=ayah_data,
                            surah_data=surah_data,
                            translation=translation,
                            loaded=True))
        except Exception as e:
            log.error("Failed to load Bismillah: %s", e)

        for index, item in self._jobs:
            if self.isInterruptionRequested():
                return
            base = placeholder(item)
            try:
                ayah_data, surah_data, translation, audio = r.load(item.surah, item.ayah)
                entry = replace(base,
                                audio_file=audio,
                                data=ayah_data,
                                surah_data=surah_data,
                                translation=translation,
                                loaded=True)
            except Exception as e:
                log.error("Failed to load %s:%s - %s", item.surah, item.ayah, e)
                entry = replace(base, loaded=True, error=str(e))
            self.item_loaded.emit(index, entry)

        self.finished_loading.emit()

# ------------------------------------------------------------
# Playlist model (exposed to QML)
# ------------------------------------------------------------

class PlaylistModel(QAbstractListModel):
    LABEL, GROUP, STATUS, ERROR = 257, 258, 259, 260

    def __init__(self):
        super().__init__()
        self._entries: list[LoadedEntry] = []

    def roleNames(self):
        return {
            self.LABEL: QByteArray(b"label"),
            self.GROUP: QByteArray(b"group"),
            self.STATUS: QByteArray(b"status"),
            self.ERROR: QByteArray(b"errorText"),
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
        if role == self.LABEL:
            return self._label(e)
        if role == self.GROUP:
            return e.section
        if role == self.STATUS:
            return "error" if e.error else ("ready" if e.loaded else "loading")
        if role == self.ERROR:
            return e.error or ""
        return None

    # ---- helpers used by the controller ----
    def reset_entries(self, entries):
        self.beginResetModel()
        self._entries = entries
        self.endResetModel()

    def update(self, row, entry):
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
        """Next row that isn't a known failure (may still be loading)."""
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
# Controller (exposed to QML as `player`)
# ------------------------------------------------------------

class PlayerController(QObject):
    displayChanged = Signal()
    currentIndexChanged = Signal()
    playingChanged = Signal()
    positionChanged = Signal()
    durationChanged = Signal()
    volumeChanged = Signal()
    mutedChanged = Signal()
    repeatModeChanged = Signal()
    translationChanged = Signal()
    loadingChanged = Signal()
    toast = Signal(str)
    loopChanged = Signal()

    REPEAT_OFF, REPEAT_ONE, REPEAT_ALL = 0, 1, 2

    def __init__(self, model: PlaylistModel, font_family: str):
        super().__init__()
        self.model = model
        self._font_family = font_family

        self._queue: list[QueueItem] = []
        self._loader: Optional[PlaylistLoader] = None
        self._bismillah: Optional[LoadedEntry] = None

        self._current = -1
        self._stage = "main"  # "bismillah" | "main"
        self._pending = -1  # row waiting for its download to finish

        self._position = self._duration = 0
        self._playing = False
        self._volume = 1.0
        self._muted = False
        self._repeat = self.REPEAT_ALL
        self._loop_a = self._loop_b = -1  # ms, -1 = unset
        self._loop_total = 3  # passes; 0 = until stopped
        self._loop_done = 0
        self._loop_guard = False  # ignore stale positions right after a seek
        self._show_translation = bool(TRANSLATION_EDITION)

        self._loaded = self._total = self._failed = 0
        self._loading = False

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

    @Property(bool, constant=True)
    def hasTranslationEdition(self):
        return bool(TRANSLATION_EDITION)

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

    @Property(str, notify=displayChanged)
    def title(self):
        return self._title

    @Property(str, notify=displayChanged)
    def titleArabic(self):
        return self._title_ar

    @Property(str, notify=displayChanged)
    def subtitle(self):
        return self._subtitle

    @Property(str, notify=displayChanged)
    def arabicText(self):
        return self._arabic

    @Property(str, notify=displayChanged)
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

    @Property(float, notify=volumeChanged)
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, v):
        v = max(0.0, min(1.0, float(v)))
        if v != self._volume:
            self._volume = v
            self._apply_volume()
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

    @Property(int, notify=repeatModeChanged)
    def repeatMode(self):
        return self._repeat

    @repeatMode.setter
    def repeatMode(self, m):
        if int(m) != self._repeat:
            self._repeat = int(m)
            self.repeatModeChanged.emit()

    @Property(bool, notify=translationChanged)
    def showTranslation(self):
        return self._show_translation

    @showTranslation.setter
    def showTranslation(self, v):
        if bool(v) != self._show_translation:
            self._show_translation = bool(v)
            self.translationChanged.emit()

    def _apply_volume(self):
        # Squared curve feels closer to perceived loudness than linear.
        self._audio.setVolume(self._volume**2)

    # ---------------- Loading ----------------

    def start(self):
        self._queue = build_queue()
        entries = [placeholder(q) for q in self._queue] + load_custom_entries()
        self.model.reset_entries(entries)
        self._loaded, self._failed, self._total = 0, 0, len(self._queue)
        self._run_loader(list(enumerate(self._queue)))

    def _run_loader(self, jobs):
        self._loader = PlaylistLoader(jobs)
        self._loader.bismillah_ready.connect(self._on_bismillah)
        self._loader.item_loaded.connect(self._on_item_loaded)
        self._loader.finished_loading.connect(self._on_load_finished)
        self._loading = True
        self.loadingChanged.emit()
        self._loader.start()

    @Slot()
    def retry(self):
        if self._loading:
            return
        jobs = []
        for i, item in enumerate(self._queue):
            e = self.model.entry(i)
            if e and e.error:
                self.model.update(i, placeholder(item))
                jobs.append((i, item))
        if jobs:
            self._loaded, self._failed, self._total = 0, 0, len(jobs)
            self._run_loader(jobs)

    def _on_bismillah(self, entry):
        self._bismillah = entry

    def _on_item_loaded(self, index, entry):
        self.model.update(index, entry)
        self._loaded += 1
        if entry.error:
            self._failed += 1
        self.loadingChanged.emit()

        if self._current < 0 and self.model.is_playable(index):
            self._select(index)
        if index == self._pending:
            self._pending = -1
            self.play(index)

    def _on_load_finished(self):
        self._loading = False
        self.loadingChanged.emit()
        if self._current < 0:
            for i in range(self.model.rowCount()):
                if self.model.is_playable(i):
                    self._select(i)
                    break

    def shutdown(self):
        if self._loader is not None and self._loader.isRunning():
            self._loader.requestInterruption()
            if not self._loader.wait(2000):
                self._loader.terminate()
                self._loader.wait()

    # ---------------- Selection / display ----------------

    def _select(self, index):
        self._current = index
        self._stage = "main"
        self.currentIndexChanged.emit()
        self._refresh_display()

    def _refresh_display(self):
        e = self.model.entry(self._current)
        t = ta = sub = ar = tr = ""
        if e and e.loaded and not e.error:
            suffix = repeat_suffix(e)
            if self._stage == "bismillah" and self._bismillah:
                t = "Bismillah"
                sub = f"Before {e.description}{suffix}"
                ar = self._bismillah.data.get("text", "")
                tr = self._bismillah.translation
            elif e.kind == "custom":
                t = e.description
                sub = CUSTOM_PLAYLIST_SEPARATOR_LABEL
                ar = e.data.get("text", "")
                tr = e.translation
            else:
                t = e.surah_data.get("englishName", "")
                ta = e.surah_data.get("name", "")
                sub = f"Ayah {e.ayah}{suffix}"
                ar = e.data.get("text", "")
                tr = e.translation
        self._title, self._title_ar, self._subtitle = t, ta, sub
        self._arabic, self._translation = ar, tr
        self.displayChanged.emit()

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

    @Slot(int)
    def play(self, index):
        entry = self.model.entry(index)
        if entry is None:
            return
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

        self._stage = "main"
        path = entry.audio_file
        if entry.lead_bismillah and self._bismillah_ok():
            self._stage = "bismillah"
            path = self._bismillah.audio_file
        self._start_audio(path)

    @Slot()
    def toggle(self):
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
        if self._current < 0:
            first = self.model.first_index()
            if first is not None:
                self.play(first)
            return
        nxt = self.model.next_index(self._current)
        if nxt is None and self._repeat == self.REPEAT_ALL:
            nxt = self.model.first_index()
        if nxt is None:
            self.toast.emit("End of playlist")
        else:
            self.play(nxt)

    @Slot()
    def playPrevious(self):
        if self._current < 0:
            return
        if self._position > 3000:
            self.seek(0)
            return
        prev = self.model.prev_index(self._current)
        if prev is None:
            self.seek(0)
        else:
            self.play(prev)

    @Slot(int)
    def seek(self, ms):
        self._player.setPosition(max(0, int(ms)))

    @Slot(int)
    def seekBy(self, delta_ms):
        end = self._duration or (self._position + abs(delta_ms))
        self.seek(max(0, min(end, self._position + int(delta_ms))))

    @Slot()
    def cycleRepeat(self):
        self.repeatMode = (self._repeat + 1) % 3

    # ---------------- A-B loop (session only) ----------------

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

    def _loop_valid(self):
        return self._loop_a >= 0 and self._loop_b > self._loop_a

    def _loop_running(self):
        return self._stage == "main" and self._loop_valid()

    def _loop_hit(self):
        """Loop end reached. Jump back and return True, or finish the loop and return False."""
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
        if not self._can_mark():
            return
        self._loop_a = self._position
        if self._loop_b <= self._loop_a:
            self._loop_b = -1
        self._loop_done = 0
        self._loop_guard = False
        self.loopChanged.emit()

    @Slot()
    def markEnd(self):
        if not self._can_mark():
            return
        if self._loop_a < 0:
            self._loop_a = 0
        if self._position - self._loop_a < 300:
            self.toast.emit("The end must come after the start")
            return
        self._loop_b = self._position
        self._loop_done = 0
        self.loopChanged.emit()
        self._loop_guard = True
        self._player.setPosition(self._loop_a)  # start looping immediately
        self._player.play()

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
        if entry is None:
            return
        if self._stage == "bismillah":
            self._stage = "main"
            self._start_audio(entry.audio_file)
            return
        if self._loop_running() and self._loop_hit():
            self._player.play()
            return
        if self._repeat == self.REPEAT_ONE:
            self.play(self._current)
            return
        nxt = self.model.next_index(self._current)
        if nxt is None and self._repeat == self.REPEAT_ALL:
            nxt = self.model.first_index()
        if nxt is None:
            self.toast.emit("End of playlist")
        else:
            self.play(nxt)

    def _on_position(self, pos):
        if pos != self._position:
            self._position = int(pos)
            self.positionChanged.emit()
        if not self._loop_running():
            return
        if self._loop_guard:
            if pos < self._loop_b:  # the seek has taken effect
                self._loop_guard = False
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
            if families:
                family = families[0]
    log.info("Using font: %s", family)
    return family

def main():
    QQuickStyle.setStyle("Basic")  # fully customisable; we draw our own theme
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Ruqya Quran")
    app.setOrganizationName("ruqya-quran")  # needed for persisted UI settings
    app.setDesktopFileName("ruqya-quran")

    font_family = load_quran_font()
    model = PlaylistModel()
    controller = PlayerController(model, font_family)

    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("player", controller)
    ctx.setContextProperty("playlistModel", model)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    if not engine.rootObjects():
        sys.exit(1)

    app.aboutToQuit.connect(controller.shutdown)
    controller.start()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
