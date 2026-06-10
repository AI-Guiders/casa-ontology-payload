#!/usr/bin/env python3
"""Rationalization — prefer low-conflict explain blocks (ADR-0074 P19e)."""

from __future__ import annotations

from typing import Any

from casa.prisms.defense.core import defense_block, limbic_rationalization_active


def apply_rationalization_block_deltas(
    blocks: list[dict[str, Any]],
    *,
    state: dict,
) -> dict[str, Any]:
    if not limbic_rationalization_active(state):
        return {"active": False}

    honest_damp = 0
    smooth_boost = 0
    for block in blocks:
        cid = str(block.get("concept_id") or "")
        score = int(block.get("score") or 0)
        if cid.startswith("ru.dialog.honest."):
            block["score"] = max(0, score - 16)
            honest_damp += 1
        elif cid.startswith(("ru.dialog.explain.", "ru.dialog.greeting", "ru.dialog.clarify.")):
            block["score"] = score + 12
            smooth_boost += 1
        elif block.get("source") == "journal" and str(block.get("section") or "") == "journal_echo":
            block["score"] = max(0, score - 8)
            honest_damp += 1

    rep = {
        "active": True,
        "mechanism": "rationalization",
        "honest_damped": honest_damp,
        "smooth_boosted": smooth_boost,
    }
    defense_block(state)["rationalization_last"] = rep
    return rep


def rationalization_budget_margin_delta(state: dict | None) -> int:
    """Widen discourse floor margin when rationalizing — shorter, safer reply."""
    if state is None or not limbic_rationalization_active(state):
        return 0
    return 6
