#!/usr/bin/env python3
"""Cursor agent client for Neumann duplex wire — one command per turn, life stays up."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    cmd = [sys.executable, "-m", "casa.cli", "partner_agent_wire", *args]
    proc = subprocess.run(cmd, cwd=str(_REPO))
    return int(proc.returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
