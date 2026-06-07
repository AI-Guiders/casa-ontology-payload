#!/usr/bin/env python3
"""Legacy re-export — prefer casa.prisms.tick.discourse."""

from casa.prisms.tick.discourse import *  # noqa: F403
from casa.prisms.tick.discourse.budget import DiscourseBudget, discourse_budget_from_blocks
from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseSketch, PhraseSketch
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
