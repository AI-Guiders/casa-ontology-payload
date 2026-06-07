"""Discourse compose — OOA&D package (ADR-0056).

Public surface for tick layer and legacy imports.
"""

from __future__ import annotations

from casa.prisms.tick.discourse.budget import DiscourseBudget, discourse_budget_from_blocks
from casa.prisms.tick.discourse.composer import SubjectDiscourseComposer, default_composer
from casa.prisms.tick.discourse.model import (
    ClauseSketch,
    DiscourseContext,
    DiscourseSketch,
    PhraseSketch,
)
from casa.prisms.tick.discourse.paste import paste_ratio_against_blocks
from casa.prisms.tick.discourse.render import (
    clause_from_pieces,
    clause_from_slot_phrase,
    closing_for_query,
    paragraph_breaks,
    partner_turn_is_brief,
    partner_turn_word_count,
    query_tokens,
    render_discourse,
    render_phrase,
)
from casa.prisms.tick.discourse.sketch import DiscourseSketchBuilder, infer_discourse_sketch, infer_phrase_sketch
from casa.prisms.tick.discourse.strategies import (
    AgentEmergentIntentStrategy,
    IntentStrategyRegistry,
    default_intent_strategies,
)
from casa.prisms.tick.discourse.wm import wm_clauses_from_block, wm_link_discourse

__all__ = [
    "ClauseSketch",
    "DiscourseBudget",
    "DiscourseContext",
    "DiscourseSketch",
    "DiscourseSketchBuilder",
    "PhraseSketch",
    "AgentEmergentIntentStrategy",
    "IntentStrategyRegistry",
    "clause_from_pieces",
    "clause_from_slot_phrase",
    "closing_for_query",
    "default_intent_strategies",
    "SubjectDiscourseComposer",
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
