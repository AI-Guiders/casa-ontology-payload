#!/usr/bin/env python3
"""Build casa/cli/cli_modules.json — CLI name → casa module (modules with main())."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASA = ROOT / "casa"
OUT = ROOT / "casa" / "cli" / "cli_modules.json"


def has_main(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return True
    return False


def module_id(path: Path) -> str:
    rel = path.relative_to(CASA).with_suffix("")
    return "casa." + ".".join(rel.parts)


def main() -> int:
    manifest: dict[str, str] = {}
    collisions: dict[str, list[str]] = {}
    for path in sorted(CASA.rglob("*.py")):
        if path.name.startswith("_"):
            continue
        if not has_main(path):
            continue
        stem = path.stem
        mod = module_id(path)
        if stem in manifest and manifest[stem] != mod:
            collisions.setdefault(stem, []).append(mod)
            continue
        manifest[stem] = mod
    if collisions:
        for stem, mods in collisions.items():
            print(f"collision {stem}: {manifest[stem]} vs {mods}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest)} entries → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
