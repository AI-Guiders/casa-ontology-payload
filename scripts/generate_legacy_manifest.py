#!/usr/bin/env python3
"""Build casa/cli/legacy_manifest.json from tools/ shims (run before M4 shim removal)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
OUT = ROOT / "casa" / "cli" / "legacy_manifest.json"

IMPORT_MOD = re.compile(r'import_module\(["\'](casa\.[^"\']+)["\']')
SKIP = frozenset({"_shim_v0.py", "run.py", "README.md"})


def main() -> int:
    manifest: dict[str, str] = {}
    for path in sorted(TOOLS.glob("*.py")):
        if path.name in SKIP:
            continue
        text = path.read_text(encoding="utf-8")
        m = IMPORT_MOD.search(text)
        if not m:
            print(f"missing casa target: {path.name}", file=sys.stderr)
            return 1
        manifest[path.stem] = m.group(1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest)} entries → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
