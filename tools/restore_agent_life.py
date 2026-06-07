#!/usr/bin/env python3
"""Restore trained agent life from life-archive snapshot."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.cli.restore_agent_life import main

if __name__ == "__main__":
    raise SystemExit(main())
