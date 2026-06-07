"""Intent strategies — how subject composes per query_intent."""

from __future__ import annotations

from casa.prisms.tick.discourse.strategies.agent_emergent import AgentEmergentIntentStrategy
from casa.prisms.tick.discourse.strategies.base import COMPOSE_HOST_MODES, IntentStrategy, _SOCIAL_DIALOG_DENY
from casa.prisms.tick.discourse.strategies.explain import ExplainIntentStrategy
from casa.prisms.tick.discourse.strategies.field_discuss import (
    DiscussIntentStrategy,
    FieldIntentStrategy,
    JournalIntentStrategy,
)
from casa.prisms.tick.discourse.strategies.grammar import GrammarIntentStrategy
from casa.prisms.tick.discourse.strategies.recall_social_general import (
    GeneralIntentStrategy,
    RecallIntentStrategy,
    SocialIntentStrategy,
)
from casa.prisms.tick.discourse.strategies.registry import (
    IntentStrategyRegistry,
    _HOST_STRATEGY_BY_MODE,
    default_intent_strategies,
)
from casa.prisms.tick.discourse.strategies.rewrite import RewriteIntentStrategy

__all__ = [
    "COMPOSE_HOST_MODES",
    "AgentEmergentIntentStrategy",
    "DiscussIntentStrategy",
    "ExplainIntentStrategy",
    "FieldIntentStrategy",
    "GeneralIntentStrategy",
    "GrammarIntentStrategy",
    "IntentStrategy",
    "IntentStrategyRegistry",
    "JournalIntentStrategy",
    "RecallIntentStrategy",
    "RewriteIntentStrategy",
    "SocialIntentStrategy",
    "_HOST_STRATEGY_BY_MODE",
    "_SOCIAL_DIALOG_DENY",
    "default_intent_strategies",
]
