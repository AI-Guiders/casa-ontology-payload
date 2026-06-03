"""Первый import в runner: visual-curriculum + repo на sys.path."""

import sys
from pathlib import Path

_vc = Path(__file__).resolve().parents[1]
_repo = _vc.parents[1]
for entry in (_repo, _vc):
    s = str(entry)
    if s not in sys.path:
        sys.path.insert(0, s)
