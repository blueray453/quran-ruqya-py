"""Playlist file parsing and queue building. No Qt, no network."""
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from .config import CUSTOM_PLAYLIST_SEPARATOR_LABEL

log = logging.getLogger("ruqya.playlist")

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

def build_queue_from_items(items: list, store) -> list:
    """`store` is a DataStore; it is only used to resolve custom clip paths."""
    queue: list[QueueItem] = []
    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            continue
        if "path" in raw:
            path = store.resolve_clip(raw.get("path", ""))
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
