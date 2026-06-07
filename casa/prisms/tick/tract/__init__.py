"""Tract competition — intent = winning F-tract on field (ADR-0052)."""

from __future__ import annotations

from casa.prisms.tick.tract.competition import compete_tract_intent
from casa.prisms.tick.tract.geometry import geometry_signals
from casa.prisms.tick.tract.model import (
    TRACT_IDS,
    TractScore,
    _BOOTSTRAP_TRACT_CLAIMS,
    parse_math_ops,
    parse_stick_runs,
)

__all__ = [
    "TRACT_IDS",
    "TractScore",
    "_BOOTSTRAP_TRACT_CLAIMS",
    "compete_tract_intent",
    "geometry_signals",
    "parse_math_ops",
    "parse_stick_runs",
]
