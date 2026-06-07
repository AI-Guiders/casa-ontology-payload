#!/usr/bin/env python3
"""Deprecated: use bootstrap_agent_self_tier or restore_agent_life."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

warnings.warn(
    "init_agent_self is deprecated — use tools/restore_agent_life.py (snapshot) "
    "or tools/bootstrap_agent_self_tier.py (Self tier only)",
    DeprecationWarning,
    stacklevel=1,
)

from casa.cli.bootstrap_agent_self_tier import main

if __name__ == "__main__":
    main()
