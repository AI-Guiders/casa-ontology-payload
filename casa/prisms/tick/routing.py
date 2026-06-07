#!/usr/bin/env python3
"""Unified query routing — tract competition + KB read (ADR-0052 facade)."""

from __future__ import annotations

from casa.prisms.tick.semantic_read import (
    QueryRead,
    classify_query_intent,
    concept_hints_from_surface,
    detect_query_locales,
    has_passage_context,
    route_kb_read,
)
from casa.prisms.tick.tract import compete_tract_intent
from casa.prisms.tick.tract.model import TractScore

__all__ = [
    "QueryRead",
    "TractScore",
    "classify_query_intent",
    "compete_tract_intent",
    "concept_hints_from_surface",
    "detect_query_locales",
    "has_passage_context",
    "route_kb_read",
]
