"""Local data access for one playlist workspace. No network code lives here."""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("ruqya.store")

class DataMissing(LookupError):
    """Requested data is not on disk and no provider can fetch it."""

def build_ayah_lookup(surah_data: dict) -> dict:
    return {a["numberInSurah"]: a for a in surah_data["ayahs"]}

class DataStore:
    """<playlist>.ruqya + its data folder.

    Layout (unchanged):
      data/audio/<reciter>/<surah>_<ayah>.mp3
      data/text/<edition>/surah_<n>.json
      data/words/<lang>/<surah>_<ayah>.json
      data/clips/*.mp3

    `provider` is optional and duck-typed: fetch_surah / fetch_audio / fetch_words.
    The store never knows what it is or how it works.
    """

    def __init__(self, playlist_path: Path, data_dir: str = ""):
        self.playlist_path = Path(playlist_path).resolve()
        self.base_dir = self.playlist_path.parent
        d = Path(data_dir).expanduser() if data_dir else Path("data")
        self.data_dir = d if d.is_absolute() else self.base_dir / d
        self.write_dir = self._pick_write_dir()
        self.provider = None

    # ---- provider hook ----
    def attach(self, provider) -> None:
        self.provider = provider

    @property
    def can_fetch(self) -> bool:
        return self.provider is not None

    # ---- locations ----
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
        log.warning("Data folder is read-only; writes go to %s", fallback)
        return fallback

    def _find(self, *parts: str) -> Path:
        p = self.data_dir.joinpath(*parts)
        return p if p.exists() else self.write_dir.joinpath(*parts)

    def audio_path(self, surah, ayah, reciter) -> Path:
        return self._find("audio", reciter, f"{surah}_{ayah}.mp3")

    def text_path(self, surah, edition) -> Path:
        return self._find("text", edition, f"surah_{surah}.json")

    def words_path(self, surah, ayah, lang) -> Path:
        return self._find("words", lang, f"{surah}_{ayah}.json")

    def resolve_clip(self, raw: str) -> str:
        if not raw:
            return ""
        p = Path(raw).expanduser()
        return str(p if p.is_absolute() else self.data_dir / p)

    # ---- raw local reads ----
    @staticmethod
    def _read_json(path: Path, what: str):
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Corrupt %s %s: %s", what, path, e)
            return None

    def read_surah(self, surah, edition) -> Optional[dict]:
        return self._read_json(self.text_path(surah, edition), "text file")

    def read_words(self, surah, ayah, lang) -> Optional[list]:
        return self._read_json(self.words_path(surah, ayah, lang), "words file")

    # ---- writes (used by whatever builds the data) ----
    @staticmethod
    def _write_json(path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_surah(self, surah, edition, data) -> None:
        self._write_json(self.text_path(surah, edition), data)

    def save_words(self, surah, ayah, lang, data) -> None:
        self._write_json(self.words_path(surah, ayah, lang), data)

    def audio_target(self, surah, ayah, reciter) -> Path:
        p = self.audio_path(surah, ayah, reciter)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # ---- what the app calls: local first, provider if attached ----
    def surah(self, surah, edition) -> dict:
        cached = self.read_surah(surah, edition)
        if cached:
            return cached
        if not self.provider:
            raise DataMissing(f"text/{edition}/surah_{surah}.json not found in {self.data_dir}")
        return self.provider.fetch_surah(surah, edition)

    def audio(self, surah, ayah, reciter, ayah_data) -> str:
        p = self.audio_path(surah, ayah, reciter)
        if p.exists():
            return str(p)
        if not self.provider:
            raise DataMissing(f"audio/{reciter}/{surah}_{ayah}.mp3 not found in {self.data_dir}")
        return self.provider.fetch_audio(surah, ayah, reciter, ayah_data)

    def words(self, surah, ayah, lang) -> Optional[list]:
        cached = self.read_words(surah, ayah, lang)
        if cached is not None:
            return cached
        if not self.provider:
            return None
        try:
            return self.provider.fetch_words(surah, ayah, lang)
        except Exception as e:
            log.warning("Word-by-word unavailable for %s:%s: %s", surah, ayah, e)
            return None

    def is_complete(self, pairs, reciters, editions) -> bool:
        """pairs: iterable of (surah, ayah). True if everything is already on disk."""
        pairs = list(pairs)
        surahs = {s for s, _ in pairs}
        for ed in editions:
            if any(not self.text_path(s, ed).exists() for s in surahs):
                return False
        for r in reciters:
            if any(not self.audio_path(s, a, r).exists() for s, a in pairs):
                return False
        return True
