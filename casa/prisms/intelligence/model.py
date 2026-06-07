#!/usr/bin/env python3
"""Shared Intelligence Zone model (ADR-0061)."""

from __future__ import annotations

from typing import Any

DEFAULT_ZONE_POLICY: dict[str, Any] = {
    "sandbox_writes_core": False,
    "promote_theta": 0.65,
    "max_sandbox_lattices": 2,
    "max_experiments": 32,
}

ZONE_KEYS = (
    "emotional_zone",
    "executive_zone",
    "social_zone",
    "logical_zone",
    "character_zone",
    "spatial_zone",
)


def intelligence_root(state: dict) -> dict[str, Any]:
    from casa.prisms.memory.agent_prism import ensure_agent_prism

    block = ensure_agent_prism(state)
    return block.setdefault("intelligence_zones", {})
