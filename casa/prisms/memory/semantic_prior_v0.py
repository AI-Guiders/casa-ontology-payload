#!/usr/bin/env python3
"""Optional semantic priors for preview/T9 (entity taxonomy, off by default on hot path)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.entity_taxonomy_lookup_v0 import taxonomy_bonus
from casa.prisms.memory.pos_lookup_v0 import word_pos


def preview_semantic_bonus(
    state: dict | None,
    word: str,
    *,
    lang: str | None = None,
    enable_taxonomy: bool = True,
    enable_pos: bool = False,
    prefer_pos: str | None = None,
) -> float:
    """
    Sleep/L3 priors for merged preview scoring — not used in predict_t9 v0 hot path.

    ``enable_pos`` + ``prefer_pos`` (e.g. pos.noun): small boost when POS matches.
    """
    if state is None:
        return 0.0
    bonus = 0.0
    if enable_taxonomy:
        bonus += taxonomy_bonus(state, word)
    if enable_pos and prefer_pos:
        got = word_pos(state, word).get("pos")
        if got == prefer_pos:
            bonus += 6.0
    return bonus
