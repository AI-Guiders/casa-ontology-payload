from __future__ import annotations

from typing import Any

from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import DiscourseContext
from casa.prisms.tick.discourse.strategies.base import COMPOSE_HOST_MODES


class AgentEmergentIntentStrategy:
    """Dynamic compose for agent:slug — profile from Intent Prism."""

    def __init__(self, profile: dict[str, Any]) -> None:
        self.profile = profile
        self.intent = str(profile.get("intent_id") or "")

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        from casa.prisms.tick.discourse.strategies.registry import _HOST_STRATEGY_BY_MODE

        mode = str(self.profile.get("compose_mode") or "field")
        host_ctx = ctx.with_intent(mode if mode in COMPOSE_HOST_MODES else "general")
        host_ctx.agent_tract_profile = self.profile
        delegate = _HOST_STRATEGY_BY_MODE.get(mode)
        if delegate is not None:
            return delegate.compose(plan, host_ctx, composer)
        return composer.field_text(host_ctx)
