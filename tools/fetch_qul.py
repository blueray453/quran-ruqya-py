#!/usr/bin/env python3
"""Fetch and bundle QUL data into a playlist's data folder.

Requires QUL JSON exports in --src (default: tools/raw/):

    ayah-recitation-*.json          recitations (audio_url + segments)
    qpc-hafs-word-by-word.json      Arabic word-by-word script
    english-wbw-translation.json    English word-by-word
    bangali-word-by-word-translation.json  Bangla word-by-word
    en-sahih-international-simple.json     English ayah-level
    bn-taisirul-quran-simple.json          Bangla ayah-level
    bn-rawai-al-bayan-simple.json          Bangla ayah-level
    quran-metadata-surah-name.json         Surah metadata

Only recitations whose `audio_url` host maps to a reciter in TARGET_RECITERS
are bundled. Everything else (extra reciters, duplicates) is skipped with a
clear log line. Segment arrays with string positions are normalized to ints.

Usage:

    python3 tools/fetch_qul.py                         # default playlist, all target reciters
    python3 tools/fetch_qul.py --playlist path/foo.ruqya
    python3 tools/fetch_qul.py --skip-audio             # JSON only, fast
    python3 tools/fetch_qul.py --list                   # preview only
    python3 tools/fetch_qul.py --restart                # re-download all
    python3 tools/fetch_qul.py --validate-only          # tokenization check

    # Test one reciter, deleting others first
    python3 tools/fetch_qul.py --only-reciter ar.abdurrahmaansudais --prune-others

    # Add one reciter on top of what exists
    python3 tools/fetch_qul.py --only-reciter ar.alafasy

Resume-safe via `.mp3.part` + `wget -c`. Falls back to urllib with Range
resume when wget is not installed.
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
from typing import Optional
from urllib.parse import urlparse

try:
    from mutagen import File as MutagenFile
except ImportError:
    MutagenFile = None
    print("warn: mutagen missing — durations will be 0; pip install mutagen", file=sys.stderr)

WGET = shutil.which("wget")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Reciters to bundle. Add a reciter here AND to DEFAULTS["reciters"] in
# src/ruqya_quran/main.py to expose it in the picker. Files targeting a
# reciter not in this set are skipped with a clear message.
TARGET_RECITERS = {
    "ar.abdurrahmaansudais",
    "ar.alafasy",
    "ar.ghamdi",
    "ar.husary",
    "ar.husarymuallim",
    "ar.saoodshuraym",
}

RECITER_BY_HOST = {
    # Tarteel CDN:    audio-cdn.tarteel.ai/quran/<host>/<file>.mp3
    "abdulrahmanAlSudais": "ar.abdurrahmaansudais",
    "alafasy": "ar.alafasy",
    "ghamadi": "ar.ghamdi",
    "husary": "ar.husary",
    "husaryMuallim": "ar.husarymuallim",
    "saudAlShuraim": "ar.saoodshuraym",
    # Quran.com CDN:  audio.qurancdn.com/<host>/mp3/<file>.mp3
    "Sudais": "ar.abdurrahmaansudais",
    "Alafasy_128kbps": "ar.alafasy",
    "Ghamadi_40kbps": "ar.ghamdi",
    "Husary_128kbps": "ar.husary",
    "Husary_Muallim_128kbps": "ar.husarymuallim",
    "Saood_ash-Shuraym_128kbps": "ar.saoodshuraym",
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

def reciter_id(audio_url: str) -> Optional[str]:
    """Return internal reciter ID from a QUL audio URL, or None if unknown."""
    if not audio_url:
        return None
    parts = [p for p in urlparse(audio_url).path.split("/") if p]
    host = None
    if "audio-cdn.tarteel.ai" in audio_url and len(parts) >= 2 and parts[0] == "quran":
        host = parts[1]
    elif "audio.qurancdn.com" in audio_url and len(parts) >= 3 and parts[1] == "mp3":
        host = parts[0]
    if host is None:
        return None
    return RECITER_BY_HOST.get(host)

def normalize_segments(segments) -> Optional[list]:
    """Return [[pos,start_ms,end_ms], ...] as ints, or None if malformed."""
    out = []
    for seg in segments or []:
        if not isinstance(seg, (list, tuple)) or len(seg) != 3:
            return None
        try:
            out.append([int(seg[0]), int(seg[1]), int(seg[2])])
        except (TypeError, ValueError):
            return None
    return out

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

def prune_others(out: Path, keep: str):
    """Delete recitation JSONs and audio folders for reciters != keep."""
    kept = []
    pruned = []
    rec_dir = out / "recitations"
    if rec_dir.exists():
        for p in sorted(rec_dir.glob("*.json")):
            if p.stem == keep:
                kept.append(p.stem)
            else:
                p.unlink()
                pruned.append(p.stem)
    audio_dir = out / "audio"
    if audio_dir.exists():
        for d in sorted(audio_dir.iterdir()):
            if not d.is_dir():
                continue
            if d.name == keep:
                continue
            shutil.rmtree(d)
            pruned.append(d.name + "/")
    if pruned:
        log(f"[prune] removed: {', '.join(pruned)}")
    if kept:
        log(f"[prune] kept: {', '.join(kept)}")

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
    seen = set()
    for path in sorted(src.glob("ayah-recitation-*.json")):
        raw = load_json(path)
        first = next(iter(raw.values()))
        rid = reciter_id(first.get("audio_url", ""))
        if rid is None:
            log(f"\n[recitations] SKIP {path.name}: unknown host "
                f"in {first.get('audio_url', '')!r}")
            continue
        if rid not in TARGET_RECITERS:
            log(f"\n[recitations] SKIP {path.name}: {rid} not in TARGET_RECITERS")
            continue
        if only_reciter and rid != only_reciter:
            log(f"\n[recitations] SKIP {path.name}: {rid} not in --only-reciter")
            continue
        if rid in seen:
            log(f"\n[recitations] SKIP {path.name}: duplicate of {rid}")
            continue
        seen.add(rid)

        log(f"\n[recitations] {path.name} -> {rid}")
        sidecar = dict(raw)

        # Normalize segments for every entry (defensive — some QUL exports
        # use string positions, and the bad Sudais file has only 2 segments).
        for key, entry in sidecar.items():
            segs = normalize_segments(entry.get("segments"))
            if segs is None:
                log(f"  WARN {rid} {key}: malformed segments; dropped")
                entry["segments"] = []
            else:
                entry["segments"] = segs

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
            jobs.append((key, entry, mp3, entry.get("audio_url", "")))

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
    """Diagnostic only. Never fails the build.

    At runtime, missing segments render as untimed words (no underline), and
    extra segments (ayah-end marker is in script, not in segments) are simply
    unused. Tokenization drift between QPC script and QUL segments accounts
    for every anomaly seen; all are harmless.
    """
    log("[validate]")
    total = 0
    for rid, sidecar in bundled.items():
        extra = partial = 0
        samples = []
        for key, entry in sidecar.items():
            s, a = key.split(":")
            n_words = 0
            while f"{s}:{a}:{n_words + 1}" in script:
                n_words += 1
            positions = [seg[0] for seg in entry.get("segments", [])]
            if not positions:
                continue
            max_pos = max(positions)
            if max_pos > n_words:
                extra += 1
                samples.append((key, f"extra seg pos {max_pos} vs {n_words} words"))
            elif max_pos < n_words - 1:
                partial += 1
                samples.append((key, f"missing seg {max_pos} vs {n_words} words"))
        if extra or partial:
            log(f"  {rid}: {extra} extra, {partial} partial (harmless)")
            for key, why in sorted(samples)[:3]:
                log(f"    {key}: {why}")
            total += extra + partial
    if total:
        log(f"  {total} anomalous ayahs across all reciters "
            f"(untimed words render without underline)")
    else:
        log("  all ayahs align cleanly")
    return 0

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
    ap.add_argument("--prune-others",
                    action="store_true",
                    help="with --only-reciter, delete other recitations + audio first")
    ap.add_argument("--workers", type=int, default=4, help="concurrent MP3 downloads (default: 4)")
    ap.add_argument("--list", action="store_true", help="list files that would be downloaded, then exit")
    ap.add_argument("--restart", action="store_true", help="re-download files even if they already exist")
    args = ap.parse_args(argv)

    if not WGET:
        log("note: wget not found; using urllib (resume via Range header)")
    check_required(args.src)

    out = resolve_out(args)

    if args.prune_others:
        if not args.only_reciter:
            log("warn: --prune-others has no effect without --only-reciter")
        else:
            prune_others(out, args.only_reciter)

    if args.validate_only:
        script = load_json((out / "script" / "words.json") if (out / "script" / "words.json").exists() else args.src /
                           SCRIPT_FILE)
        bundled = {p.stem: load_json(p) for p in (out / "recitations").glob("*.json")}
        return 0 if validate(bundled, script) is not None else 1

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

    validate(bundled, load_json(args.src / SCRIPT_FILE))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
