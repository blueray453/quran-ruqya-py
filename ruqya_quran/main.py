#!/usr/bin/env python3
"""
ruqya_quran.main — Quranic Ruqya player.

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
from dataclasses import dataclass
from typing import Optional
from importlib.resources import files as _pkg_files

import requests

from PySide6.QtCore import Qt, QUrl, QThread, QTimer, Signal, QSize
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QScrollArea,
)

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

    if not CONFIG_PATH.exists():
        try:
            src = _pkg_files(__package__).joinpath(TEMPLATE_CONFIG_NAME)
            with src.open("rb") as fsrc, open(CONFIG_PATH, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
            log.info("Created default config at %s", CONFIG_PATH)
        except OSError as e:
            log.warning("Could not create %s: %s", CONFIG_PATH, e)

    if not CUSTOM_PLAYLIST_PATH.exists():
        try:
            src = _pkg_files(__package__).joinpath(TEMPLATE_PLAYLIST_NAME)
            with src.open("rb") as fsrc, open(CUSTOM_PLAYLIST_PATH, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
            log.info("Created default custom playlist at %s", CUSTOM_PLAYLIST_PATH)
        except OSError as e:
            log.warning("Could not create %s: %s", CUSTOM_PLAYLIST_PATH, e)

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
    kind: str
    surah: int
    ayah: int
    description: str = ""
    group_desc: str = ""
    repeat_index: int = 1
    repeat_total: int = 1

@dataclass
class LoadedEntry:
    kind: str
    surah: int
    ayah: int
    description: str
    audio_file: str
    data: dict
    surah_data: dict
    translation: str = ""
    repeat_index: int = 1
    repeat_total: int = 1
    error: Optional[str] = None

def build_queue():
    queue = []
    for raw_entry in PLAYLIST:
        surah, start_ayah, end_ayah, description, repeat_count = normalize_playlist_entry(raw_entry)
        for rep in range(1, repeat_count + 1):
            if needs_bismillah(surah):
                queue.append(
                    QueueItem(
                        kind="bismillah",
                        surah=BISMILLAH_SURAH,
                        ayah=BISMILLAH_AYAH,
                        group_desc=description,
                        repeat_index=rep,
                        repeat_total=repeat_count,
                    ))
            for ayah in range(start_ayah, end_ayah + 1):
                queue.append(
                    QueueItem(
                        kind="ayah",
                        surah=surah,
                        ayah=ayah,
                        description=description,
                        repeat_index=rep,
                        repeat_total=repeat_count,
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
        log.info("Using cached surah %s metadata (%s)", surah, edition)
        return cached

    log.info("Downloading surah %s metadata (%s)...", surah, edition)
    url = f"https://api.alquran.cloud/v1/surah/{surah}/{edition}"
    resp = request_with_retry(url)
    data = resp.json()["data"]
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
    """Load user's custom_playlist.json from ~/.config/ruqya-quran/.
    Relative paths resolve against the JSON's own directory."""
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
        body = item.get("body", "")
        translation = item.get("translation", "")
        exists = os.path.isfile(path)

        entries.append(
            LoadedEntry(
                kind="custom",
                surah=0,
                ayah=0,
                description=title,
                audio_file=path,
                data={"text": body},
                surah_data={},
                translation=translation,
                error=None if exists else f"File not found: {path}",
            ))
        if not exists:
            log.warning("Custom playlist file missing: %s", path)

    return entries

# ------------------------------------------------------------
# Background loader
# ------------------------------------------------------------

class PlaylistLoader(QThread):
    progress = Signal(int, int, int, int)
    items_loaded = Signal(list)
    finished_loading = Signal(int, int, int)

    def run(self):
        queue = build_queue()
        total = len(queue)
        loaded = cached_count = downloaded_count = 0
        surah_data_cache = {}
        ayah_lookup_cache = {}
        translation_data_cache = {}
        translation_lookup_cache = {}
        batch = []
        BATCH_SIZE = 10

        for index, item in enumerate(queue):
            try:
                if item.surah not in surah_data_cache:
                    surah_data_cache[item.surah] = get_surah_data(item.surah)
                    ayah_lookup_cache[item.surah] = build_ayah_lookup(surah_data_cache[item.surah])
                surah_data = surah_data_cache[item.surah]
                ayah_data = ayah_lookup_cache[item.surah].get(item.ayah)
                if ayah_data is None:
                    raise ValueError(f"Ayah {item.ayah} not found in surah {item.surah}")

                translation_text = ""
                if TRANSLATION_EDITION:
                    try:
                        if item.surah not in translation_data_cache:
                            translation_data_cache[item.surah] = get_surah_data(item.surah, TRANSLATION_EDITION)
                            translation_lookup_cache[item.surah] = build_ayah_lookup(
                                translation_data_cache[item.surah])
                        translation_ayah = translation_lookup_cache[item.surah].get(item.ayah)
                        if translation_ayah is not None:
                            translation_text = translation_ayah.get("text", "")
                    except Exception as e:
                        log.warning("Failed to load translation for %s:%s - %s", item.surah, item.ayah, e)

                audio_url = ayah_data.get(
                    "audio",
                    f"https://cdn.alquran.cloud/media/audio/ayah/{RECITER}/"
                    f"{item.surah}_{item.ayah}.mp3",
                )
                audio_file, was_cached = ensure_audio_cached(item.surah, item.ayah, audio_url)
                if was_cached:
                    cached_count += 1
                else:
                    downloaded_count += 1

                entry = LoadedEntry(
                    kind=item.kind,
                    surah=item.surah,
                    ayah=item.ayah,
                    description=item.description or item.group_desc,
                    audio_file=audio_file,
                    data=ayah_data,
                    surah_data=surah_data,
                    translation=translation_text,
                    repeat_index=item.repeat_index,
                    repeat_total=item.repeat_total,
                )
                log.info("Loaded: %s (%s)", entry.description, "cached" if was_cached else "downloaded")

            except Exception as e:
                log.error("Failed to load %s:%s - %s", item.surah, item.ayah, e)
                entry = LoadedEntry(
                    kind=item.kind,
                    surah=item.surah,
                    ayah=item.ayah,
                    description=item.description or item.group_desc,
                    audio_file="",
                    data={},
                    surah_data={},
                    translation="",
                    repeat_index=item.repeat_index,
                    repeat_total=item.repeat_total,
                    error=str(e),
                )

            loaded += 1
            batch.append((index, entry))

            if len(batch) >= BATCH_SIZE or loaded == total:
                self.items_loaded.emit(batch)
                batch = []

            self.progress.emit(loaded, total, cached_count, downloaded_count)

        self.finished_loading.emit(loaded, cached_count, downloaded_count)

# ------------------------------------------------------------
# Qt helpers
# ------------------------------------------------------------

def load_quran_font():
    font_family = "Arial"
    if os.path.exists(FONT_FILE):
        font_id = QFontDatabase.addApplicationFont(FONT_FILE)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                font_family = families[0]
    log.info("Using font: %s", font_family)
    return font_family

class WrapLabel(QLabel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWordWrap(True)

    def heightForWidth(self, width):
        if width <= 0:
            return super().heightForWidth(width)
        margins = self.contentsMargins()
        usable = max(1, width - margins.left() - margins.right())
        fm = self.fontMetrics()
        rect = fm.boundingRect(0, 0, usable, 0, Qt.TextWordWrap, self.text())
        return rect.height() + margins.top() + margins.bottom()

    def hasHeightForWidth(self):
        return True

    def sizeHint(self):
        width = self.width() if self.width() > 0 else 400
        return QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self):
        return self.sizeHint()

# ------------------------------------------------------------
# Main window
# ------------------------------------------------------------

class QuranPlayer(QWidget):

    def __init__(self, font_family):
        super().__init__()

        self.font_family = font_family
        self.current_index = -1
        self.playlist_data = []
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(1.0)
        self.player.setAudioOutput(self.audio_output)

        self.loader = None

        self.setup_ui()

        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.errorOccurred.connect(self.on_player_error)
        self.playlist_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.start_loading()

    def setup_ui(self):
        self.setWindowTitle("Ruqya Quran")
        self.resize(1400, 800)

        main_layout = QHBoxLayout(self)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        playlist_label = QLabel(" Playlist")
        playlist_label.setFont(QFont("Arial", 14, QFont.Bold))
        left_layout.addWidget(playlist_label)

        self.playlist_widget = QListWidget()
        self.playlist_widget.setFont(QFont("Arial", 12))
        left_layout.addWidget(self.playlist_widget)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Ready")
        left_layout.addWidget(self.progress_label)

        main_layout.addWidget(left_panel, stretch=1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.title_label = QLabel("Select a verse from the playlist")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Arial", 16))
        right_layout.addWidget(self.title_label)

        text_scroll = QScrollArea()
        text_scroll.setWidgetResizable(True)
        text_scroll.setFrameShape(QScrollArea.NoFrame)
        text_scroll.setStyleSheet("background: transparent;")

        text_container = QWidget()
        text_container.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_container)

        self.ayah_label = WrapLabel("")
        self.ayah_label.setAlignment(Qt.AlignCenter)
        self.ayah_label.setLayoutDirection(Qt.RightToLeft)
        self.ayah_label.setFont(QFont(self.font_family, 30))
        text_layout.addWidget(self.ayah_label)

        self.translation_label = WrapLabel("")
        self.translation_label.setAlignment(Qt.AlignCenter)
        self.translation_label.setLayoutDirection(Qt.LeftToRight)
        self.translation_label.setFont(QFont("Arial", 20))
        self.translation_label.setStyleSheet("color: white;")
        text_layout.addWidget(self.translation_label)

        text_scroll.setWidget(text_container)
        right_layout.addWidget(text_scroll, stretch=1)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.pause_btn = QPushButton("⏸ Pause")
        self.stop_btn = QPushButton("■ Stop")
        self.prev_btn = QPushButton("⏮ Previous")
        self.next_btn = QPushButton("Next ⏭")

        button_layout.addWidget(self.prev_btn)
        button_layout.addWidget(self.play_btn)
        button_layout.addWidget(self.pause_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.next_btn)
        right_layout.addLayout(button_layout)

        nav_layout = QHBoxLayout()
        self.auto_play_check = QPushButton("🔁 Auto-play: OFF")
        self.auto_play_check.setCheckable(True)
        self.auto_play_check.setChecked(True)
        nav_layout.addWidget(self.auto_play_check)

        self.translation_toggle = QPushButton("🌐 Translation: ON" if TRANSLATION_EDITION else "🌐 Translation: OFF")
        self.translation_toggle.setCheckable(True)
        self.translation_toggle.setChecked(bool(TRANSLATION_EDITION))
        self.translation_toggle.setEnabled(bool(TRANSLATION_EDITION))
        nav_layout.addWidget(self.translation_toggle)
        right_layout.addLayout(nav_layout)

        main_layout.addWidget(right_panel, stretch=2)

        self.play_btn.clicked.connect(self.play_current)
        self.pause_btn.clicked.connect(self.player.pause)
        self.stop_btn.clicked.connect(self.stop_playback)
        self.prev_btn.clicked.connect(self.play_previous)
        self.next_btn.clicked.connect(self.play_next)
        self.auto_play_check.toggled.connect(self.toggle_auto_play)
        self.translation_toggle.toggled.connect(self.toggle_translation)

    # ---------------- Loading ----------------

    def start_loading(self):
        log.info("=" * 60)
        log.info("Loading playlist (threaded, cache dir: %s)...", CACHE_DIR)
        log.info("=" * 60)

        self.playlist_widget.clear()
        self.playlist_data = []
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.loader = PlaylistLoader()
        self.loader.progress.connect(self.on_load_progress)
        self.loader.items_loaded.connect(self.on_items_loaded)
        self.loader.finished_loading.connect(self.on_load_finished)
        self.loader.start()

    def on_load_progress(self, loaded, total, cached, downloaded):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(loaded)
        self.progress_label.setText(f"Loading {loaded}/{total}... "
                                    f"(cached: {cached}, downloaded: {downloaded})")

    @staticmethod
    def _repeat_suffix(entry):
        if entry.repeat_total and entry.repeat_total > 1:
            return f" (Repeat {entry.repeat_index}/{entry.repeat_total})"
        return ""

    def on_items_loaded(self, batch):
        max_index = max(idx for idx, _ in batch)
        while len(self.playlist_data) <= max_index:
            self.playlist_data.append(None)
            self.playlist_widget.addItem("Loading…")

        for index, entry in batch:
            self.playlist_data[index] = entry
            repeat_suffix = self._repeat_suffix(entry)

            if entry.error:
                item_text = f"❌ {entry.description} (Error)"
            elif entry.kind == "bismillah":
                item_text = f".....{repeat_suffix}"
            else:
                surah_name = entry.surah_data.get("englishName", "")
                item_text = f"{entry.description} - {surah_name} {entry.ayah}{repeat_suffix}"

            self.playlist_widget.item(index).setText(item_text)

        if self.current_index == -1:
            first = self._first_valid_index()
            if first is not None:
                self.playlist_widget.setCurrentRow(first)
                self.show_ayah(first)

    def on_load_finished(self, loaded, cached, downloaded):
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"✓ Loaded {loaded} items (cached: {cached}, downloaded: {downloaded})")
        log.info("=" * 60)
        log.info("Loaded %s items total (cached: %s, downloaded: %s)", loaded, cached, downloaded)
        log.info("=" * 60)

        self.append_custom_entries()

    def append_custom_entries(self):
        custom_entries = load_custom_entries()
        if not custom_entries:
            return

        self._add_separator(CUSTOM_PLAYLIST_SEPARATOR_LABEL)

        for entry in custom_entries:
            self.playlist_data.append(entry)
            if entry.error:
                item_text = f"❌ {entry.description} (Error)"
            else:
                item_text = f"🎵 {entry.description}"
            self.playlist_widget.addItem(item_text)

        log.info("Appended %s custom entries to playlist", len(custom_entries))

    def _add_separator(self, label):
        separator_entry = LoadedEntry(
            kind="separator",
            surah=0,
            ayah=0,
            description=label,
            audio_file="",
            data={},
            surah_data={},
        )
        self.playlist_data.append(separator_entry)

        item = QListWidgetItem(f"───── {label} ─────")
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
        font = item.font()
        font.setItalic(True)
        item.setFont(font)
        self.playlist_widget.addItem(item)

    # ---------------- Playability ----------------

    def _is_playable(self, entry):
        return entry is not None and not entry.error and entry.kind != "separator"

    # ---------------- Display ----------------

    def show_ayah(self, index):
        if not (0 <= index < len(self.playlist_data)):
            return
        entry = self.playlist_data[index]
        if not self._is_playable(entry):
            self.title_label.setText("Error: Failed to load this item")
            self.ayah_label.setText("")
            self.translation_label.setText("")
            return

        repeat_suffix = self._repeat_suffix(entry)
        translation_text = entry.translation if self.translation_toggle.isChecked() else ""

        if entry.kind == "bismillah":
            self.title_label.setText(f"Bismillah\n{entry.description}{repeat_suffix}")
            self.ayah_label.setText(entry.data.get("text", ""))
            self.status_label.setText(f"Bismillah — {entry.description}{repeat_suffix}")
        elif entry.kind == "custom":
            self.title_label.setText(entry.description)
            self.ayah_label.setText(entry.data.get("text", ""))
            self.status_label.setText(f"Loaded: {entry.description}")
        else:
            surah_data = entry.surah_data
            title_text = (f"{surah_data.get('englishName', 'Unknown')} "
                          f"({surah_data.get('name', '')})\n"
                          f"Ayah {entry.ayah}{repeat_suffix}")
            self.title_label.setText(title_text)
            self.ayah_label.setText(entry.data.get("text", ""))
            self.status_label.setText(f"Loaded: {entry.description}{repeat_suffix}")

        self.translation_label.setText(translation_text)
        self.select_row_no_scroll(index)

    def select_row_no_scroll(self, index):
        self.playlist_widget.setAutoScroll(False)
        self.playlist_widget.setCurrentRow(index)
        self.playlist_widget.setAutoScroll(True)

    # ---------------- Playback ----------------

    def play_current(self):
        if self.current_index < 0 or self.current_index >= len(self.playlist_data):
            first = self._first_valid_index()
            if first is not None:
                self.play_selected(first)
            else:
                self.status_label.setText("No valid item to play")
        else:
            self.play_selected(self.current_index)

    def on_item_double_clicked(self, item):
        self.play_selected(self.playlist_widget.row(item))

    def play_selected(self, index):
        if not (0 <= index < len(self.playlist_data)):
            return
        entry = self.playlist_data[index]
        if not self._is_playable(entry):
            self.status_label.setText("Error: This item could not be loaded")
            return

        self.current_index = index
        if not os.path.exists(entry.audio_file):
            self.status_label.setText(f"Error: Audio file not found: {entry.audio_file}")
            return

        log.info("Playing: %s - %s", entry.description, entry.audio_file)
        self.player.setSource(QUrl.fromLocalFile(entry.audio_file))
        self.show_ayah(index)
        self.player.play()
        label = "Bismillah" if entry.kind == "bismillah" else entry.description
        self.status_label.setText(f"▶ Playing: {label}{self._repeat_suffix(entry)}")

    def _first_valid_index(self):
        for i, entry in enumerate(self.playlist_data):
            if self._is_playable(entry):
                return i
        return None

    def _next_valid_index(self, from_index):
        for i in range(from_index + 1, len(self.playlist_data)):
            if self._is_playable(self.playlist_data[i]):
                return i
        return None

    def _prev_valid_index(self, from_index):
        for i in range(from_index - 1, -1, -1):
            if self._is_playable(self.playlist_data[i]):
                return i
        return None

    def play_next(self):
        if self.current_index < 0:
            first = self._first_valid_index()
            if first is not None:
                self.play_selected(first)
            return

        nxt = self._next_valid_index(self.current_index)
        if nxt is not None:
            self.play_selected(nxt)
            return

        if self.auto_play_check.isChecked():
            first = self._first_valid_index()
            if first is not None:
                self.play_selected(first)
                return

        self.status_label.setText("End of playlist")

    def play_previous(self):
        if self.current_index < 0:
            first = self._first_valid_index()
            if first is not None:
                self.play_selected(first)
            return

        prev = self._prev_valid_index(self.current_index)
        if prev is not None:
            self.play_selected(prev)
        else:
            self.status_label.setText("Beginning of playlist")

    def stop_playback(self):
        self.player.stop()
        self.status_label.setText("Stopped")

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.status_label.setText("Finished")
            if self.auto_play_check.isChecked():
                QTimer.singleShot(0, self.play_next)
        elif status == QMediaPlayer.MediaStatus.LoadedMedia:
            self.status_label.setText("Loaded, ready to play")
        elif status == QMediaPlayer.MediaStatus.BufferingMedia:
            self.status_label.setText("Buffering...")

    def on_player_error(self, error):
        error_messages = {
            QMediaPlayer.Error.NoError: "No error",
            QMediaPlayer.Error.ResourceError: "Resource error",
            QMediaPlayer.Error.FormatError: "Format error",
            QMediaPlayer.Error.NetworkError: "Network error",
            QMediaPlayer.Error.AccessDeniedError: "Access denied",
            QMediaPlayer.Error.ServiceMissingError: "Service missing",
        }
        self.status_label.setText(f"Player Error: {error_messages.get(error, str(error))}")
        log.error("Player error: %s", error)

    def toggle_auto_play(self, checked):
        self.auto_play_check.setText(f"🔁 Auto-play: {'ON' if checked else 'OFF'}")

    def toggle_translation(self, checked):
        self.translation_toggle.setText(f"🌐 Translation: {'ON' if checked else 'OFF'}")
        if self.current_index >= 0:
            self.show_ayah(self.current_index)

    def closeEvent(self, event):
        if self.loader is not None and self.loader.isRunning():
            self.loader.quit()
            self.loader.wait(2000)
        super().closeEvent(event)

# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName("ruqya-quran")
    font_family = load_quran_font()
    window = QuranPlayer(font_family)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
