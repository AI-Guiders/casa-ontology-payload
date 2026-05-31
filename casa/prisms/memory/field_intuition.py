#!/usr/bin/env python3
"""Intuition from cylinder: competing H: hypotheses + R: votes."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.field_decode import active_rule_from_field


def segment_field_intuition(state: dict, word: str) -> dict[str, Any]:
    from casa.prisms.memory.field_hypotheses import compete_hypotheses

    return compete_hypotheses(state, word)
