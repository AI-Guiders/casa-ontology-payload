"""Intent Prism — constants."""

from __future__ import annotations

import re
from typing import Any

DEFAULT_INTENT_LATTICE = "agent-intent-scratch"
INTENT_CONCEPT_PREFIX = "agent.intent."
AGENT_TRACT_PREFIX = "agent:"
AGENT_TRACT_CONCEPT_PREFIX = "agent.tract."

DEFAULT_INTENT_POLICY: dict[str, Any] = {
    "theta_decay": 0.12,
    "theta_hold": 0.38,
    "theta_promote": 0.62,
    "max_hypotheses": 48,
    "min_boost": 4,
    "max_boost_per_tract": 28,
    "emergent_general_min_bind": 18,
    "emergent_activation_threshold": 3,
}

COMPOSE_MODES = frozenset({"field", "discuss", "journal", "social", "explain", "general", "recall"})


def slug_from_tokens(tokens: list[str]) -> str:
    pick = [t for t in tokens if len(t) > 3][:3]
    if not pick:
        pick = tokens[:2] or ["emergent"]
    return re.sub(r"-+", "-", "-".join(pick))[:28]
