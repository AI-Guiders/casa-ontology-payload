#!/usr/bin/env python3
"""Strip _v0 / -v0 / .v0. noise from casa modules, design assets, lab paths."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_PARTS = {".git", ".pytest_cache", "__pycache__", "node_modules"}
TEXT_GLOBS = ("*.py", "*.md", "*.json", "*.toml", "*.yml", "*.yaml", "*.ps1", "*.sh")


def _skip(path: Path) -> bool:
    return any(p in SKIP_PARTS for p in path.parts)


def _new_name(name: str) -> str | None:
    if name.endswith("_v0.py"):
        return name[:-6] + ".py"
    if name.endswith("-v0.md"):
        return name[:-6] + ".md"
    if name == "stack.json":
        return "stack.json"
    if name == "stack.toml":
        return "stack.toml"
    if ".schema.json" in name:
        return name.replace(".schema.json", ".schema.json")
    if name.endswith(".json"):
        return name[:-8] + ".json"
    if name.endswith(".toml"):
        return name[:-8] + ".toml"
    return None


def collect_file_renames() -> list[tuple[Path, Path]]:
    moves: list[tuple[Path, Path]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or _skip(path):
            continue
        new_name = _new_name(path.name)
        if not new_name or new_name == path.name:
            continue
        dest = path.with_name(new_name)
        if dest.exists():
            raise SystemExit(f"collision: {path.relative_to(ROOT)} → {dest.name} (exists)")
        moves.append((path, dest))
    return moves


def collect_dir_renames() -> list[tuple[Path, Path]]:
    dirs: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_dir() or _skip(path):
            continue
        if path.name.endswith("_v0") or path.name.endswith("-v0"):
            dirs.append(path)
    moves: list[tuple[Path, Path]] = []
    for path in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        if path.name.endswith("_v0"):
            dest = path.with_name(path.name.removesuffix("_v0"))
        else:
            dest = path.with_name(path.name.removesuffix("-v0"))
        if dest.exists():
            raise SystemExit(f"dir collision: {path.relative_to(ROOT)}")
        moves.append((path, dest))
    return moves


def module_path(py: Path) -> str:
    rel = py.relative_to(ROOT / "casa").with_suffix("")
    return "casa." + ".".join(rel.parts)


def build_replace_map(
    file_moves: list[tuple[Path, Path]],
    dir_moves: list[tuple[Path, Path]],
) -> dict[str, str]:
    repl: dict[str, str] = {}

    for old, new in file_moves:
        orel = old.relative_to(ROOT).as_posix()
        nrel = new.relative_to(ROOT).as_posix()
        repl[orel] = nrel
        repl[old.as_posix()] = new.as_posix()
        if old.suffix == ".py" and old.parts[0] == "casa":
            repl[module_path(old)] = module_path(new)

    for old, new in dir_moves:
        orel = old.relative_to(ROOT).as_posix()
        nrel = new.relative_to(ROOT).as_posix()
        repl[orel] = nrel

    # CLI stems and bare module stems (longest first via sort)
    stems: set[str] = set()
    for old, new in file_moves:
        if old.suffix == ".py":
            stems.add(old.stem)
            repl[old.stem] = new.stem

    for old, new in dir_moves:
        repl[old.name] = new.name

    return repl


def rewrite_text(content: str, repl: dict[str, str]) -> str:
    for old, new in sorted(repl.items(), key=lambda x: -len(x[0])):
        content = content.replace(old, new)
    # path-ish -v0 segments (stores, docs already covered by file map)
    content = re.sub(r"([a-z0-9]+)-v0\b", r"\1", content)
    content = re.sub(r"([a-z0-9]+)_v0\b", r"\1", content)
    return content


def rewrite_tree(repl: dict[str, str]) -> int:
    changed = 0
    for pattern in TEXT_GLOBS:
        for path in ROOT.rglob(pattern):
            if not path.is_file() or _skip(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            new_text = rewrite_text(text, repl)
            if new_text != text:
                path.write_text(new_text, encoding="utf-8")
                changed += 1
    return changed


def apply_renames(moves: list[tuple[Path, Path]]) -> None:
    for old, new in sorted(moves, key=lambda x: -len(x[0].parts)):
        new.parent.mkdir(parents=True, exist_ok=True)
        old.rename(new)
        print(f"  {old.relative_to(ROOT)} → {new.relative_to(ROOT)}")


def main() -> int:
    file_moves = collect_file_renames()
    dir_moves = collect_dir_renames()
    print(f"file renames: {len(file_moves)}")
    print(f"dir renames: {len(dir_moves)}")

    repl = build_replace_map(file_moves, dir_moves)
    n = rewrite_tree(repl)
    print(f"rewrote {n} text files")
    apply_renames(file_moves)
    apply_renames(dir_moves)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
