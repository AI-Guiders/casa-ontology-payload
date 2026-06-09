#!/usr/bin/env python3
"""Emergent discourse length budget from field bind scores."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiscourseBudget:
    """How much the subject may say — from bind strength, not teacher constants."""

    score_floor: int
    stance: str


# Phatic dialog blocks bind strongly on ANY short turn; they should not set the
# answer bar, or they float the floor above the block that actually answers a
# self/identity question (e.g. ru.dialog.self for "как тебя зовут").
_PHATIC_PREFIXES = (
    "ru.dialog.greeting",
    "ru.dialog.farewell",
    "ru.dialog.thanks",
    "ru.dialog.how_are_you",
)


def _budget_hub(block: dict[str, Any]) -> str:
    try:
        from casa.prisms.memory.concept_layer import bind_concept_id

        return bind_concept_id(str(block.get("bind_hub") or block.get("concept_id") or ""))
    except ImportError:
        return str(block.get("concept_id") or "")


def discourse_budget_from_blocks(
    blocks: list[dict[str, Any]],
    *,
    stance: str = "partial",
    query_intent: str = "general",
) -> DiscourseBudget:
    scores = [int(b.get("score") or 0) for b in blocks if b.get("concept_id")]
    if scores:
        by_hub: dict[str, int] = {}
        for b in blocks:
            if not b.get("concept_id"):
                continue
            hub = _budget_hub(b)
            by_hub[hub] = max(by_hub.get(hub, 0), int(b.get("score") or 0))
        scores = list(by_hub.values())
    if not scores:
        return DiscourseBudget(score_floor=0, stance=stance)
    if query_intent == "social":
        content_scores = [
            int(b.get("score") or 0)
            for b in blocks
            if b.get("concept_id")
            and not str(b.get("concept_id")).startswith(_PHATIC_PREFIXES)
        ]
        if content_scores:
            scores = content_scores
    top = max(scores)
    margin = {"confident": 18, "partial": 10, "unknown": 5}.get(stance, 10)
    if query_intent in ("discuss", "journal", "rewrite"):
        margin += 12
    floor = max(4, top - margin)
    return DiscourseBudget(score_floor=floor, stance=stance)
