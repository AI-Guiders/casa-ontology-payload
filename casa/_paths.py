"""Repo root + tools/ on sys.path for incremental M2 migration."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"


def ensure_import_paths() -> None:
    for p in (REPO_ROOT, TOOLS_DIR):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
