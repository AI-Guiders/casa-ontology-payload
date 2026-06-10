#!/usr/bin/env python3
"""Projection — attribute own negative affect to partner surface (ADR-0074 P19d)."""

from __future__ import annotations

from typing import Any

from casa.prisms.defense.core import defense_block, limbic_projection_active


def apply_projection_block_deltas(
    blocks: list[dict[str, Any]],
    *,
    intent: str,
    state: dict,
) -> dict[str, Any]:
    if not limbic_projection_active(state) or intent not in ("social", "discuss", "general"):
        return {"active": False}

    partner_boost = 0
    self_damp = 0
    for block in blocks:
        cid = str(block.get("concept_id") or "")
        score = int(block.get("score") or 0)
        if cid in ("subject.dialog.partner_recent",) or cid.startswith("ru.dialog.thanks"):
            block["score"] = score + 16
            partner_boost += 1
        elif cid.startswith("ru.dialog.self") or cid == "subject.dialog.self_recent":
            block["score"] = max(0, score - 10)
            self_damp += 1
        elif block.get("source") == "dialogue" and "partner" in str(block.get("section") or ""):
            block["score"] = score + 12
            partner_boost += 1

    rep = {
        "active": True,
        "mechanism": "projection",
        "partner_boosted": partner_boost,
        "self_damped": self_damp,
    }
    defense_block(state)["projection_last"] = rep
    return rep
