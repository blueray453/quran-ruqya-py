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
  4. Emits docs/KNOWN-NON-ISSUES.md first (so the reader knows what
     *not* to flag), then README.md, then docs/INSTALL.md, then each
     remaining file alphabetically, with a `// ===== FILE: path =====`
     header.
  5. Prints, to stdout, the total line count of the finished combined.txt
     and the line count of every emitted source file (i.e. its `wc -l`,
     not its position inside combined.txt).

Usage:
    python3 tools/combine.py                 # → combined.txt
    python3 tools/combine.py out.txt         # custom name
    python3 tools/combine.py combined.txt 100  # skip files > 100 KB
"""

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
# it reads any source.
PRIORITY = [
    "docs/KNOWN-NON-ISSUES.md",
    "README.md",
    "docs/INSTALL.md",
]

# Directories whose contents are tracked in git but not useful as LLM
# context. Collapsed to a marker in the tree.
SKIP_PREFIXES = (
    "examples/Ruqya/data/",  # bulk audio, text, words, clips
)

# Exact relative paths dropped silently — no tree marker, no content.
SKIP_PATHS = {
    # Meta: this script's output (the script itself is emitted up top)
    "combined.txt",

    # Full alquran.cloud OpenAPI spec — app uses only 2 endpoints, both
    # spelled out in main.py. ~1400 lines of mostly-irrelevant API schema.
    "docs/API.txt",

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

        # 3. Reading-order comment, then the rest.
        w.write("// ===== READING ORDER =====\n")
        w.write("// docs/KNOWN-NON-ISSUES.md lists behaviors that look wrong\n")
        w.write("// but are intentional — read it before flagging anything.\n")
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
