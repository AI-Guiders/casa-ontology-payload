#!/usr/bin/env python3
"""Second pass: strip leftover .v0. in path strings; fix stack defaults."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", ".pytest_cache", "__pycache__"}
GLOBS = ("*.py", "*.md", "*.json", "*.toml", "*.ps1", "*.sh", "*.jsonl")
STACK_DEFAULT = "design/prisms/memory/stack.json"
CONTROL_STACK = "design/control-lattice-stack.toml"


def skip(path: Path) -> bool:
    return any(p in SKIP for p in path.parts)


def rewrite(content: str) -> str:
    content = content.replace(".jsonl", ".jsonl")
    content = content.replace(".json", ".json")
    content = content.replace(".toml", ".toml")
    content = content.replace(".schema.json", ".schema.json")
    content = re.sub(r"design/sss-lattice-stack\.json", STACK_DEFAULT, content)
    content = re.sub(
        r"sss-lattice-stack\.json",
        "prisms/memory/stack.json",
        content,
    )
    content = content.replace("layered-ca-phases.json", "layered-ca-phases.json")
    content = content.replace("layout.json", "layout.json")
    content = re.sub(r"([a-z0-9]+)-v0(?=[/\"'\\])", r"\1", content)
    return content


def main() -> int:
    n = 0
    for pattern in GLOBS:
        for path in ROOT.rglob(pattern):
            if not path.is_file() or skip(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            new = rewrite(text)
            if new != text:
                path.write_text(new, encoding="utf-8")
                n += 1
    # rename scripts still suffixed
    for path in list((ROOT / "scripts").glob("*_v0.ps1")):
        dest = path.with_name(path.stem.removesuffix("_v0") + ".ps1")
        if not dest.exists():
            path.rename(dest)
            print(f"rename {path.name} → {dest.name}")
    print(f"pass2 rewrote {n} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
