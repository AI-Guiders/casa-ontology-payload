#!/usr/bin/env python3
"""Deprecated: use scripts/generate_cli_modules.py."""

from __future__ import annotations

import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_cli_modules import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
