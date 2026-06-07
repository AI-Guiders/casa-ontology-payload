#!/usr/bin/env python3
"""Spatial Intelligence Zone — vis stub (ADR-0061 P5)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

CORE_LATTICE = "agent-spatial-core"
SANDBOX_LATTICE = "agent-spatial-sandbox"
CORE_PREFIX = "agent.spatial."
SANDBOX_PREFIX = "agent.spatial.lab."


def ensure_spatial_zone(state: dict) -> dict[str, Any]:
    root = intelligence_root(state)
    zone = root.setdefault("spatial", {})
    zone.setdefault("enabled", False)
    zone.setdefault("vis_attention", 0.0)
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", SANDBOX_LATTICE)
    zone.setdefault("zone_policy", dict(DEFAULT_ZONE_POLICY))
    return zone


def spawn_spatial_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_spatial_zone(state)
    if cfg.get("enabled") is False:
        zone["enabled"] = False
        return {"spawned": False, "reason": "disabled"}
    zone["enabled"] = True
    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix=SANDBOX_PREFIX,
    )
    return {"spawned": True, **rep}
