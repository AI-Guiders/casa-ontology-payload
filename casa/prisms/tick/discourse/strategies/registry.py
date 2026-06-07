from __future__ import annotations

from typing import Any

from casa.prisms.tick.discourse.strategies.agent_emergent import AgentEmergentIntentStrategy
from casa.prisms.tick.discourse.strategies.base import IntentStrategy
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
from casa.prisms.tick.discourse.strategies.rewrite import RewriteIntentStrategy


class IntentStrategyRegistry:
    def __init__(self, base: dict[str, IntentStrategy] | None = None) -> None:
        self._base = base or default_intent_strategies()

    def resolve(self, query_intent: str, profile: dict[str, Any] | None = None) -> IntentStrategy:
        if query_intent in self._base:
            return self._base[query_intent]
        if profile and str(profile.get("intent_id") or query_intent).startswith("agent:"):
            return AgentEmergentIntentStrategy(profile)
        return self._base["general"]


def default_intent_strategies() -> dict[str, IntentStrategy]:
    items: list[IntentStrategy] = [
        GrammarIntentStrategy(),
        ExplainIntentStrategy(),
        DiscussIntentStrategy(),
        JournalIntentStrategy(),
        RewriteIntentStrategy(),
        RecallIntentStrategy(),
        SocialIntentStrategy(),
        GeneralIntentStrategy(),
    ]
    return {s.intent: s for s in items}


_HOST_STRATEGY_BY_MODE = default_intent_strategies()
_HOST_STRATEGY_BY_MODE["field"] = FieldIntentStrategy()
