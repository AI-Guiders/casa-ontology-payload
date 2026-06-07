#!/usr/bin/env python3
"""Bootstrap Self tier (journal + agent/) — not full life restore."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.cli.bootstrap_agent_self_tier import main

if __name__ == "__main__":
    main()
