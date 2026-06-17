#!/usr/bin/env python3
"""Defense Intelligence Zone — innate survival gates @ T=0 (ADR-0076)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root

CORE_LATTICE = "agent-defense-core"
SANDBOX_LATTICE = "agent-defense-sandbox"
CORE_PREFIX = "agent.defense."
SANDBOX_PREFIX = "agent.defense.lab."


def migrate_legacy_defense_state(state: dict) -> bool:
    """Move flat state.defense → intelligence_zones.defense.core (idempotent)."""
    legacy = state.get("defense")
    if not isinstance(legacy, dict) or not legacy:
        return False
    root = intelligence_root(state)
    zone = root.setdefault("defense", {})
    core = zone.setdefault("core", {})
    if isinstance(core, dict):
        for key, val in legacy.items():
            core.setdefault(key, val)
    state.pop("defense", None)
    return True


def ensure_defense_zone(state: dict) -> dict[str, Any]:
    if isinstance(state.get("defense"), dict):
        migrate_legacy_defense_state(state)
    root = intelligence_root(state)
    zone = root.setdefault("defense", {})
    zone.setdefault("core", {})
    sandbox = zone.setdefault("sandbox", {})
    sandbox.setdefault("lattice_id", SANDBOX_LATTICE)
    sandbox.setdefault("experiments", [])
    sandbox.setdefault("next_experiment_id", 1)
    policy = zone.setdefault("zone_policy", {})
    for key, val in DEFAULT_ZONE_POLICY.items():
        policy.setdefault(key, val)
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", SANDBOX_LATTICE)
    return zone


def defense_core_block(state: dict) -> dict[str, Any]:
    """Mutable defense core — trauma edges, counters, honesty."""
    zone = ensure_defense_zone(state)
    core = zone.setdefault("core", {})
    if not isinstance(core, dict):
        core = {}
        zone["core"] = core
    return core


def spawn_defense_zone(state: dict, *, tick: int = 0, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_defense_zone(state)
    if cfg.get("zone_policy"):
        zone["zone_policy"].update(cfg["zone_policy"])

    from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix=SANDBOX_PREFIX,
    )
    zone["core_lattice_id"] = rep["core_lattice_id"]
    zone["sandbox_lattice_id"] = rep["sandbox_lattice_id"]
    zone["sandbox"]["lattice_id"] = rep["sandbox_lattice_id"]
    zone["sandbox"]["active_lattice"] = rep["sandbox_lattice_id"]
    return rep


def defense_zone_snapshot(state: dict) -> dict[str, Any]:
    zone = ensure_defense_zone(state)
    core = defense_core_block(state)
    return {
        "core_lattice_id": zone.get("core_lattice_id"),
        "sandbox_lattice_id": zone.get("sandbox_lattice_id"),
        "trauma_edges": len(core.get("trauma_edges") or []),
        "repression_count": int(core.get("repression_count") or 0),
        "trauma_count": int(core.get("trauma_count") or 0),
    }
