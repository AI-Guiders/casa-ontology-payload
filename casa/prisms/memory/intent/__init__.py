"""Intent Prism — agent-owned tract hypotheses and emergent intents (ADR-0057)."""

from __future__ import annotations

from .cli import main
from .lifecycle import intent_after_partner_turn, intent_on_sleep_boundary, spawn_emergent_tract
from .model import DEFAULT_INTENT_LATTICE, DEFAULT_INTENT_POLICY
from .policy import (
    agent_tract_concept_id,
    agent_tract_slug,
    agent_tracts,
    format_agent_tract_id,
    get_intent_policy,
    intent_root,
    is_agent_tract,
    list_agent_tracts,
    list_hypotheses,
    resolve_compose_profile,
    spawn_intent_lattice,
)
from .promote import promote_intent_hypothesis
from .scoring import intent_tract_boosts

__all__ = [
    "DEFAULT_INTENT_LATTICE",
    "DEFAULT_INTENT_POLICY",
    "agent_tract_concept_id",
    "agent_tract_slug",
    "agent_tracts",
    "format_agent_tract_id",
    "get_intent_policy",
    "intent_after_partner_turn",
    "intent_on_sleep_boundary",
    "intent_root",
    "intent_tract_boosts",
    "is_agent_tract",
    "list_agent_tracts",
    "list_hypotheses",
    "main",
    "promote_intent_hypothesis",
    "resolve_compose_profile",
    "spawn_emergent_tract",
    "spawn_intent_lattice",
]
