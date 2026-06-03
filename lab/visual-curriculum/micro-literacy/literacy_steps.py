"""Совместимость: используй ../lex_steps.py."""

from __future__ import annotations

import sys
from pathlib import Path

_vc = Path(__file__).resolve().parents[1]
if str(_vc) not in sys.path:
    sys.path.insert(0, str(_vc))

from lex_steps import lex_step

__all__ = ["lex_step"]
