#!/usr/bin/env python3
"""Spatial Intelligence Zone — vis stub (ADR-0061 P5)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root
from casa.prisms.memory.agent_prism import agent_lattices, create_agent_lattice

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
    core_lid = str(cfg.get("core_lattice_id") or CORE_LATTICE)
    sandbox_lid = str(cfg.get("sandbox_lattice_id") or SANDBOX_LATTICE)
    lats = agent_lattices(state)
    if core_lid not in lats:
        create_agent_lattice(state, core_lid, concept_prefix=str(cfg.get("concept_prefix_core") or CORE_PREFIX))
    if sandbox_lid not in lats:
        create_agent_lattice(
            state,
            sandbox_lid,
            concept_prefix=str(cfg.get("concept_prefix_sandbox") or SANDBOX_PREFIX),
        )
    zone["core_lattice_id"] = core_lid
    zone["sandbox_lattice_id"] = sandbox_lid
    return {"spawned": True, "core_lattice_id": core_lid, "sandbox_lattice_id": sandbox_lid}
