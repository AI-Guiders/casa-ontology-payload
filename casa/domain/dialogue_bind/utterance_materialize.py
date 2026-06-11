"""Materialize ru.dialog hub slots into competing utterance blocks at bind — not compose."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.partner_scoring import (
    narrative_recently_spoken,
    partner_field_overlap,
    thread_continuer_turn,
)
from casa.prisms.tick.discourse.slots import BlockSlots


def _hub_id(block: dict[str, Any]) -> str:
    from casa.prisms.memory.concept_layer import discourse_concept_id

    return discourse_concept_id(block)


def _variant_score(
    hub_score: int,
    *,
    query: str,
    body: str,
    slot_index: int,
    min_index: int,
    blocks: list[dict[str, Any]],
    continuer: bool,
) -> int:
    stub: dict[str, Any] = {"text": body, "slots": {"phrase": body}}
    score = hub_score + min(24, partner_field_overlap(query, stub))
    if narrative_recently_spoken(body, blocks):
        return 0
    if continuer and slot_index == min_index and partner_field_overlap(query, stub) < 8:
        score = max(0, score - 72)
    return score


def materialize_dialog_utterances(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
) -> None:
    """Split multi-slot dialog hubs into ranked utterance atoms; compose only renders winners."""
    if intent != "social":
        return

    continuer = thread_continuer_turn(blocks, query)
    out: list[dict[str, Any]] = []

    for block in blocks:
        hub = _hub_id(block)
        if not hub.startswith("ru.dialog."):
            out.append(block)
            continue

        slots = BlockSlots.read(block)
        indices = BlockSlots.clause_indices(slots)
        if not indices:
            out.append(block)
            continue

        hub_score = int(block.get("score") or 0)
        min_index = min(indices)
        variants: list[dict[str, Any]] = []

        for i in indices:
            body = str(slots.get(f"clause_{i}") or slots.get(f"sentence_{i}") or "").strip()
            if not body:
                continue
            slot_key = f"clause_{i}" if f"clause_{i}" in slots else f"sentence_{i}"
            score = _variant_score(
                hub_score,
                query=query,
                body=body,
                slot_index=i,
                min_index=min_index,
                blocks=blocks,
                continuer=continuer,
            )
            if score <= 0:
                continue
            row = dict(block)
            row["concept_id"] = f"{hub}@{slot_key}"
            row["bind_hub"] = hub
            row["surface_concept_id"] = hub
            row["text"] = body
            row["slots"] = {"phrase": body, "slot_key": slot_key}
            row["score"] = score
            variants.append(row)

        if variants:
            out.extend(variants)
        elif hub_score > 0:
            out.append(block)

    blocks[:] = out
