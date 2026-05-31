#!/usr/bin/env python3
"""Pre-publish guard: fail if any git-tracked file embeds an absolute machine path.

Catches leaks like ``C:\\Users\\...`` or ``D:\\Experiments\\...`` in tracked
manifests, reports and logs before the repo is pushed public.

    python scripts/check_no_abs_paths.py

Exit code 0 = clean, 1 = leaks found (printed as ``path:line``).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Drive-letter path into a typical user/workspace root. ``\\\\?`` matches one or
# two literal backslashes (JSON-escaped paths store two), and ``/`` covers posix
# mirrors of the same leak.
LEAK_RE = re.compile(r"[A-Za-z]:[\\/]{1,2}(?:Users|Experiments|Windows|Program)", re.IGNORECASE)


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=str(ROOT), capture_output=True, text=True, check=True
    )
    return [line for line in out.stdout.splitlines() if line]


def main() -> int:
    hits: list[str] = []
    for rel in tracked_files():
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable
        for i, line in enumerate(text.splitlines(), start=1):
            if LEAK_RE.search(line):
                hits.append(f"{rel}:{i}")

    if hits:
        print(f"Absolute machine paths in {len(hits)} tracked location(s):", file=sys.stderr)
        for h in hits:
            print(f"  {h}", file=sys.stderr)
        return 1
    print("OK: no absolute machine paths in tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
