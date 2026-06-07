#!/usr/bin/env python3
"""Discourse compose facade — backward-compatible imports for tick layer."""

from __future__ import annotations

from typing import Any

from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse import (
    ClauseSketch,
    DiscourseBudget,
    DiscourseSketch,
    PhraseSketch,
    SubjectDiscourseComposer,
    clause_from_pieces,
    clause_from_slot_phrase,
    closing_for_query,
    default_composer,
    discourse_budget_from_blocks,
    infer_discourse_sketch,
    infer_phrase_sketch,
    paragraph_breaks,
    partner_turn_is_brief,
    partner_turn_word_count,
    paste_ratio_against_blocks,
    query_tokens,
    render_discourse,
    render_phrase,
    wm_clauses_from_block,
    wm_link_discourse,
)

_wm_link_discourse = wm_link_discourse


def compose_subject_phrase(
    plan: UtterancePlan,
    query: str,
    *,
    blocks: list[dict[str, Any]],
    query_intent: str,
    stance: str = "partial",
    agent_tract_profile: dict[str, Any] | None = None,
    concept_hints: list[str] | None = None,
) -> str | None:
    """Subject says as much as field bind supports — no fixed sentence quota."""
    return default_composer().compose(
        plan,
        query,
        blocks,
        query_intent=query_intent,
        stance=stance,
        agent_tract_profile=agent_tract_profile,
        concept_hints=concept_hints,
    )


__all__ = [
    "ClauseSketch",
    "DiscourseBudget",
    "DiscourseSketch",
    "PhraseSketch",
    "SubjectDiscourseComposer",
    "_wm_link_discourse",
    "clause_from_pieces",
    "clause_from_slot_phrase",
    "closing_for_query",
    "compose_subject_phrase",
    "default_composer",
    "discourse_budget_from_blocks",
    "infer_discourse_sketch",
    "infer_phrase_sketch",
    "paragraph_breaks",
    "partner_turn_is_brief",
    "partner_turn_word_count",
    "paste_ratio_against_blocks",
    "query_tokens",
    "render_discourse",
    "render_phrase",
    "wm_clauses_from_block",
    "wm_link_discourse",
]
