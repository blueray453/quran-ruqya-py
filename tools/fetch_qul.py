#!/usr/bin/env python3
"""Fetch and bundle QUL data into a playlist's data folder.

Requires QUL JSON exports in --src (default: tools/raw/). Download each once
from qul.tarteel.ai/resources/<category> and place in tools/raw/:

    ayah-recitation-*.json          5 reciters (audio + segments)
    qpc-hafs-word-by-word.json      Arabic word-by-word script
    english-wbw-translation.json    English word-by-word
    bangali-word-by-word-translation.json  Bangla word-by-word
    en-sahih-international-simple.json     English ayah-level
    bn-taisirul-quran-simple.json          Bangla ayah-level
    bn-rawai-al-bayan-simple.json          Bangla ayah-level
    quran-metadata-surah-name.json         Surah metadata

Usage:

    python3 tools/fetch_qul.py                         # uses examples/Ruqya/ruqya.ruqya
    python3 tools/fetch_qul.py --playlist path/foo.ruqya
    python3 tools/fetch_qul.py --out path/to/data       # explicit output
    python3 tools/fetch_qul.py --skip-audio             # JSON only (~5s, validates)
    python3 tools/fetch_qul.py --list                   # preview, exit
    python3 tools/fetch_qul.py --restart                # re-download everything
    python3 tools/fetch_qul.py --validate-only          # tokenization check

Downloads go to <out>/audio/<reciter>/<surah>_<ayah>.mp3.
Sidecars go to <out>/{meta,script,translations,wbw,recitations}/.

Resume-safe: uses `.mp3.part` + rename; `wget -c` picks up where it left off.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

try:
    from mutagen import File as MutagenFile
except ImportError:
    MutagenFile = None
    print("warn: mutagen missing — durations will be 0; pip install mutagen", file=sys.stderr)

WGET = shutil.which("wget")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

RECITER_BY_HOST = {
    "abdulrahmanAlSudais": "ar.abdurrahmaansudais",
    "alafasy": "ar.alafasy",
    "ghamadi": "ar.ghamdi",
    "husary": "ar.husary",
    "husaryMuallim": "ar.husarymuallim",
}
TRANSLATIONS = {
    "en-sahih-international-simple.json": "en.sahih",
    "bn-taisirul-quran-simple.json": "bn.taisirul",
    "bn-rawai-al-bayan-simple.json": "bn.rawai",
}
WBW = {
    "english-wbw-translation.json": "en",
    "bangali-word-by-word-translation.json": "bn",
}
SCRIPT_FILE = "qpc-hafs-word-by-word.json"
META_FILE = "quran-metadata-surah-name.json"
REQUIRED = [SCRIPT_FILE, META_FILE, *TRANSLATIONS, *WBW]
DEFAULT_PLAYLIST = Path("examples/Ruqya/ruqya.ruqya")

def log(msg):
    print(msg, flush=True)

def fmt_dur(sec):
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m{sec % 60:02d}s"
    return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"

def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def write_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    log(f"  wrote {p} ({p.stat().st_size // 1024} KB)")

def reciter_id(audio_url: str) -> str:
    parts = urlparse(audio_url).path.split("/")
    if len(parts) < 3 or parts[2] not in RECITER_BY_HOST:
        raise SystemExit(f"unknown reciter host in {audio_url!r}")
    return RECITER_BY_HOST[parts[2]]

def probe_ms(mp3: Path) -> int:
    if not MutagenFile or not mp3.exists():
        return 0
    try:
        f = MutagenFile(str(mp3))
        return int(f.info.length * 1000) if f and f.info else 0
    except Exception:
        return 0

# ---------------------------------------------------------------- progress
class Progress:

    def __init__(self, total, label):
        self.total = total
        self.label = label
        self.done = self.cached = self.errors = 0
        self.start = time.time()
        self._lock = threading.Lock()
        self._bar_len = 0
        self._is_tty = sys.stdout.isatty()

    def _bar_str(self):
        pct = self.done / self.total * 100 if self.total else 100
        width = 24
        filled = int(width * self.done / max(1, self.total))
        bar = "█" * filled + "░" * (width - filled)
        elapsed = time.time() - self.start
        rate = self.done / elapsed if elapsed > 0 else 0
        eta = (self.total - self.done) / rate if rate > 0 else 0
        warn = f"  ⚠ {self.errors}" if self.errors else ""
        return (f"  {self.label} [{bar}] {self.done}/{self.total} "
                f"({pct:5.1f}%) {rate:5.1f}/s ETA {fmt_dur(eta)}{warn}")

    def _erase_bar(self):
        if self._is_tty and self._bar_len:
            sys.stdout.write("\r" + " " * self._bar_len + "\r")

    def _draw_bar(self):
        if not self._is_tty:
            return
        s = self._bar_str()
        sys.stdout.write(s)
        sys.stdout.flush()
        self._bar_len = len(s)

    def file_done(self, name, status, size, elapsed, error):
        with self._lock:
            self.done += 1
            if status == "cached":
                self.cached += 1
                line = f"  {name}  ·  cached"
            elif status == "error":
                self.errors += 1
                line = f"  {name}  ✗  {error or 'error'}"
            else:
                kb = size // 1024
                t = f"  {elapsed:.1f}s" if elapsed else ""
                line = f"  {name}  ✓  {kb} KB{t}"
            self._erase_bar()
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
            self._draw_bar()

    def finish(self):
        with self._lock:
            self._erase_bar()
            if self._is_tty:
                sys.stdout.write(self._bar_str() + "\n")
            else:
                sys.stdout.write(f"  {self.label}: {self.done}/{self.total} "
                                 f"({self.cached} cached, {self.errors} errors)\n")
            sys.stdout.flush()

# ---------------------------------------------------------------- download
def download_wget(url, dest: Path):
    part = dest.with_name(dest.name + ".part")
    if dest.exists() and dest.stat().st_size > 512:
        return "cached", dest.stat().st_size, None
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run([WGET, "-c", "-q", "--timeout=60", "--tries=3", "--user-agent", UA, "-O",
                            str(part), url],
                           capture_output=True,
                           timeout=180)
    except subprocess.TimeoutExpired:
        return "error", 0, "wget timeout"
    except Exception as e:
        return "error", 0, str(e)[:80]
    if r.returncode != 0:
        err = (r.stderr.decode("utf-8", "replace").strip().split("\n")[-1] if r.stderr else f"exit {r.returncode}")
        return "error", 0, err
    if not part.exists() or part.stat().st_size < 512:
        return "error", 0, "file too small"
    part.rename(dest)
    return "ok", dest.stat().st_size, None

def download_urllib(url, dest: Path):
    part = dest.with_name(dest.name + ".part")
    if dest.exists() and dest.stat().st_size > 512:
        return "cached", dest.stat().st_size, None
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": UA, "Accept": "audio/mpeg,audio/*;q=0.9,*/*;q=0.8"}
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            mode = "wb" if r.status == 200 else ("ab" if r.status == 206 else None)
            if mode is None:
                return "error", 0, f"status {r.status}"
            with open(part, mode) as f:
                shutil.copyfileobj(r, f)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return "error", 0, "403 forbidden"
        if e.code == 416:
            if part.exists() and part.stat().st_size > 512:
                part.rename(dest)
                return "ok", dest.stat().st_size, None
            return "error", 0, "range not satisfiable"
        return "error", 0, f"HTTP {e.code}"
    except Exception as e:
        return "error", 0, str(e)[:80]
    if not part.exists() or part.stat().st_size < 512:
        return "error", 0, "file too small"
    part.rename(dest)
    return "ok", dest.stat().st_size, None

def download(url, dest):
    if WGET:
        return download_wget(url, dest)
    return download_urllib(url, dest)

# ---------------------------------------------------------------- bundle pieces
def check_required(src: Path):
    missing = [n for n in REQUIRED if not (src / n).exists()]
    if not list(src.glob("ayah-recitation-*.json")):
        missing.append("ayah-recitation-*.json")
    if missing:
        print(f"missing in {src}:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        print("download from qul.tarteel.ai/resources", file=sys.stderr)
        raise SystemExit(2)

def resolve_out(args) -> Path:
    if args.out is not None:
        return args.out.resolve()
    if args.playlist is not None:
        pl = load_json(args.playlist)
        data_dir = pl.get("data_dir") or "data"
        out = (args.playlist.parent / data_dir).resolve()
        log(f"playlist:  {args.playlist}")
        log(f"data dir:  {out}")
        return out
    if DEFAULT_PLAYLIST.exists():
        pl = load_json(DEFAULT_PLAYLIST)
        data_dir = pl.get("data_dir") or "data"
        out = (DEFAULT_PLAYLIST.parent / data_dir).resolve()
        log(f"playlist:  {DEFAULT_PLAYLIST}  (default)")
        log(f"data dir:  {out}")
        return out
    out = Path("data").resolve()
    log(f"data dir:  {out}  (no playlist found, using ./data)")
    return out

def bundle_script(src, out):
    log("[script]")
    write_json(out / "script" / "words.json", load_json(src / SCRIPT_FILE))

def bundle_meta(src, out):
    log("[meta]")
    write_json(out / "meta" / "surahs.json", load_json(src / META_FILE))

def bundle_translations(src, out):
    log("[translations]")
    for filename, edition in TRANSLATIONS.items():
        write_json(out / "translations" / f"{edition}.json", load_json(src / filename))

def bundle_wbw(src, out):
    log("[wbw]")
    for filename, lang in WBW.items():
        write_json(out / "wbw" / f"{lang}.json", load_json(src / filename))

def _list_recitation(out: Path, rid: str, sidecar: dict):
    cached = to_dl = 0
    for key in sidecar:
        s, a = key.split(":")
        mp3 = out / "audio" / rid / f"{s}_{a}.mp3"
        if mp3.exists() and mp3.stat().st_size > 512:
            cached += 1
        else:
            to_dl += 1
            print(f"  {rid}/{s}_{a}.mp3")
    print(f"  -- {to_dl} to download, {cached} cached --")

def bundle_recitations(src, out, skip_audio, workers, only_reciter, list_only=False, restart=False):
    bundled = {}
    for path in sorted(src.glob("ayah-recitation-*.json")):
        raw = load_json(path)
        first = next(iter(raw.values()))
        rid = reciter_id(first["audio_url"])
        if only_reciter and rid != only_reciter:
            continue

        log(f"\n[recitations] {path.name} -> {rid}")
        sidecar = dict(raw)
        n = len(sidecar)

        if list_only:
            _list_recitation(out, rid, sidecar)
            continue

        if skip_audio:
            existing = {}
            p_existing = out / "recitations" / f"{rid}.json"
            if p_existing.exists():
                try:
                    existing = load_json(p_existing)
                except Exception:
                    pass
            preserved = 0
            for key, entry in sidecar.items():
                entry.pop("audio_url", None)
                if entry.get("duration") is None:
                    prev = existing.get(key, {})
                    d = int(prev.get("duration", 0) or 0)
                    entry["duration"] = d
                    if d > 0:
                        preserved += 1
            write_json(out / "recitations" / f"{rid}.json", sidecar)
            if preserved:
                log(f"  preserved {preserved} durations from previous bundle")
            bundled[rid] = sidecar
            continue

        jobs = []
        for key, entry in sidecar.items():
            s, a = key.split(":")
            mp3 = out / "audio" / rid / f"{s}_{a}.mp3"
            if restart:
                if mp3.exists():
                    mp3.unlink()
                part = mp3.with_name(mp3.name + ".part")
                if part.exists():
                    part.unlink()
            jobs.append((key, entry, mp3, entry["audio_url"]))

        bar = Progress(n, rid)
        first_error = None
        futs = []

        def worker(job):
            key, entry, mp3, url = job
            t0 = time.time()
            status, size, err = download(url, mp3)
            return key, entry, mp3, status, size, err, time.time() - t0

        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(worker, j) for j in jobs]
                for fut in as_completed(futs):
                    key, entry, mp3, status, size, err, elapsed = fut.result()
                    entry.pop("audio_url", None)
                    if entry.get("duration") is None:
                        entry["duration"] = probe_ms(mp3)
                    bar.file_done(mp3.name, status, size, elapsed, err)
                    if err and first_error is None:
                        first_error = err
        except KeyboardInterrupt:
            log("\n  interrupted — .part files will resume on next run")
            for f in futs:
                f.cancel()
            bar.finish()
            return bundled

        bar.finish()
        if first_error:
            log(f"  first error: {first_error}")
        write_json(out / "recitations" / f"{rid}.json", sidecar)
        bundled[rid] = sidecar

    return bundled

# ---------------------------------------------------------------- validate
def validate(bundled, script):
    log("[validate]")
    errors = warnings = 0
    for rid, sidecar in bundled.items():
        for key, entry in sidecar.items():
            s, a = key.split(":")
            n_words = 0
            while f"{s}:{a}:{n_words + 1}" in script:
                n_words += 1
            positions = [seg[0] for seg in entry.get("segments", [])]
            max_pos = max(positions) if positions else 0
            if max_pos > n_words:
                log(f"  ERROR {rid} {key}: segment pos {max_pos} > {n_words} words")
                errors += 1
            elif max_pos and max_pos < n_words:
                warnings += 1
    log(f"  {errors} errors, {warnings} warnings")
    return errors

# ---------------------------------------------------------------- summary
def summarize(out: Path):
    audio_dir = out / "audio"
    if not audio_dir.exists():
        log("  (no audio directory)")
        return
    total_files = total_bytes = 0
    parts = 0
    for rid_dir in sorted(audio_dir.iterdir()):
        if not rid_dir.is_dir():
            continue
        files = 0
        size = 0
        for mp3 in rid_dir.glob("*.mp3"):
            if mp3.stat().st_size > 512:
                files += 1
                size += mp3.stat().st_size
        for _ in rid_dir.glob("*.part"):
            parts += 1
        total_files += files
        total_bytes += size
        log(f"  {rid_dir.name}: {files} files, {size // (1024 * 1024)} MB")
    log(f"  total: {total_files} files, {total_bytes // (1024 * 1024)} MB" +
        (f"  ({parts} .part files remaining)" if parts else ""))

# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=Path("tools/raw"))
    ap.add_argument("--playlist",
                    type=Path,
                    default=None,
                    help=".ruqya file; output becomes <playlist_dir>/<data_dir>")
    ap.add_argument("--out", type=Path, default=None, help="explicit data dir (overrides --playlist)")
    ap.add_argument("--skip-audio", action="store_true", help="write JSON only, no MP3 download")
    ap.add_argument("--validate-only", action="store_true", help="check tokenization alignment without re-bundling")
    ap.add_argument("--only-reciter", type=str, default=None, help="bundle only this reciter id")
    ap.add_argument("--workers", type=int, default=4, help="concurrent MP3 downloads (default: 4)")
    ap.add_argument("--list", action="store_true", help="list files that would be downloaded, then exit")
    ap.add_argument("--restart", action="store_true", help="re-download files even if they already exist")
    args = ap.parse_args(argv)

    if not WGET:
        log("note: wget not found; using urllib (resume via Range header)")
    check_required(args.src)

    out = resolve_out(args)

    if args.validate_only:
        script = load_json((out / "script" / "words.json") if (out / "script" / "words.json").exists() else args.src /
                           SCRIPT_FILE)
        bundled = {p.stem: load_json(p) for p in (out / "recitations").glob("*.json")}
        return 1 if validate(bundled, script) else 0

    t0 = time.time()
    bundle_script(args.src, out)
    bundle_meta(args.src, out)
    bundle_translations(args.src, out)
    bundle_wbw(args.src, out)

    bundled = bundle_recitations(args.src,
                                 out,
                                 args.skip_audio,
                                 args.workers,
                                 args.only_reciter,
                                 list_only=args.list,
                                 restart=args.restart)

    if args.list:
        log("\n[summary — what exists]")
        summarize(out)
        return 0

    write_json(
        out / "VERSION", {
            "source": "QUL / Tarteel",
            "reciters": sorted(bundled.keys()),
            "translations": list(TRANSLATIONS.values()),
            "wbw": list(WBW.values()),
        })

    log(f"\n[summary — took {fmt_dur(time.time() - t0)}]")
    summarize(out)

    return 1 if validate(bundled, load_json(args.src / SCRIPT_FILE)) else 0

if __name__ == "__main__":
    raise SystemExit(main())
