#!/usr/bin/env python3
"""Character Intelligence Zone — slow temperament EMA (ADR-0061 P4)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.model import intelligence_root
from casa.prisms.memory.agent_prism import agent_lattices, create_agent_lattice

CORE_LATTICE = "agent-character-core"
CORE_PREFIX = "agent.character."


def ensure_character_zone(state: dict) -> dict[str, Any]:
    root = intelligence_root(state)
    zone = root.setdefault("character", {})
    zone.setdefault("openness", 0.5)
    zone.setdefault("directness", 0.5)
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("ema_alpha", 0.05)
    return zone


def spawn_character_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_character_zone(state)
    core_lid = str(cfg.get("core_lattice_id") or CORE_LATTICE)
    lats = agent_lattices(state)
    if core_lid not in lats:
        create_agent_lattice(state, core_lid, concept_prefix=str(cfg.get("concept_prefix_core") or CORE_PREFIX))
    if cfg.get("initial_openness") is not None:
        zone["openness"] = float(cfg["initial_openness"])
    if cfg.get("initial_directness") is not None:
        zone["directness"] = float(cfg["initial_directness"])
    zone["core_lattice_id"] = core_lid
    return {"core_lattice_id": core_lid}


def character_after_turn(
    state: dict,
    *,
    emotional_axes: dict[str, float] | None = None,
    social_trust: float | None = None,
) -> dict[str, Any]:
    zone = ensure_character_zone(state)
    alpha = float(zone.get("ema_alpha") or 0.05)
    try:
        from casa.prisms.genetic import genetic_constant

        alpha = min(
            alpha,
            float(genetic_constant(state, "ema_limits.character_alpha_max", alpha)),
        )
    except ImportError:
        pass
    axes = emotional_axes or {}
    valence = float(axes.get("valence") or 0.0)
    security = float(axes.get("security") or 0.5)
    trust = float(social_trust if social_trust is not None else 0.5)
    target_open = max(0.0, min(1.0, 0.5 + 0.25 * valence + 0.15 * (trust - 0.5)))
    target_direct = max(0.0, min(1.0, 0.45 + 0.2 * security - 0.1 * abs(valence)))
    zone["openness"] = (1 - alpha) * float(zone["openness"]) + alpha * target_open
    zone["directness"] = (1 - alpha) * float(zone["directness"]) + alpha * target_direct
    return {"openness": float(zone["openness"]), "directness": float(zone["directness"])}


def character_compose_deltas(state: dict) -> dict[str, int]:
    zone = ensure_character_zone(state)
    openness = float(zone.get("openness") or 0.5)
    directness = float(zone.get("directness") or 0.5)
    deltas = {
        "ru.dialog.greeting": int(6 * openness),
        "ru.dialog.self": int(8 * directness) - 4,
    }
    matrix = zone.get("bias_matrix") or {}
    if isinstance(matrix, dict):
        social = matrix.get("social") or {}
        if isinstance(social, dict):
            discuss_bias = float(social.get("discuss") or 1.0)
            if discuss_bias < 0.85:
                deltas["ru.dialog.self"] = deltas.get("ru.dialog.self", 0) - 6
                deltas["ru.dialog.honest."] = deltas.get("ru.dialog.honest.", 0) - 4
    return deltas
