#!/usr/bin/env python3
"""CI gate: legacy manifest complete; casa/ uses casa.* imports only (M4)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "casa" / "cli" / "legacy_manifest.json"
CASA = ROOT / "casa"
TOOLS = ROOT / "tools"

FROM_LEGACY = re.compile(r"^from ([a-z_][a-z0-9_]*) import")
IMPORT_LEGACY = re.compile(r"^import ([a-z_][a-z0-9_]*)")


def check_manifest() -> list[str]:
    errors: list[str] = []
    if not MANIFEST.is_file():
        return ["missing casa/cli/legacy_manifest.json"]
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if len(data) < 200:
        errors.append(f"manifest too small: {len(data)} entries")
    return errors


def check_no_legacy_shims() -> list[str]:
    errors: list[str] = []
    for path in TOOLS.glob("*.py"):
        if path.name in ("run.py",):
            continue
        errors.append(f"tools/{path.name}: remove shim (use python -m casa.cli {path.stem})")
    return errors


def check_casa_imports(manifest: dict[str, str]) -> list[str]:
    errors: list[str] = []
    legacy_names = set(manifest)
    for py in CASA.rglob("*.py"):
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            for pat in (FROM_LEGACY, IMPORT_LEGACY):
                m = pat.match(line.strip())
                if not m:
                    continue
                mod = m.group(1)
                if mod in legacy_names or mod.startswith("sss_"):
                    errors.append(f"{py.relative_to(ROOT)}:{i}: legacy import {mod!r}")
    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--allow-tools-shims", action="store_true", help="Deprecated M2 shims still present")
    args = p.parse_args()
    errors = check_manifest()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    errors.extend(check_casa_imports(manifest))
    if not args.allow_tools_shims:
        errors.extend(check_no_legacy_shims())
    if errors:
        for e in errors[:50]:
            print(e, file=sys.stderr)
        if len(errors) > 50:
            print(f"... and {len(errors) - 50} more", file=sys.stderr)
        return 1
    print(f"M4 layout OK (manifest {len(manifest)} modules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
