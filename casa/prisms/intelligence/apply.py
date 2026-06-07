#!/usr/bin/env python3
"""Apply Intelligence Zone biases to bind and tract (ADR-0061)."""

from __future__ import annotations

from typing import Any

from casa.prisms.affect import affect_compose_bias, core_affect_state
from casa.prisms.intelligence.character import character_compose_deltas, ensure_character_zone
from casa.prisms.intelligence.executive import ensure_executive_zone, executive_tract_boosts
from casa.prisms.intelligence.logical import ensure_logical_zone, logical_tract_boosts
from casa.prisms.intelligence.social import ensure_social_zone, social_compose_deltas


def intelligence_tract_boosts(
    state: dict,
    *,
    concept_hints: list[str] | None = None,
) -> dict[str, int]:
    merged: dict[str, int] = {}
    for part in (
        executive_tract_boosts(state, concept_hints=concept_hints),
        logical_tract_boosts(state, concept_hints=concept_hints),
    ):
        for tract_id, boost in part.items():
            merged[tract_id] = merged.get(tract_id, 0) + int(boost)
    return merged


def intelligence_compose_deltas(state: dict) -> dict[str, int]:
    affect = affect_compose_bias(state)
    repair = bool(affect.get("repair_pending"))
    deltas = dict(social_compose_deltas(state, repair_pending=repair))
    deltas.update(character_compose_deltas(state))
    if repair:
        for prefix in ("ru.dialog.capabilities", "ru.dialog.how_are_you"):
            deltas.setdefault(prefix, -20)
    return deltas


def apply_zone_deltas_to_blocks(
    blocks: list[dict[str, Any]],
    deltas: dict[str, int],
) -> None:
    if not deltas:
        return
    for block in blocks:
        cid = str(block.get("concept_id") or "")
        score = int(block.get("score") or 0)
        for prefix, delta in deltas.items():
            if cid == prefix or cid.startswith(f"{prefix}.") or prefix.startswith(cid):
                score += int(delta)
        block["score"] = score


def intelligence_snapshot(state: dict) -> dict[str, Any]:
    affect = core_affect_state(state)
    char = ensure_character_zone(state)
    return {
        "emotional": affect.to_dict(),
        "executive": {
            "predict_surprise_n": ensure_executive_zone(state).get("predict_surprise_n"),
        },
        "social": {
            "partner_trust": ensure_social_zone(state).get("partner_trust"),
            "repair_open": ensure_social_zone(state).get("repair_open"),
        },
        "logical": {
            "math_confidence": ensure_logical_zone(state).get("math_confidence"),
        },
        "character": {
            "openness": char.get("openness"),
            "directness": char.get("directness"),
        },
    }
