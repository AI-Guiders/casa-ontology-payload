"""Legacy field-social adapter — candidates only, no surface rendering."""

from __future__ import annotations

from typing import Any

from casa.prisms.tick.discourse.material import (
    EfferentCandidate,
    build_afferent_event,
    build_text_understanding,
    candidates_from_blocks,
)
from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext


def field_social_candidates(ctx: DiscourseContext) -> list[EfferentCandidate]:
    """Expose old field-social material as typed candidates, not clauses."""
    event = build_afferent_event(ctx.query)
    trace = build_text_understanding(event)
    return candidates_from_blocks(trace, ctx.blocks)


def realize_subject_field_block(block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
    _ = (block, ctx)
    return []
