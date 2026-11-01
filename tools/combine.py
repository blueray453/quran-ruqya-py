#!/usr/bin/env python3
"""
Concatenate project source into a single file for LLM context.

Uses `git ls-files --cached --others --exclude-standard` so .gitignore is
the single source of truth for what's in the project. Then:

  1. Filters out bulk binary/data trees, the OpenAPI spec, pure-reference
     docs that duplicate code (keyboard map, config keys, deploy recipes),
     standard MIT boilerplate, trivial one-liners, binary files, and
     anything above a size cap (except this script itself).
  2. Emits tools/combine.py first — context-first: the reader sees how
     the dump was built before reading what's in it.
  3. Emits a small ASCII tree derived from the filtered list, with
     skipped directories collapsed to a "[N files not shown]" marker.
  4. Emits a DATA INVENTORY section — walk of the resolved data folder
     (see `resolve_data_dir`) with file sizes plus one `to_entries[0]`
     sample per JSON file — so the reader sees the data-folder schema
     without the bulk.
  5. Emits docs/KNOWN-NON-ISSUES.md first (so the reader knows what
     *not* to flag), then docs/DATA-SCHEMA.md (the data contract), then
     README.md, then docs/INSTALL.md, then each remaining file
     alphabetically, with a `// ===== FILE: path =====` header.
  6. Prints, to stdout, the total line count of the finished combined.txt
     and the line count of every emitted source file (i.e. its `wc -l`,
     not its position inside combined.txt).

Usage:
    python3 tools/combine.py                                       # → combined.txt
    python3 tools/combine.py out.txt                               # custom name
    python3 tools/combine.py combined.txt 100                      # skip files > 100 KB
    python3 tools/combine.py combined.txt 500 /path/to/data        # explicit data dir
    RUQYA_DATA_ROOT=/path/to/Ruqya python3 tools/combine.py        # env override
"""

import json
import os
import subprocess
import sys
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "combined.txt")
MAX_KB = int(sys.argv[2]) if len(sys.argv) > 2 else 500

# The script itself. Emitted before the tree so the reader sees how the
# dump was built before reading what's in it. Never skipped for size.
SELF_PATH = "tools/combine.py"

# High-signal files that come first after the tree, in this order.
# KNOWN-NON-ISSUES goes first so an LLM sees "don't flag these" before
# it reads any source. DATA-SCHEMA comes second — before main.py —
# so the reader knows what the data folder contains when it reads
# DataStore._load / words / segments / translation / wbw.
PRIORITY = [
    "docs/KNOWN-NON-ISSUES.md",
    "docs/DATA-SCHEMA.md",
    "README.md",
    "docs/INSTALL.md",
]

# Directories whose contents are tracked in git but not useful as LLM
# context. Collapsed to a marker in the tree.
SKIP_PREFIXES = (
    "tools/raw/",  # QUL JSON source files for bundle; mirrored at <data>/
    "examples/Ruqya/data/",  # legacy in-repo bundle target (if present)
)

# Exact relative paths dropped silently — no tree marker, no content.
SKIP_PATHS = {
    "tools/fetch_qul.py",
    # Meta: this script's output (the script itself is emitted up top)
    "combined.txt",
    "docs/INSTALL.md",

    # Pure reference: keyboard map, config keys, "make your own playlist"
    # walkthrough, folder-layout table. All of it is derivable from
    # Shortcut { ... } blocks in Main.qml, _CFG.get(...) calls in main.py,
    # and the docstring at the top of main.py. No reasoning value here.
    "docs/REFERENCE.md",

    # MIT boilerplate — LLMs know it verbatim; also in pyproject.toml
    "LICENSE",
    "debian/copyright",

    # Trivial / debhelper-generated one-liners
    "debian/source/format",
    "debian/changelog",
    "debian/ruqya-quran.postinst.debhelper",
    "debian/ruqya-quran.prerm.debhelper",

    # 4-line re-export wrapper
    "src/ruqya_quran/__main__.py",
}

BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".mp3",
    ".m4a",
    ".aac",
    ".ogg",
    ".wav",
    ".flac",
    ".pyc",
    ".pyo",
    ".qmlc",
    ".jsc",
    ".so",
    ".dylib",
    ".dll",
}

# ---------------------------------------------------------------
# Data-dir resolution
# ---------------------------------------------------------------

def _as_data_dir(p: Path) -> Path:
    """If p wraps a bundled data/ subfolder, descend into it."""
    if p.is_dir() and not (p / "VERSION").exists() and (p / "data" / "VERSION").exists():
        return p / "data"
    return p

def resolve_data_dir(root: Path) -> Path:
    """Find the bundled data folder for the DATA INVENTORY.

    Resolution order (first wins):
      1. third CLI argument     (python3 combine.py OUT MAX_KB DATADIR)
      2. RUQYA_DATA_ROOT env    (may point at the wrapper or at data/)
      3. examples/Ruqya/data inside the repo — may not exist;
         _render_data_inventory handles the missing case with a notice.
    """
    if len(sys.argv) > 3:
        return _as_data_dir(Path(sys.argv[3]).expanduser())
    env_root = os.environ.get("RUQYA_DATA_ROOT")
    if env_root:
        return _as_data_dir(Path(env_root).expanduser())
    return root / "examples" / "Ruqya" / "data"

# ---------------------------------------------------------------
# Repository scan
# ---------------------------------------------------------------

def repo_root() -> Path:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(r.stdout.strip())
    except (FileNotFoundError, subprocess.CalledProcessError):
        return Path.cwd()

def list_files(root: Path) -> list[Path]:
    """Files git considers part of the project: tracked + untracked-not-ignored."""
    r = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    out = []
    for line in r.stdout.splitlines():
        if not line:
            continue
        p = root / line
        if p.is_file():
            out.append(p)
    return out

# ---------------------------------------------------------------
# Tree rendering
# ---------------------------------------------------------------

def render_tree(
    root_name: str,
    included_rel: list[str],
    skipped_dir_counts: dict[str, int],
) -> str:
    """Build a small ASCII tree.

    `included_rel` — files that end up in combined.txt (rendered as leaves).
    `skipped_dir_counts` — prefix → number of files skipped under it
        (rendered as `<dir>/  [N files not shown]`).
    """
    tree: dict = {}

    def insert(parts: list[str], value) -> None:
        node = tree
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        if parts[-1] not in node:
            node[parts[-1]] = value

    for rel in included_rel:
        insert(rel.split("/"), None)

    for prefix, count in skipped_dir_counts.items():
        insert(prefix.rstrip("/").split("/"), ("[skipped]", count))

    lines = [f"{root_name}/"]

    def walk(node: dict, prefix: str) -> None:
        dirs = sorted(k for k, v in node.items() if isinstance(v, dict))
        markers = sorted(k for k, v in node.items() if not isinstance(v, dict) and v is not None)
        files = sorted(k for k, v in node.items() if not isinstance(v, dict) and v is None)

        items = ([(d, node[d], "dir") for d in dirs] + [(m, node[m], "marker")
                                                        for m in markers] + [(f, node[f], "file") for f in files])

        for i, (name, value, kind) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")

            if kind == "dir":
                lines.append(f"{prefix}{connector}{name}/")
                walk(value, child_prefix)
            elif kind == "marker":
                _, count = value
                marker = f"[{count} files not shown]" if count else "[not shown]"
                lines.append(f"{prefix}{connector}{name}/  {marker}")
            else:
                lines.append(f"{prefix}{connector}{name}")

    walk(tree, "")
    return "\n".join(lines)

# ---------------------------------------------------------------
# Data inventory (one sample entry per JSON file in the data dir)
# ---------------------------------------------------------------

def _sample_json(path: Path, max_chars: int = 800) -> str:
    """Return one representative entry from a JSON file, compacted.

    For dicts: `to_entries[0]` — first key/value pair.
    For lists: first element.
    Truncates at `max_chars` so a huge first value doesn't dominate.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"// (unreadable: {e})"

    if isinstance(data, dict) and data:
        key = next(iter(data))
        try:
            dumped = json.dumps({key: data[key]}, ensure_ascii=False)
        except Exception as e:
            return f"// (unserializable: {e})"
        if len(dumped) > max_chars:
            dumped = dumped[:max_chars] + " …}"
        return dumped

    if isinstance(data, list) and data:
        try:
            dumped = json.dumps([data[0]], ensure_ascii=False)
        except Exception as e:
            return f"// (unserializable: {e})"
        if len(dumped) > max_chars:
            dumped = dumped[:max_chars] + " …]"
        return dumped

    try:
        return json.dumps(data, ensure_ascii=False)[:max_chars]
    except Exception as e:
        return f"// (unserializable: {e})"

def _walk_data_dir(data_root: Path) -> tuple[dict, list]:
    """Return (audio_by_reciter, other_files).

    audio_by_reciter: {reciter: [(path, size), ...]}
    other_files:      [(rel_path, path, size), ...] — everything except audio/
    """
    audio: dict[str, list] = {}
    other: list = []
    for p in sorted(data_root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(data_root).as_posix()
        parts = rel.split("/")
        size = p.stat().st_size
        if len(parts) >= 2 and parts[0] == "audio":
            audio.setdefault(parts[1], []).append((p, size))
        else:
            other.append((rel, p, size))
    return audio, other

def _render_data_inventory(data_root: Path, display_name: str) -> list[str]:
    """Build the DATA INVENTORY lines for combined.txt."""
    lines: list[str] = []

    if not data_root.exists():
        lines.append(f"// (data folder not present: {display_name}/)")
        lines.append("// Fresh checkout — run 'make init' then 'make bundle-fast'")
        lines.append("// for JSON only, or 'make bundle' for JSON + audio, after")
        lines.append("// populating tools/raw/. See docs/DATA-SCHEMA.md for the")
        lines.append("// full contract.")
        return lines

    audio, other = _walk_data_dir(data_root)

    lines.append(f"// {display_name}/")
    for rel, p, size in other:
        if p.suffix == ".json" or p.name == "VERSION":
            lines.append(f"//   {rel}  ({size:,} B)")
    if audio:
        lines.append("//   audio/")
        for rid in sorted(audio):
            entries = audio[rid]
            total = sum(sz for _, sz in entries)
            lines.append(f"//     {rid}/  ({len(entries):,} files, {total:,} B)")
    lines.append("")

    for rel, p, size in other:
        if p.suffix != ".json":
            continue
        lines.append(f"// --- {rel}  (first entry; {size:,} B total) ---")
        sample = _sample_json(p)
        for raw in sample.splitlines():
            lines.append("// " + raw)
        lines.append("")

    for rel, p, size in other:
        if p.name != "VERSION":
            continue
        lines.append(f"// --- {rel}  (full) ---")
        try:
            content = p.read_text(encoding="utf-8")
        except Exception as e:
            lines.append(f"// (unreadable: {e})")
            lines.append("")
            break
        for raw in content.splitlines():
            lines.append("// " + raw)
        lines.append("")
        break

    return lines

# ---------------------------------------------------------------
# Content ordering
# ---------------------------------------------------------------

def content_sort_key(rel: str) -> tuple:
    """Priority files first in fixed order; everything else alphabetically."""
    if rel in PRIORITY:
        return (0, PRIORITY.index(rel))
    return (1, rel)

# ---------------------------------------------------------------
# Line-tracking writer
# ---------------------------------------------------------------

class _LineWriter:
    """Tracks the current 1-based line number as text is written.

    Every `write()` advances `line` by the number of `\\n` characters it
    received. After the file is complete, `line - 1` equals the total
    number of newlines written — i.e. `wc -l`.
    """

    def __init__(self, fout):
        self.fout = fout
        self.line = 1

    def write(self, s: str) -> None:
        self.fout.write(s)
        self.line += s.count("\n")

# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def main() -> None:
    root = repo_root()
    files = list_files(root)

    included: list[tuple[str, str]] = []
    skipped_dir_counts: dict[str, int] = {}
    skipped = 0

    for path in files:
        rel = path.relative_to(root).as_posix()

        if rel in SKIP_PATHS:
            skipped += 1
            continue

        matched_prefix = next((p for p in SKIP_PREFIXES if rel.startswith(p)), None)
        if matched_prefix is not None:
            skipped_dir_counts[matched_prefix] = skipped_dir_counts.get(matched_prefix, 0) + 1
            skipped += 1
            continue

        if path.suffix in BINARY_SUFFIXES:
            skipped += 1
            continue

        size = path.stat().st_size
        if rel != SELF_PATH and size > MAX_KB * 1024:
            print(f"SKIP (size {size // 1024} KB): {rel}", file=sys.stderr)
            skipped += 1
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"SKIP ({e}): {rel}", file=sys.stderr)
            skipped += 1
            continue

        included.append((rel, content))

    # Context-first: split out the script, then sort the remainder.
    self_pairs = [(r, c) for r, c in included if r == SELF_PATH]
    other_pairs = sorted(
        ((r, c) for r, c in included if r != SELF_PATH),
        key=lambda pair: content_sort_key(pair[0]),
    )

    # (relative path, line count of that source file)
    file_counts: list[tuple[str, int]] = []
    total_lines = 0

    def emit(w: "_LineWriter", rel: str, content: str) -> None:
        # Normalise trailing newline so the count and the written bytes
        # agree: `body.count("\n")` == `wc -l` of the emitted block.
        body = content if content.endswith("\n") else content + "\n"
        file_counts.append((rel, body.count("\n")))
        w.write(f"// ===== FILE: {rel} =====\n")
        w.write(body)
        w.write("\n")

    local_data = (root / "examples/Ruqya/data").resolve()
    data_root = resolve_data_dir(root)
    data_display = ("examples/Ruqya/data" if data_root.resolve() == local_data else str(data_root))

    with open(OUT, "w", encoding="utf-8") as fout:
        w = _LineWriter(fout)

        # 1. The tool first, so the reader sees how the dump was built.
        for rel, content in self_pairs:
            emit(w, rel, content)

        # 2. Tree of everything else.
        w.write("// ===== PROJECT TREE =====\n")
        w.write("// tools/combine.py (the script that produced this dump)\n")
        w.write("// appears first, above this tree. Every other file listed\n")
        w.write("// below appears verbatim later in the dump.\n")
        w.write("// Folders marked [N files not shown] are tracked in git but\n")
        w.write("// intentionally excluded (bulk data, OpenAPI spec, boilerplate,\n")
        w.write("// reference tables that duplicate code).\n")
        w.write(render_tree(root.name, [r for r, _ in included], skipped_dir_counts))
        w.write("\n\n")

        # 3. Data inventory — one sample entry per JSON file so the reader
        #    sees the schema without the bulk. This is ground truth; if the
        #    static doc (docs/DATA-SCHEMA.md) disagrees, this wins.
        w.write("// ===== DATA INVENTORY =====\n")
        w.write(f"// The bundled data folder: {data_display}\n")
        w.write("// Excluded from the main tree above (bulk audio); shown here\n")
        w.write("// as a file tree plus one representative entry per JSON file,\n")
        w.write("// so you can see the exact schema without downloading 2.5 GB.\n")
        w.write("// Sample shape is 'to_entries[0]' — first key/value pair —\n")
        w.write("// truncated to 800 chars. Contract: docs/DATA-SCHEMA.md.\n")
        for line in _render_data_inventory(data_root, data_display):
            w.write(line + "\n")
        w.write("\n")

        # 4. Reading-order comment, then the rest.
        w.write("// ===== READING ORDER =====\n")
        w.write("// docs/KNOWN-NON-ISSUES.md lists behaviors that look wrong\n")
        w.write("// but are intentional — read it before flagging anything.\n")
        w.write("// docs/DATA-SCHEMA.md is the data folder contract — the schema\n")
        w.write("// that DataStore in main.py reads. The DATA INVENTORY above is\n")
        w.write("// ground truth; if the doc and the samples disagree, trust the\n")
        w.write("// samples (schema has drifted, doc needs updating).\n")
        w.write("// README.md explains what the project is and the playlist format.\n")
        w.write("// docs/INSTALL.md explains deployment, MIME registration, and\n")
        w.write("// troubleshooting. Everything else follows alphabetically.\n\n")

        for rel, content in other_pairs:
            emit(w, rel, content)

        total_lines = w.line - 1

    actual = OUT.stat().st_size
    print(f"Wrote {OUT}: {len(included)} files, {total_lines} lines, "
          f"{actual // 1024} KB (skipped {skipped})")
    if file_counts:
        print()
        for rel, n in file_counts:
            print(f"{rel} ({n})")

    if actual > 200_000:
        print(f"WARNING: {OUT} is {actual // 1024} KB — may be large "
              f"for some LLMs", file=sys.stderr)
        print(f"  Tip: python3 {sys.argv[0]} {OUT} 100   "
              f"# skip files >100 KB", file=sys.stderr)

if __name__ == "__main__":
    main()
