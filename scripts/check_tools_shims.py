#!/usr/bin/env python3
"""CI gate: casa layout — cli_modules.json, no tools shims, no sss_* imports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ROOT / "casa" / "cli" / "cli_modules.json"
CASA = ROOT / "casa"
TOOLS = ROOT / "tools"

FROM_LEGACY = re.compile(r"^from ([a-z_][a-z0-9_]*) import")
IMPORT_LEGACY = re.compile(r"^import ([a-z_][a-z0-9_]*)")


def check_modules() -> list[str]:
    errors: list[str] = []
    if not MODULES.is_file():
        return ["missing casa/cli/cli_modules.json — run scripts/generate_cli_modules.py"]
    data = json.loads(MODULES.read_text(encoding="utf-8"))
    if len(data) < 150:
        errors.append(f"cli_modules too small: {len(data)} entries")
    return errors


def check_no_tools_shims() -> list[str]:
    errors: list[str] = []
    for path in TOOLS.glob("*.py"):
        if path.name in ("run.py",):
            continue
        errors.append(f"tools/{path.name}: remove shim (use python -m casa.cli {path.stem})")
    return errors


def check_casa_imports() -> list[str]:
    errors: list[str] = []
    for py in CASA.rglob("*.py"):
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            for pat in (FROM_LEGACY, IMPORT_LEGACY):
                m = pat.match(line.strip())
                if not m:
                    continue
                mod = m.group(1)
                if mod.startswith("sss_"):
                    errors.append(f"{py.relative_to(ROOT)}:{i}: legacy import {mod!r}")
    return errors


def check_no_sss_filenames() -> list[str]:
    errors: list[str] = []
    for py in CASA.rglob("sss_*.py"):
        errors.append(f"{py.relative_to(ROOT)}: rename sss_* module")
    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--allow-tools-shims", action="store_true")
    args = p.parse_args()
    errors = check_modules()
    errors.extend(check_casa_imports())
    errors.extend(check_no_sss_filenames())
    if not args.allow_tools_shims:
        errors.extend(check_no_tools_shims())
    if errors:
        for e in errors[:50]:
            print(e, file=sys.stderr)
        if len(errors) > 50:
            print(f"... and {len(errors) - 50} more", file=sys.stderr)
        return 1
    manifest = json.loads(MODULES.read_text(encoding="utf-8"))
    print(f"casa layout OK ({len(manifest)} CLI modules, canonical paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
