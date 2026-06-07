from __future__ import annotations

from typing import Any, Protocol

from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.discourse.model import DiscourseContext

_SOCIAL_DIALOG_DENY = ("ru.dialog.explain",)

COMPOSE_HOST_MODES = frozenset(
    {"grammar", "explain", "discuss", "journal", "rewrite", "recall", "social", "general", "field"}
)


class IntentStrategy(Protocol):
    intent: str

    def compose(self, plan: UtterancePlan, ctx: DiscourseContext, composer: Any) -> str | None: ...
