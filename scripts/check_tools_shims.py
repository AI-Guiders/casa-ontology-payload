#!/usr/bin/env python3
"""CI gate: tools/*.py must be M2 shims (sys.modules alias to casa.*)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

SHIM_MARK = re.compile(r'^"""Shim → casa\.', re.M)
IMPORT_MOD = re.compile(r"import_module\([\"']casa\.")

SKIP = frozenset({"_shim_v0.py", "README.md"})


def check_tools() -> list[str]:
    errors: list[str] = []
    for path in sorted(TOOLS.glob("*.py")):
        if path.name in SKIP:
            continue
        text = path.read_text(encoding="utf-8")
        if not SHIM_MARK.search(text):
            errors.append(f"{path.name}: missing shim header")
            continue
        if not IMPORT_MOD.search(text):
            errors.append(f"{path.name}: missing import_module('casa....')")
        if "ensure_import_paths()" in text and "def " in text.split("ensure_import_paths()")[-1][:200]:
            errors.append(f"{path.name}: looks like implementation, not shim")
    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--strict-casa-imports", action="store_true", help="Future M4: casa/ must not import legacy tools names")
    args = p.parse_args()
    errors = check_tools()
    if args.strict_casa_imports:
        legacy = re.compile(r"from (sss_|store_layout_v0|field_write) ")
        for py in (ROOT / "casa").rglob("*.py"):
            for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if legacy.search(line) and "type: ignore" not in line:
                    errors.append(f"{py.relative_to(ROOT)}:{i}: legacy import (M4)")
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print(f"tools shims OK ({len(list(TOOLS.glob('*.py')))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
