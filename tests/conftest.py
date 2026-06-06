"""Pytest path for lab/visual-curriculum modules (teacher_pedagogy, probe_infra)."""

from __future__ import annotations

import sys
from pathlib import Path

_CURRICULUM = Path(__file__).resolve().parents[1] / "lab" / "visual-curriculum"
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))
