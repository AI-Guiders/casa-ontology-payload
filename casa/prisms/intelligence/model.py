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
    "genetic_zone",
    "emotional_zone",
    "executive_zone",
    "social_zone",
    "logical_zone",
    "character_zone",
    "spatial_zone",
    "metabolic_zone",
    "perceptual_zone",
    "linguistic_zone",
)


def intelligence_root(state: dict) -> dict[str, Any]:
    from casa.prisms.memory.agent_prism import ensure_agent_prism

    block = ensure_agent_prism(state)
    return block.setdefault("intelligence_zones", {})


def zone_proportion_scale(state: dict, zone_id: str, default: float = 1.0) -> float:
    """Genome zone weight for tract/compose scaling (ADR-0062)."""
    try:
        from casa.prisms.genetic import genetic_constant

        return float(genetic_constant(state, f"zone_proportions.{zone_id}", default))
    except ImportError:
        return default
