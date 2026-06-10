#!/usr/bin/env python3
"""Denial — dampen threat-linked tracts before bind (ADR-0074 P19b)."""

from __future__ import annotations

from typing import Any

from casa.prisms.defense.core import defense_block, limbic_denial_active, query_has_threat_cue
from casa.prisms.tick.tract.model import TractScore


def apply_denial_tract_adjustment(
    scores: dict[str, TractScore],
    query: str,
    state: dict | None,
) -> dict[str, Any]:
    """Lower recall/explain when limbic denial band + threat cue in query."""
    if state is None or not limbic_denial_active(state):
        return {"active": False}
    if not query_has_threat_cue(query):
        return {"active": False, "reason": "no_threat_cue"}

    damp = {"recall": 18, "explain": 12, "journal": 10}
    boost = {"social": 10, "general": 6}
    touched: list[str] = []
    for tract_id, delta in damp.items():
        if tract_id in scores and delta:
            scores[tract_id].score = max(0, scores[tract_id].score - delta)
            scores[tract_id].sources.append("defense:denial_damp")
            touched.append(f"damp:{tract_id}")
    for tract_id, delta in boost.items():
        if tract_id in scores and delta:
            scores[tract_id].score += delta
            scores[tract_id].sources.append("defense:denial_redirect")
            touched.append(f"boost:{tract_id}")

    rep = {"active": True, "mechanism": "denial", "touched": touched}
    defense_block(state)["denial_last"] = rep
    return rep
