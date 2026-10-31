"""ruqya_quran.main — single-file controller.

Each playlist is self-contained: `<name>.ruqya` sits next to `<data_dir>/`
which holds audio, segments, script, translations, wbw, meta, and clips.
The data folder is generated once by tools/fetch_qul.py. No network at runtime.
"""
import json
import logging
import os
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    Qt,
    QUrl,
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

log = logging.getLogger("ruqya")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("qt.qpa.services").setLevel(logging.ERROR)

BISMILLAH_SURAH, BISMILLAH_AYAH = 1, 1

# ============================================================
# Config
# ============================================================
DEFAULTS = {
    "reciters": {
        "ar.abdurrahmaansudais": "Sudais",
        "ar.alafasy": "Mishari Rashid",
        "ar.ghamdi": "Saad al-Ghamdi",
        "ar.husary": "Mahmoud Khalil Al-Husary (Murattal)",
        "ar.husarymuallim": "Mahmoud Khalil Al-Husary (Muallim)",
    },
    "default_reciter": "ar.abdurrahmaansudais",
    "translations": {
        "en.sahih": "English (Saheeh)",
        "bn.taisirul": "বাংলা (তাইসিরুল কুরআন)",
        "bn.rawai": "বাংলা (রাওয়াই আল-বায়ান)",
    },
    "default_translation": "en.sahih",
    "font_file": "/usr/share/fonts/opentype/fonts-hosny-amiri/AmiriQuran.ttf",
    "bangla_font_file": "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
    "custom_playlist_separator_label": "Duas",
}

def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else Path.home() / ".config") / "ruqya-quran"

CONFIG_DIR = _config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"

def _load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Config unreadable (%s); using defaults", e)
    else:
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except OSError as e:
            log.warning("Cannot write config: %s", e)
    return cfg

CFG = _load_config()
RECITERS = CFG["reciters"]
DEFAULT_RECITER = CFG["default_reciter"]
TRANSLATIONS = CFG["translations"]
DEFAULT_TRANSLATION = CFG["default_translation"]
FONT_FILE = os.path.expanduser(CFG["font_file"])
BANGLA_FONT_FILE = os.path.expanduser(CFG["bangla_font_file"])
CUSTOM_PLAYLIST_SEPARATOR_LABEL = CFG["custom_playlist_separator_label"]

# ============================================================
# Data store (one per playlist)
# ============================================================
class DataStore:
    """Reads from a playlist's data folder. Populated by tools/fetch_qul.py."""

    def __init__(self, root: Path):
        self.root = root
        self.meta = self._load("meta/surahs.json", {})
        self.script = self._load("script/words.json", {})
        self.wbw_en = self._load("wbw/en.json", {})
        self.wbw_bn = self._load("wbw/bn.json", {})
        self.translations = {ed: self._load(f"translations/{ed}.json", {}) for ed in TRANSLATIONS}
        self.recitations = {}
        rec_dir = self.root / "recitations"
        if rec_dir.exists():
            for p in rec_dir.glob("*.json"):
                self.recitations[p.stem] = self._load(f"recitations/{p.name}", {})

    def _load(self, rel, default):
        f = self.root / rel
        if not f.exists():
            return default
        try:
            with open(f, encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as e:
            log.warning("cannot read %s: %s", f, e)
            return default

    def surah_meta(self, surah: int) -> dict:
        return self.meta.get(str(surah), {})

    def words(self, surah: int, ayah: int) -> list:
        out, pos = [], 1
        while True:
            e = self.script.get(f"{surah}:{ayah}:{pos}")
            if e is None:
                break
            out.append({"position": pos, "text": e.get("text", "")})
            pos += 1
        return out

    def segments(self, reciter: str, surah: int, ayah: int) -> dict:
        rec = self.recitations.get(reciter, {}).get(f"{surah}:{ayah}", {})
        return {pos: (s, e) for pos, s, e in rec.get("segments", [])}

    def duration(self, reciter: str, surah: int, ayah: int) -> int:
        rec = self.recitations.get(reciter, {}).get(f"{surah}:{ayah}", {})
        return int(rec.get("duration", 0) or 0)

    def translation(self, edition: str, surah: int, ayah: int) -> str:
        v = self.translations.get(edition, {}).get(f"{surah}:{ayah}", "")
        return v.get("t", "") if isinstance(v, dict) else (v or "")

    def wbw(self, lang: str, surah: int, ayah: int, pos: int) -> str:
        tbl = self.wbw_bn if lang == "bn" else self.wbw_en
        return tbl.get(f"{surah}:{ayah}:{pos}", "")

    def audio_path(self, reciter: str, surah: int, ayah: int) -> Path:
        return self.root / "audio" / reciter / f"{surah}_{ayah}.mp3"

    def available_reciters(self) -> list:
        return sorted(self.recitations.keys())

    def resolve_clip(self, raw: str) -> str:
        """Resolve a clip path relative to the playlist's data folder."""
        if not raw:
            return ""
        p = Path(raw).expanduser()
        if p.is_absolute():
            return str(p)
        return str((self.root / p).resolve())

# Set to a fresh DataStore when a playlist opens. None before then.
_DATA: Optional[DataStore] = None

# ============================================================
# Marks (user-level SQLite, shared across playlists)
# ============================================================
class Marks:

    def __init__(self, path=None):
        self._lock = threading.Lock()
        if path is None:
            base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
            d = base / "ruqya-quran"
            d.mkdir(parents=True, exist_ok=True)
            path = d / "marks.db"
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS marks(
                surah INT, ayah INT, word INT, text TEXT, ts REAL,
                PRIMARY KEY (surah, ayah, word));
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY, surah INT, ayah INT, word INT,
                text TEXT, ts REAL, session TEXT, action TEXT);
            CREATE INDEX IF NOT EXISTS events_word ON events(surah, ayah, word);
        """)

    def toggle(self, surah, ayah, word, text, session) -> bool:
        now = time.time()
        with self._lock, self._db:
            row = self._db.execute("SELECT text FROM marks WHERE surah=? AND ayah=? AND word=?",
                                   (surah, ayah, word)).fetchone()
            if row and row[0] != text:
                self._db.execute("DELETE FROM marks WHERE surah=? AND ayah=? AND word=?", (surah, ayah, word))
                row = None
            if row:
                self._db.execute("DELETE FROM marks WHERE surah=? AND ayah=? AND word=?", (surah, ayah, word))
                action = "unmark"
            else:
                self._db.execute("INSERT OR REPLACE INTO marks VALUES (?,?,?,?,?)", (surah, ayah, word, text, now))
                action = "mark"
            self._db.execute("INSERT INTO events(surah,ayah,word,text,ts,session,action) "
                             "VALUES (?,?,?,?,?,?,?)", (surah, ayah, word, text, now, session, action))
        return action == "mark"

    def for_ayah(self, surah, ayah) -> dict:
        with self._lock:
            counts = dict(
                self._db.execute(
                    "SELECT word, COUNT(*) FROM events WHERE surah=? AND ayah=? "
                    "AND action='mark' GROUP BY word", (surah, ayah)))
            marked = dict(self._db.execute("SELECT word, text FROM marks WHERE surah=? AND ayah=?", (surah, ayah)))
        return {
            w: {
                "marked": w in marked,
                "count": counts.get(w, 0),
                "text": marked.get(w, "")
            }
            for w in set(counts) | set(marked)
        }

# ============================================================
# Playlist
# ============================================================
@dataclass
class QueueItem:
    surah: int
    ayah: int
    description: str
    group_id: str = ""
    lead_bismillah: bool = False
    kind: str = "quran"
    custom_path: str = ""
    custom_body: str = ""
    custom_translation: str = ""
    custom_section: str = ""
    ayah_repeat: int = 1
    group_repeat: int = 1

def read_playlist_file(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        data = {"items": data}
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("not a playlist (missing 'items' list)")
    if data.get("format", "ruqya-playlist") != "ruqya-playlist":
        raise ValueError("unknown playlist format")
    return {
        "name": data.get("name") or Path(path).stem.replace("_", " ").title(),
        "items": data["items"],
        "reciter": data.get("reciter") or "",
        "translation": data.get("translation") or "",
        "data_dir": data.get("data_dir") or "",
        "offline": bool(data.get("offline", False)),
        "preload_reciters": data.get("preload_reciters") or [],
        "preload_translations": data.get("preload_translations") or [],
    }

def needs_bismillah(surah: int) -> bool:
    """QUL audio never embeds a Bismillah in the first-ayah file.
    Al-Fatiha already begins with it as ayah 1; At-Tawbah has none."""
    return surah not in (1, 9)

def _read_repeats(raw: dict) -> tuple:
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

def build_queue_from_items(items: list, store) -> list:
    queue = []
    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            continue
        if "path" in raw:
            path = store.resolve_clip(raw.get("path", ""))
            ar, gr = _read_repeats(raw)
            queue.append(
                QueueItem(surah=0,
                          ayah=0,
                          description=raw.get("title") or os.path.basename(path),
                          group_id=f"custom:{idx}",
                          kind="custom",
                          custom_path=path,
                          custom_body=raw.get("body", ""),
                          custom_translation=raw.get("translation", ""),
                          custom_section=raw.get("section") or CUSTOM_PLAYLIST_SEPARATOR_LABEL,
                          ayah_repeat=ar,
                          group_repeat=gr))
            continue
        if "surah" not in raw:
            continue
        surah = int(raw["surah"])
        f_a = int(raw.get("from", 1))
        t_a = int(raw.get("to", f_a))
        desc = raw.get("description") or f"Surah {surah}:{f_a}-{t_a}"
        ar, gr = _read_repeats(raw)
        gid = f"g{idx}:{surah}:{f_a}-{t_a}"
        for ayah in range(f_a, t_a + 1):
            queue.append(
                QueueItem(surah=surah,
                          ayah=ayah,
                          description=desc,
                          group_id=gid,
                          lead_bismillah=needs_bismillah(surah) and ayah == f_a,
                          ayah_repeat=ar,
                          group_repeat=gr))
    return queue

# ============================================================
# LoadedEntry + loader helpers
# ============================================================
@dataclass
class LoadedEntry:
    kind: str
    surah: int
    ayah: int
    description: str
    audio_file: str = ""
    arabic: str = ""
    translation: str = ""
    surah_name: str = ""
    surah_name_ar: str = ""
    group_id: str = ""
    lead_bismillah: bool = False
    section: str = ""
    loaded: bool = False
    error: Optional[str] = None
    ayah_repeat: int = 1
    group_repeat: int = 1
    duration_ms: int = 0

def _probe_ms(path: str) -> int:
    try:
        from mutagen import File
        f = File(path)
        return int(f.info.length * 1000) if f and f.info else 0
    except Exception:
        return 0

def placeholder(item: QueueItem, store: DataStore) -> LoadedEntry:
    if item.kind == "custom":
        exists = bool(item.custom_path) and os.path.isfile(item.custom_path)
        return LoadedEntry(kind="custom",
                           surah=0,
                           ayah=0,
                           description=item.description,
                           audio_file=item.custom_path,
                           arabic=item.custom_body,
                           translation=item.custom_translation,
                           group_id=item.group_id,
                           section=item.custom_section or CUSTOM_PLAYLIST_SEPARATOR_LABEL,
                           loaded=True,
                           error=None if exists else f"File not found: {item.custom_path}",
                           ayah_repeat=item.ayah_repeat,
                           group_repeat=item.group_repeat,
                           duration_ms=_probe_ms(item.custom_path) if exists else 0)
    return LoadedEntry(kind="ayah",
                       surah=item.surah,
                       ayah=item.ayah,
                       description=item.description,
                       group_id=item.group_id,
                       lead_bismillah=item.lead_bismillah,
                       ayah_repeat=item.ayah_repeat,
                       group_repeat=item.group_repeat,
                       section=item.description)

def _load_ayah(store: DataStore, reciter: str, translation_edition: str, surah: int,
               ayah: int) -> Optional[LoadedEntry]:
    meta = store.surah_meta(surah)
    words = store.words(surah, ayah)
    if not words:
        return None
    audio = store.audio_path(reciter, surah, ayah)
    base = LoadedEntry(kind="ayah",
                       surah=surah,
                       ayah=ayah,
                       description=f"{meta.get('name', surah)} · {ayah}",
                       surah_name=meta.get("name", ""),
                       surah_name_ar=meta.get("name_arabic", ""),
                       arabic=" ".join(w["text"] for w in words),
                       translation=store.translation(translation_edition, surah, ayah),
                       loaded=True,
                       duration_ms=store.duration(reciter, surah, ayah))
    if audio.exists():
        base.audio_file = str(audio)
    else:
        base.error = f"audio missing: {audio.name}"
    return base

# ============================================================
# Model
# ============================================================
class PlaylistModel(QAbstractListModel):
    LABEL, GROUP, STATUS, ERROR, AYAH_NO = 257, 258, 259, 260, 261

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []

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
    def _label(e):
        if e.kind == "custom":
            return e.description
        return f"{e.surah_name} · {e.ayah}" if e.surah_name else f"{e.surah}:{e.ayah}"

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._entries)):
            return None
        e = self._entries[index.row()]
        if role == self.LABEL: return self._label(e)
        if role == self.GROUP: return e.section
        if role == self.STATUS: return "error" if e.error else ("ready" if e.loaded else "loading")
        if role == self.ERROR: return e.error or ""
        if role == self.AYAH_NO: return e.ayah if e.kind == "ayah" else 0
        return None

    def reset_entries(self, entries):
        self.beginResetModel()
        self._entries = entries
        self.endResetModel()

    def update(self, row, entry):
        if 0 <= row < len(self._entries):
            self._entries[row] = entry
            ix = self.index(row)
            self.dataChanged.emit(ix, ix)

    def entry(self, row):
        return self._entries[row] if 0 <= row < len(self._entries) else None

    def is_playable(self, row):
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

# ============================================================
# Controller
# ============================================================
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
        self._marks = Marks()
        self._session = time.strftime("%Y-%m-%d %H:%M")

        self._playlist = {"name": "", "items": []}
        self._playlist_path = ""
        self._recent = self._load_recent()

        saved = self._settings.value("ui/reciter", DEFAULT_RECITER, type=str)
        self._reciter = saved if saved in RECITERS else DEFAULT_RECITER

        saved_t = self._settings.value("ui/translation", DEFAULT_TRANSLATION, type=str)
        self._translation_edition = saved_t if saved_t in TRANSLATIONS else DEFAULT_TRANSLATION

        try:
            v = float(self._settings.value("ui/volume", 1.0, type=float))
        except (TypeError, ValueError):
            v = 1.0
        self._volume = max(0.0, min(1.0, v))
        self._muted = False
        self._show_translation = self._settings.value("ui/showTranslation", True, type=bool)
        self._word_by_word = self._settings.value("ui/wordByWord", True, type=bool)

        self._words_with_state = []

        self._ayah_repeat = -1
        self._group_repeat = -1
        self._playlist_loop = False
        self._ayah_pass = 0
        self._group_pass = 0
        self._current_group_id = ""

        self._queue = []
        self._bismillah = None

        self._current = -1
        self._stage = "main"
        self._pending = -1
        self._resume_index = -1
        self._position = 0
        self._duration = 0
        self._playing = False

        self._loop_a = -1
        self._loop_b = -1
        self._loop_total = 3
        self._loop_done = 0
        self._loop_guard = False

        self._loaded = 0
        self._total = 0
        self._failed = 0
        self._loading = False

        self._title = ""
        self._title_ar = ""
        self._subtitle = ""
        self._arabic = ""
        self._translation = ""

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._apply_volume()
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_player_error)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._on_state)

    # ---- constant props ----
    @Property(str, constant=True)
    def fontFamily(self):
        return self._font_family

    @Property(str, constant=True)
    def banglaFontFamily(self):
        return self._bangla_font_family

    @Property(list, notify=reciterChanged)
    def reciterNames(self):
        if _DATA is None:
            return [{"id": k, "name": v} for k, v in RECITERS.items()]
        available = set(_DATA.available_reciters())
        if not available:
            return [{"id": k, "name": v} for k, v in RECITERS.items()]
        return [{"id": k, "name": v} for k, v in RECITERS.items() if k in available]

    @Property(list, constant=True)
    def translationNames(self):
        return [{"id": k, "name": v} for k, v in TRANSLATIONS.items()]

    # ---- playlists ----
    def _load_recent(self):
        try:
            raw = json.loads(self._settings.value("ui/recent", "[]", type=str))
        except (ValueError, TypeError):
            raw = []
        return [r for r in raw if isinstance(r, dict) and os.path.isfile(r.get("path", ""))][:10]

    def _remember(self, path, name):
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
    def setPlaylist(self, pid):
        if pid != self._playlist_path:
            self.openPlaylist(pid)

    @Slot(str, result=bool)
    def openPlaylist(self, location):
        global _DATA
        p = Path(QUrl(location).toLocalFile() if location.startswith("file:") else location).expanduser()
        try:
            data = read_playlist_file(p)
        except (OSError, ValueError) as e:
            self.toast.emit(f"Can't open playlist: {e}")
            return False

        data_dir = (p.parent / (data["data_dir"] or "data")).resolve()
        if not (data_dir / "VERSION").exists():
            log.warning("playlist data dir not bundled: %s "
                        "(run tools/fetch_qul.py --playlist %s)", data_dir, p)

        _DATA = DataStore(data_dir)
        available = _DATA.available_reciters()

        self._playlist = data
        self._playlist_path = str(p.resolve())
        self._bismillah = None

        if data["reciter"] in RECITERS and data["reciter"] in available:
            self._reciter = data["reciter"]
        elif self._reciter not in available and available:
            self._reciter = available[0]

        if data["translation"] in TRANSLATIONS:
            self._translation_edition = data["translation"]

        self._remember(self._playlist_path, data["name"])
        self.reciterChanged.emit()
        self.translationChanged.emit()
        self.currentPlaylistChanged.emit()
        self._restart_loader(keep_position=False)
        return True

    def openInitial(self, args):
        for a in args:
            if not a.startswith("-") and self.openPlaylist(a):
                return
        last = self._settings.value("ui/lastPlaylist", "", type=str)
        if last and os.path.isfile(last):
            self.openPlaylist(last)

    @Property(str, notify=reciterChanged)
    def currentReciter(self):
        return self._reciter

    @Property(str, notify=translationChanged)
    def currentTranslation(self):
        return self._translation_edition

    @Slot(str)
    def setReciter(self, rid):
        if rid not in RECITERS or rid == self._reciter:
            return
        if _DATA is None or rid not in _DATA.available_reciters():
            self.toast.emit(f"{RECITERS[rid]} is not bundled in this playlist's data")
            return
        self._reciter = rid
        self._settings.setValue("ui/reciter", rid)
        self.reciterChanged.emit()
        self.toast.emit(f"Reciter: {RECITERS[rid]} — reloading")
        self._restart_loader(keep_position=True)

    @Slot(str)
    def setTranslation(self, ed):
        if ed in TRANSLATIONS and ed != self._translation_edition:
            self._translation_edition = ed
            self._settings.setValue("ui/translation", ed)
            self.translationChanged.emit()
            self.toast.emit(f"Translation: {TRANSLATIONS[ed]} — reloading")
            self._restart_loader(keep_position=True)

    # ---- word-by-word ----
    @Property(bool, notify=wordByWordChanged)
    def wordByWord(self):
        return self._word_by_word

    @wordByWord.setter
    def wordByWord(self, v):
        v = bool(v)
        if v != self._word_by_word:
            self._word_by_word = v
            self._settings.setValue("ui/wordByWord", v)
            self.wordByWordChanged.emit()

    @Property(list, notify=wordsChanged)
    def words(self):
        return self._words_with_state

    # ---- core state ----
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

    @Property(bool, constant=True)
    def initializing(self):
        return False

    @Property(str, constant=True)
    def initMessage(self):
        return ""

    @Property(int, constant=True)
    def initCurrent(self):
        return 0

    @Property(int, constant=True)
    def initTotal(self):
        return 0

    # ---- volume ----
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

    # ---- A-B loop ----
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
        if self._loop_a < 0: self._loop_b = -1
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

    # ---- repeat ----
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

    def _cur_q(self):
        return self._queue[self._current] if 0 <= self._current < len(self._queue) else None

    def _eff_ayah_repeat(self):
        if self._ayah_repeat != -1: return self._ayah_repeat
        q = self._cur_q()
        return q.ayah_repeat if q else 1

    def _eff_group_repeat(self):
        if self._group_repeat != -1: return self._group_repeat
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
        f = lambda n: "∞" if n == 0 else str(n)
        self.toast.emit(f"Each ayah ×{f(self._eff_ayah_repeat())} · "
                        f"Section ×{f(self._eff_group_repeat())}")

    def _apply_volume(self):
        self._audio.setVolume(self._volume**2)

    # ---- load ----
    def _restart_loader(self, keep_position=True):
        keep_index = self._current if (keep_position and self._current >= 0) else -1
        self._player.stop()
        self._current = -1
        self._stage = "main"
        self._pending = -1
        self._resume_index = keep_index
        self._current_group_id = ""
        self._ayah_pass = self._group_pass = 0
        self._position = self._duration = 0
        self._words_with_state = []
        self.clearLoop()
        self.currentIndexChanged.emit()
        self.positionChanged.emit()
        self.durationChanged.emit()
        self.wordsChanged.emit()
        self.start()

    def start(self):
        if not self._playlist["items"] or _DATA is None:
            return
        self._queue = build_queue_from_items(self._playlist["items"], _DATA)
        if not self._queue:
            self.model.reset_entries([])
            return

        try:
            b = _load_ayah(_DATA, self._reciter, self._translation_edition, BISMILLAH_SURAH, BISMILLAH_AYAH)
            if b:
                b.kind = "bismillah"
                b.description = "Bismillah"
                self._bismillah = b
        except Exception as e:
            log.warning("Bismillah load failed: %s", e)

        entries = []
        for q in self._queue:
            base = placeholder(q, _DATA)
            if q.kind == "ayah":
                try:
                    loaded = _load_ayah(_DATA, self._reciter, self._translation_edition, q.surah, q.ayah)
                    if loaded is None:
                        base = replace(base, loaded=True, error="ayah data missing")
                    else:
                        loaded.description = base.description
                        loaded.group_id = base.group_id
                        loaded.section = base.section
                        loaded.lead_bismillah = base.lead_bismillah
                        loaded.ayah_repeat = base.ayah_repeat
                        loaded.group_repeat = base.group_repeat
                        base = loaded
                except Exception as e:
                    base = replace(base, loaded=True, error=str(e))
            entries.append(base)

        self.model.reset_entries(entries)
        self._loaded = sum(1 for e in entries if e.loaded and not e.error)
        self._failed = sum(1 for e in entries if e.error)
        self._total = len(entries)
        self.loadingChanged.emit()
        self._on_load_finished()

    @Slot()
    def retry(self):
        self._restart_loader(keep_position=self._current >= 0)

    def _on_load_finished(self):
        if (self._current < 0 and self._resume_index >= 0 and self.model.is_playable(self._resume_index)):
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
        pass

    # ---- words ----
    def _refresh_words(self):
        e = self.model.entry(self._current)
        self._words_with_state = []
        if not e or e.kind != "ayah" or self._stage != "main" or _DATA is None:
            self.wordsChanged.emit()
            return
        words = _DATA.words(e.surah, e.ayah)
        seg = _DATA.segments(self._reciter, e.surah, e.ayah)
        marks = self._marks.for_ayah(e.surah, e.ayah)
        out = []
        for w in words:
            pos = w["position"]
            ar = w["text"]
            if not any(c.isalpha() for c in ar):
                continue
            m = marks.get(pos, {})
            stale = bool(m.get("text")) and m["text"] != ar
            start, end = seg.get(pos, (-1, -1))
            out.append({
                "index": pos - 1,
                "arabic": ar,
                "english": _DATA.wbw("en", e.surah, e.ayah, pos),
                "bangla": _DATA.wbw("bn", e.surah, e.ayah, pos),
                "marked": bool(m.get("marked")) and not stale,
                "mistakes": m.get("count", 0),
                "start": start,
                "end": end,
            })
        self._words_with_state = out
        self.wordsChanged.emit()

    @Slot(int)
    def toggleMark(self, idx):
        e = self.model.entry(self._current)
        w = next((w for w in self._words_with_state if w["index"] == idx), None)
        if not e or e.kind != "ayah" or w is None: return
        on = self._marks.toggle(e.surah, e.ayah, idx + 1, w["arabic"], self._session)
        self._refresh_words()
        self.toast.emit("Marked — kept as a reminder" if on else "Mark removed")

    # ---- selection / display ----
    def _select(self, index):
        self._current = index
        self._stage = "main"
        self.currentIndexChanged.emit()
        self.repeatChanged.emit()
        self._refresh_display()
        self._refresh_words()

    def _refresh_display(self):
        e = self.model.entry(self._current)
        t = ta = sub = ar = tr = ""
        if e and e.loaded and not e.error:
            if self._stage == "bismillah" and self._bismillah:
                t = "Bismillah"
                sub = f"Before {e.description}"
                ar = self._bismillah.arabic
                tr = self._bismillah.translation
            elif e.kind == "custom":
                t = e.description
                sub = e.section or CUSTOM_PLAYLIST_SEPARATOR_LABEL
                ar = e.arabic
                tr = e.translation
            else:
                t = e.surah_name
                ta = e.surah_name_ar
                sub = f"Ayah {e.ayah}"
                ar = e.arabic
                tr = e.translation
        self._title, self._title_ar, self._subtitle = t, ta, sub
        self._arabic, self._translation = ar, tr
        self.contentReset.emit()

    # ---- playback ----
    def _bismillah_ok(self):
        b = self._bismillah
        return bool(b and not b.error and b.audio_file and os.path.exists(b.audio_file))

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

    def _enter_playback(self, index):
        item = self._queue[index] if 0 <= index < len(self._queue) else None
        if not item: return
        if item.group_id != self._current_group_id:
            self._current_group_id = item.group_id
            self._group_pass = 0
        self._ayah_pass = 0
        self.repeatChanged.emit()

    @Slot(int)
    def play(self, index):
        entry = self.model.entry(index)
        if entry is None: return
        if entry.error:
            self.toast.emit("This item couldn't be loaded")
            return
        if not entry.loaded:
            self._pending = index
            self.toast.emit("Loading…")
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
        self._refresh_words()

    @Slot()
    def toggle(self):
        if self._playing:
            self._player.pause()
        elif (self._current >= 0 and self._player.source().isValid()
              and self._player.mediaStatus() != QMediaPlayer.MediaStatus.EndOfMedia):
            self._player.play()
        else:
            target = self._current if self._current >= 0 else self.model.first_index()
            if target is not None: self.play(target)

    @Slot()
    def playNext(self):
        if self._current < 0:
            first = self.model.first_index()
            if first is not None: self.play(first)
            return
        nxt = self.model.next_index(self._current)
        if nxt is None and self._playlist_loop:
            nxt = self.model.first_index()
            self._current_group_id = ""
        if nxt is None: self.toast.emit("End of playlist")
        else: self.play(nxt)

    @Slot()
    def playPrevious(self):
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

    # ---- player signals ----
    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            QTimer.singleShot(0, self._on_finished)

    def _on_finished(self):
        entry = self.model.entry(self._current)
        if entry is None: return
        if self._stage == "bismillah":
            self._stage = "main"
            self._start_audio(entry.audio_file)
            self._refresh_words()
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
        if nxt is None and self._playlist_loop: nxt = self.model.first_index()
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

    def _replay_current(self):
        e = self.model.entry(self._current)
        if not e: return
        self._stage = "main"
        self._start_audio(e.audio_file)

    def _first_in_group(self, group_id):
        for i, q in enumerate(self._queue):
            if q.group_id == group_id: return i
        return None

    def _on_position(self, pos):
        if pos != self._position:
            self._position = int(pos)
            self.positionChanged.emit()
        if not self._loop_running(): return
        if self._loop_guard:
            if pos < self._loop_b: self._loop_guard = False
            return
        if pos >= self._loop_b: self._loop_hit()

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

# ============================================================
# Fonts
# ============================================================
def load_quran_font() -> str:
    family = "Arial"
    if os.path.exists(FONT_FILE):
        fid = QFontDatabase.addApplicationFont(FONT_FILE)
        if fid != -1:
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams: family = fams[0]
    log.info("Arabic font: %s", family)
    return family

def load_bangla_font() -> str:
    if os.path.exists(BANGLA_FONT_FILE):
        fid = QFontDatabase.addApplicationFont(BANGLA_FONT_FILE)
        if fid != -1:
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams: return fams[0]
    return "Noto Sans Bengali"

# ============================================================
# Entry point
# ============================================================
def main():
    global _DATA
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("ruqya-quran")
    app.setApplicationDisplayName("Ruqya Quran")
    app.setOrganizationName("ruqya-quran")
    app.setDesktopFileName("ruqya-quran")

    _DATA = None

    font_family = load_quran_font()
    bangla_font = load_bangla_font()

    model = PlaylistModel(parent=app)
    controller = PlayerController(model, font_family, parent=app)
    controller._bangla_font_family = bangla_font

    engine = QQmlApplicationEngine(parent=app)
    ctx = engine.rootContext()
    ctx.setContextProperty("player", controller)
    ctx.setContextProperty("playlistModel", model)

    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    if not engine.rootObjects():
        log.error("QML failed to load")
        sys.exit(1)

    app.aboutToQuit.connect(controller.shutdown)
    QTimer.singleShot(0, lambda: controller.openInitial(sys.argv[1:]))
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
