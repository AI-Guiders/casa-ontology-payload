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


def discourse_budget_from_blocks(
    blocks: list[dict[str, Any]],
    *,
    stance: str = "partial",
    query_intent: str = "general",
) -> DiscourseBudget:
    scores = [int(b.get("score") or 0) for b in blocks if b.get("concept_id")]
    if not scores:
        return DiscourseBudget(score_floor=0, stance=stance)
    top = max(scores)
    margin = {"confident": 18, "partial": 10, "unknown": 5}.get(stance, 10)
    if query_intent in ("discuss", "journal", "rewrite"):
        margin += 12
    floor = max(4, top - margin)
    return DiscourseBudget(score_floor=floor, stance=stance)
