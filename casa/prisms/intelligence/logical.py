#!/usr/bin/env python3
"""Logical Intelligence Zone — math tract (ADR-0061 P3)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root, zone_proportion_scale
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

CORE_LATTICE = "agent-logical-core"
SANDBOX_LATTICE = "agent-logical-sandbox"
CORE_PREFIX = "agent.logic."
SANDBOX_PREFIX = "agent.logic.lab."


def ensure_logical_zone(state: dict) -> dict[str, Any]:
    root = intelligence_root(state)
    zone = root.setdefault("logical", {})
    zone.setdefault("math_confidence", 0.5)
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", SANDBOX_LATTICE)
    zone.setdefault("zone_policy", dict(DEFAULT_ZONE_POLICY))
    zone.setdefault("sandbox", {"experiments": [], "next_experiment_id": 1})
    return zone


def spawn_logical_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_logical_zone(state)
    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix=SANDBOX_PREFIX,
    )
    if cfg.get("initial_math_confidence") is not None:
        zone["math_confidence"] = float(cfg["initial_math_confidence"])
    return rep


def logical_after_turn(
    state: dict,
    *,
    concept_hints: list[str] | None = None,
    subject_reply: str,
    query_intent: str = "",
) -> dict[str, Any]:
    zone = ensure_logical_zone(state)
    has_math = any(str(h).startswith("math.") for h in (concept_hints or []))
    if has_math and (subject_reply or "").strip() and query_intent == "math":
        zone["math_confidence"] = min(1.0, float(zone["math_confidence"]) + 0.06)
    elif has_math and not (subject_reply or "").strip():
        zone["math_confidence"] = max(0.0, float(zone["math_confidence"]) - 0.04)
    return {"math_confidence": float(zone["math_confidence"])}


def logical_tract_boosts(state: dict, *, concept_hints: list[str] | None = None) -> dict[str, int]:
    zone = ensure_logical_zone(state)
    has_math = any(str(h).startswith("math.") for h in (concept_hints or []))
    if not has_math:
        return {}
    conf = float(zone.get("math_confidence") or 0.5)
    scale = zone_proportion_scale(state, "logical", 1.0)
    return {
        "math": int((18 + 12 * conf) * scale),
        "social": -int((10 + 8 * (1.0 - conf)) * scale),
    }
