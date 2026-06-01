#!/usr/bin/env python3
"""CLI: init Self tier (journal workbook + agent/) for von-neumann."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.cli.init_agent_self import main

if __name__ == "__main__":
    main()
