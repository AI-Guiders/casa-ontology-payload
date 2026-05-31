#!/usr/bin/env python3
"""Rewrite legacy flat imports in casa/ → casa.* module paths (M4)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "casa" / "cli" / "legacy_manifest.json"
CASA = ROOT / "casa"

STDLIB = frozenset(
    {
        "__future__",
        "abc",
        "argparse",
        "collections",
        "dataclasses",
        "datetime",
        "functools",
        "importlib",
        "json",
        "os",
        "pathlib",
        "re",
        "shutil",
        "struct",
        "subprocess",
        "sys",
        "tempfile",
        "typing",
        "unicodedata",
        "unittest",
        "zlib",
    }
)

FROM_RE = re.compile(r"^(\s*)from ([a-zA-Z0-9_]+) import (.+)$")
IMPORT_AS_RE = re.compile(r"^(\s*)import ([a-zA-Z0-9_]+) as ([a-zA-Z0-9_]+)\s*(#.*)?$")
IMPORT_RE = re.compile(r"^(\s*)import ([a-zA-Z0-9_]+)\s*(#.*)?$")


def load_manifest() -> dict[str, str]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def rewrite_line(line: str, manifest: dict[str, str]) -> str:
    m = FROM_RE.match(line)
    if m:
        indent, mod, rest = m.groups()
        if mod in STDLIB or mod.startswith("casa"):
            return line
        if mod not in manifest:
            return line
        cleaned = rest.replace("  # type: ignore", "").replace(" # type: ignore", "")
        return f"{indent}from {manifest[mod]} import {cleaned}"
    m = IMPORT_AS_RE.match(line)
    if m:
        indent, mod, alias, comment = m.groups()
        if mod in STDLIB or mod.startswith("casa") or mod not in manifest:
            return line
        casa_mod = manifest[mod]
        parent, short = casa_mod.rsplit(".", 1)
        tail = comment or ""
        return f"{indent}from {parent} import {short} as {alias}{tail}"
    m = IMPORT_RE.match(line)
    if m:
        indent, mod, comment = m.groups()
        if mod in STDLIB or mod.startswith("casa") or mod not in manifest:
            return line
        tail = comment or ""
        return f"{indent}import {manifest[mod]}{tail}"
    return line


def main() -> int:
    if not MANIFEST.is_file():
        print("run generate_legacy_manifest.py first", file=sys.stderr)
        return 1
    manifest = load_manifest()
    changed = 0
    for path in sorted(CASA.rglob("*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        new_lines = [rewrite_line(ln, manifest) for ln in lines]
        if new_lines != lines:
            path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            changed += 1
    print(f"updated {changed} files under casa/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
