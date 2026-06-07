from __future__ import annotations

from typing import Any

from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import DiscourseContext


class FieldIntentStrategy:
    intent = "field"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        return composer.field_text(ctx)


class DiscussIntentStrategy:
    intent = "discuss"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        return composer.field_text(ctx.with_intent("discuss"))


class JournalIntentStrategy:
    intent = "journal"

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None:
        return composer.field_text(ctx.with_intent("journal"))
