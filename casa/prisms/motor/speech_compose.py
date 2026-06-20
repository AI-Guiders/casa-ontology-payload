#!/usr/bin/env python3
"""Field-native motor unit selection — not text→TTS (ADR-0082)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_BABBLE_POOL = (
    "A:ph:а",
    "A:ph:о",
    "A:ph:ма",
    "A:ph:ба",
    "A:ph:pa",
    "A:ph:la",
)


def _motor_speech_cfg(state: dict) -> dict[str, Any]:
    block = state.setdefault("motor_speech", {})
    return block if isinstance(block, dict) else {}


def motor_speech_enabled(state: dict) -> bool:
    return bool(_motor_speech_cfg(state).get("enabled"))


def compose_motor_units(
    state: dict,
    *,
    tick: int,
    intent: str = "babble",
    reply_text: str | None = None,
    concept_hints: list[str] | None = None,
    max_units: int = 4,
) -> list[str]:
    """Pick stable field tokens for efferent phonation plan."""
    cap = max(1, min(int(max_units), 8))
    hints = list(concept_hints or [])
    cfg = _motor_speech_cfg(state)

    if intent == "echo_field" and hints:
        picked = [h for h in hints if h.startswith(("lang.word.", "A:ph:", "motor.unit."))][:cap]
        if picked:
            return picked

    if intent == "parallel_compose" and (reply_text or "").strip():
        words = re.findall(r"[\w\u0400-\u04FF]+", reply_text.lower())
        if words:
            return [f"motor.lex.{w}" for w in words[:cap]]

    seed = f"{tick}:{intent}:{cfg.get('babble_salt', '')}"
    digest = hashlib.sha256(seed.encode()).hexdigest()
    units: list[str] = []
    for i in range(cap):
        idx = int(digest[i * 2 : i * 2 + 2], 16) % len(_BABBLE_POOL)
        token = _BABBLE_POOL[idx]
        if token not in units:
            units.append(token)
    return units or list(_BABBLE_POOL[:1])
