#!/usr/bin/env python3
"""CLI shim: boot immutable core (alphabet, syllables, keyboard) into agents/von-neumann."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.cli.boot_agent_core import main

if __name__ == "__main__":
    main()
