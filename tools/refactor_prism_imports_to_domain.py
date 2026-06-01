#!/usr/bin/env python3
"""Rewrite casa/*.py imports: prism_state → prism_ids + prism_wire."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.domain import prism_ids as ids_mod
from casa.domain import prism_wire as wire_mod

_ID_NAMES = {
    n
    for n in dir(ids_mod)
    if n.isupper() and not n.startswith("_")
}
_WIRE_NAMES = {
    n
    for n in dir(wire_mod)
    if not n.startswith("_") and callable(getattr(wire_mod, n, None)) is False
}
_WIRE_NAMES = {n for n in dir(wire_mod) if not n.startswith("_") and n[0].islower()}


def _split_names(names: list[str]) -> tuple[list[str], list[str]]:
    id_part: list[str] = []
    wire_part: list[str] = []
    for n in names:
        if n in _ID_NAMES:
            id_part.append(n)
        elif n in _WIRE_NAMES or n in ("_ACTIVE", "_ACTIVE_CONTROL"):
            wire_part.append(n)
        else:
            wire_part.append(n)
    return id_part, wire_part


def refactor_file(path: Path) -> bool:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    changed = False
    for node in reversed(tree.body):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "casa.prisms.shared.prism_state":
            continue
        names = [alias.name for alias in node.names]
        id_part, wire_part = _split_names(names)
        start, end = node.lineno - 1, node.end_lineno
        indent = lines[start][: len(lines[start]) - len(lines[start].lstrip())]
        new_lines: list[str] = []
        if id_part:
            new_lines.append(f"{indent}from casa.domain.prism_ids import {', '.join(id_part)}\n")
        if wire_part:
            new_lines.append(f"{indent}from casa.domain.prism_wire import {', '.join(wire_part)}\n")
        if not new_lines:
            continue
        lines[start:end] = new_lines
        changed = True
    if changed:
        path.write_text("".join(lines), encoding="utf-8")
    return changed


def main() -> None:
    root = _REPO / "casa"
    n = 0
    for path in sorted(root.rglob("*.py")):
        if refactor_file(path):
            n += 1
            print(path.relative_to(_REPO))
    print(f"updated {n} files")


if __name__ == "__main__":
    main()
