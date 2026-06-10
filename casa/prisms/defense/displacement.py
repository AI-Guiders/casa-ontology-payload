#!/usr/bin/env python3
"""Displacement — redirect bind to safer proxy domains (ADR-0074 P19c)."""

from __future__ import annotations

from typing import Any

from casa.prisms.defense.core import (
    defense_block,
    limbic_displacement_active,
    text_has_threat_cue,
)


def apply_displacement_block_deltas(
    blocks: list[dict[str, Any]],
    *,
    query: str,
    intent: str,
    state: dict,
) -> dict[str, Any]:
    """Threat journal blocks ↓; math/logical/grammar proxy blocks ↑."""
    if not limbic_displacement_active(state):
        return {"active": False}

    journal_damp = 0
    proxy_boost = 0
    for block in blocks:
        cid = str(block.get("concept_id") or "")
        text = str(block.get("text") or "")
        score = int(block.get("score") or 0)
        if block.get("source") == "journal" and text_has_threat_cue(text):
            block["score"] = max(0, score - 22)
            journal_damp += 1
            continue
        if cid.startswith(("math.", "ru.grammar.", "lang.word.")) or intent == "math" and cid.startswith("agent."):
            block["score"] = score + 14
            proxy_boost += 1
        elif intent in ("grammar", "logical") and cid.startswith(("ru.grammar.", "ru.prop.")):
            block["score"] = score + 10
            proxy_boost += 1

    rep = {
        "active": True,
        "mechanism": "displacement",
        "journal_damped": journal_damp,
        "proxy_boosted": proxy_boost,
    }
    defense_block(state)["displacement_last"] = rep
    return rep
