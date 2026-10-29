"""Everything that touches the network.

The app imports this inside try/except. Delete the file (and `requests`) and the
app keeps working from local data only.

CLI:  python -m ruqya_quran.fetcher examples/Ruqya/default.ruqya [more.ruqya ...]
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Optional

import requests

from .store import DataStore, build_ayah_lookup

log = logging.getLogger("ruqya.fetcher")

AUDIO_SOURCES = {
    "ar.abdurrahmaansudais": ("Abdurrahmaan_As-Sudais_192kbps", "ar.abdurrahmaansudais", 192),
    "ar.saoodshuraym": ("Saood_ash-Shuraym_128kbps", "ar.saoodshuraym", 128),
    "ar.alafasy": ("Mishaari_Raashid_Alafasy_128kbps", "ar.alafasy", 128),
    "ar.ghamdi": ("Ghamadi_40kbps", None, None),
}
SURAH_URL = "https://api.alquran.cloud/v1/surah/{surah}/{edition}"
WORD_BY_WORD_URL = ("https://api.quran.com/api/v4/verses/by_key/{surah}:{ayah}"
                    "?words=true&word_fields=text_uthmani,translation&language={lang}")

def _audio_urls(reciter, surah, ayah, global_ayah_number):
    everyayah_dir, alquran_edition, bitrate = AUDIO_SOURCES.get(reciter, (None, reciter, None))
    urls = []
    if everyayah_dir:
        urls.append(f"https://everyayah.com/data/{everyayah_dir}/{surah:03d}{ayah:03d}.mp3")
    if alquran_edition and global_ayah_number is not None and bitrate is not None:
        urls.append(f"https://cdn.islamic.network/quran/audio/{bitrate}/{alquran_edition}/{global_ayah_number}.mp3")
    return urls

@dataclass
class FetchSettings:
    timeout: float = 10
    retries: int = 2
    backoff: float = 0.5
    fail_threshold: int = 3
    workers: int = 4

    @classmethod
    def from_cfg(cls, cfg: dict) -> "FetchSettings":
        return cls(
            timeout=float(cfg.get("request_timeout", 10)),
            retries=int(cfg.get("max_retries", 2)),
            backoff=float(cfg.get("retry_backoff_base", 0.5)),
            fail_threshold=int(cfg.get("source_fail_threshold", 3)),
            workers=max(1, int(cfg.get("max_workers", 4))),
        )

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

class Fetcher:
    """Provider for DataStore: downloads whatever is missing and saves it into the store."""

    def __init__(self, store: DataStore, settings: Optional[FetchSettings] = None):
        self.store = store
        self.s = settings or FetchSettings()
        self.health = _SourceHealth(self.s.fail_threshold)

    # ---- HTTP ----
    def _get(self, url):
        s, last = self.s, None
        for attempt in range(s.retries + 1):
            try:
                resp = requests.get(url, timeout=s.timeout)
                resp.raise_for_status()
                return resp
            except requests.HTTPError as e:
                code = e.response.status_code if e.response is not None else None
                if code is not None and 400 <= code < 500 and code not in (408, 429):
                    raise
                last = e
            except requests.RequestException as e:
                last = e
            if attempt < s.retries:
                time.sleep(s.backoff * (2**attempt))
        raise last

    # ---- provider interface (called by DataStore) ----
    def fetch_surah(self, surah, edition) -> dict:
        log.info("Downloading surah %s (%s)...", surah, edition)
        data = self._get(SURAH_URL.format(surah=surah, edition=edition)).json()["data"]
        self.store.save_surah(surah, edition, data)
        return data

    def fetch_audio(self, surah, ayah, reciter, ayah_data) -> str:
        number = ayah_data.get("number")
        if number is None:
            raise RuntimeError(f"Global ayah number missing for {surah}:{ayah}")
        urls = _audio_urls(reciter, surah, ayah, number)
        if not urls:
            raise RuntimeError(f"No audio source for reciter {reciter}")
        urls = [u for u in urls if not self.health.is_disabled(u.split("/")[2])]
        if not urls:
            raise RuntimeError(f"All audio sources disabled ({surah}:{ayah})")

        target = self.store.audio_target(surah, ayah, reciter)
        last_err = None
        for url in urls:
            host = url.split("/")[2]
            try:
                log.info("Downloading %s:%s from %s...", surah, ayah, host)
                resp = self._get(url)
                with open(target, "wb") as f:
                    f.write(resp.content)
                self.health.record_success(host)
                return str(target)
            except Exception as e:
                last_err = e
                self.health.record_failure(host)
                log.warning("  %s failed: %s", host, e.__class__.__name__)
        raise last_err or RuntimeError("All audio sources failed")

    def fetch_words(self, surah, ayah, lang) -> list:
        url = WORD_BY_WORD_URL.format(surah=surah, ayah=ayah, lang=lang)
        words = self._get(url).json().get("verse", {}).get("words", [])
        out, have_bangla = [], False
        for w in words:
            trans = w.get("translation", {}) or {}
            text = trans.get("text", "") or ""
            arabic = w.get("text_uthmani", "") or ""
            if (trans.get("language_name") or "").lower() in ("bengali", "bangla", "bn"):
                have_bangla = True
                out.append({"arabic": arabic, "english": "", "bangla": text})
            else:
                out.append({"arabic": arabic, "english": text, "bangla": ""})
        if lang == "bn" and not have_bangla:
            try:
                bn = build_ayah_lookup(self.store.surah(surah, "bn.bengali")).get(ayah, {}).get("text", "")
                if bn:
                    out.append({"arabic": "", "english": "", "bangla": bn})
            except Exception as ex:
                log.warning("Bangla ayah fallback failed: %s", ex)
        if out:
            try:
                self.store.save_words(surah, ayah, lang, out)
            except OSError as ex:
                log.warning("Could not write words cache: %s", ex)
        return out

    # ---- bulk warm-up ----
    def warm(self,
             pairs,
             reciters,
             translations,
             progress: Optional[Callable[[int, int, str], None]] = None,
             cancelled: Callable[[], bool] = lambda: False) -> bool:
        """Download every missing text/audio file. Blocking; run it off the UI thread.

        Returns False if cancelled, True otherwise. Individual failures are logged, not raised.
        """
        pairs = sorted(set(pairs))
        reciters, translations = list(reciters), list(translations)
        surahs = sorted({s for s, _ in pairs})
        editions = list(dict.fromkeys(reciters + translations))
        meta_jobs = [(ed, s) for ed in editions for s in surahs]
        audio_jobs = [(r, s, a) for r in reciters for s, a in pairs]
        total = len(meta_jobs) + len(audio_jobs)
        done = 0
        lock = threading.Lock()

        def tick(label):
            nonlocal done
            with lock:
                done += 1
                c = done
            if progress:
                progress(c, total, label)

        def meta(edition, surah):
            if cancelled():
                return
            try:
                self.store.surah(surah, edition)
            except Exception as e:
                log.warning("Warmup text %s/%s failed: %s", surah, edition, e)
            tick(f"Downloading text · {edition}")

        def audio(reciter, surah, ayah):
            if cancelled():
                return
            try:
                ayah_data = build_ayah_lookup(self.store.surah(surah, reciter)).get(ayah)
                if ayah_data is not None:
                    self.store.audio(surah, ayah, reciter, ayah_data)
            except Exception as e:
                log.warning("Warmup audio %s:%s (%s) failed: %s", surah, ayah, reciter, e)
            tick(f"Downloading audio · {reciter}")

        for fn, jobs, prefix in ((meta, meta_jobs, "warmup-meta"), (audio, audio_jobs, "warmup-audio")):
            if not jobs:
                continue
            with ThreadPoolExecutor(max_workers=self.s.workers, thread_name_prefix=prefix) as pool:
                futures = [pool.submit(fn, *j) for j in jobs]
                for fut in as_completed(futures):
                    if cancelled():
                        for f in futures:
                            f.cancel()
                        return False
                    fut.result()
        log.info("Warmup finished. Disabled sources: %s", self.health.disabled_hosts() or "none")
        return True

# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    import argparse
    from pathlib import Path

    from .config import CFG, PRELOAD_RECITERS, PRELOAD_TRANSLATIONS, RECITERS, TRANSLATIONS
    from .playlist import build_queue_from_items, read_playlist_file

    ap = argparse.ArgumentParser(prog="ruqya-fetch", description="Download all data a playlist needs.")
    ap.add_argument("playlist", nargs="+", type=Path)
    ap.add_argument("--reciter", action="append", choices=list(RECITERS), help="default: playlist/config preload list")
    ap.add_argument("--translation", action="append", choices=list(TRANSLATIONS))
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    for path in args.playlist:
        data = read_playlist_file(path)
        store = DataStore(path, data["data_dir"])
        fetcher = Fetcher(store, FetchSettings.from_cfg(CFG))
        store.attach(fetcher)
        queue = build_queue_from_items(data["items"], store)
        pairs = [(1, 1)] + [(q.surah, q.ayah) for q in queue if q.kind == "quran"]  # 1:1 = Bismillah
        reciters = args.reciter or [r for r in data["preload_reciters"] if r in RECITERS] or PRELOAD_RECITERS
        translations = (args.translation or [t for t in data["preload_translations"] if t in TRANSLATIONS]
                        or PRELOAD_TRANSLATIONS)
        print(f"{path}: {len(pairs)} ayahs, reciters={reciters}, translations={translations}")
        fetcher.warm(pairs,
                     reciters,
                     translations,
                     progress=lambda c, t, m: print(f"\r  {c}/{t}  {m:<40}", end="", flush=True))
        print()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
