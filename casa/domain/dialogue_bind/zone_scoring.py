"""Intelligence Zone compose deltas on bind blocks (ADR-0061)."""

from __future__ import annotations

from typing import Any


def affect_bind_nudge(state: dict, *, concept_id: str, intent: str) -> int:
    """Apply affect_compose_bias fields not covered by intelligence_compose_deltas."""
    from casa.prisms.affect import affect_compose_bias

    bias = affect_compose_bias(state)
    cid = str(concept_id or "")
    delta = 0
    affinity = int(bias.get("social_affinity_delta") or 0)
    if affinity and cid.startswith("ru.dialog."):
        delta += affinity
    if bias.get("honest_defer_bias"):
        if cid.startswith("ru.dialog.honest."):
            delta += 14
        if cid.startswith("ru.dialog.capabilities"):
            delta -= 18
        if cid.startswith("ru.dialog.affect") and intent == "social":
            delta += 6
    return delta


def apply_intelligence_zone_block_deltas(
    blocks: list[dict[str, Any]],
    state: dict,
    *,
    concept_hints: list[str] | None = None,
    intent: str = "",
) -> None:
    from casa.prisms.intelligence.apply import (
        apply_zone_deltas_to_blocks,
        intelligence_compose_deltas,
    )

    apply_zone_deltas_to_blocks(
        blocks,
        intelligence_compose_deltas(state, concept_hints=concept_hints),
    )
    for block in blocks:
        nudge = affect_bind_nudge(state, concept_id=str(block.get("concept_id") or ""), intent=intent)
        if nudge:
            block["score"] = int(block.get("score") or 0) + nudge
