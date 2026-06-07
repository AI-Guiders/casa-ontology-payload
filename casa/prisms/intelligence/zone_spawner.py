#!/usr/bin/env python3
"""Shared core + sandbox lattice spawn for Intelligence Zones (ADR-0061)."""

from __future__ import annotations

from typing import Any

from casa.prisms.memory.agent_prism import agent_lattices, create_agent_lattice


def ensure_core_sandbox_lattices(
    state: dict,
    *,
    core_lattice_id: str,
    sandbox_lattice_id: str,
    concept_prefix_core: str,
    concept_prefix_sandbox: str,
    width: int = 32,
    height: int = 32,
) -> dict[str, str]:
    lats = agent_lattices(state)
    if core_lattice_id not in lats:
        create_agent_lattice(
            state,
            core_lattice_id,
            width=width,
            height=height,
            concept_prefix=concept_prefix_core,
        )
    if sandbox_lattice_id not in lats:
        create_agent_lattice(
            state,
            sandbox_lattice_id,
            width=width,
            height=height,
            concept_prefix=concept_prefix_sandbox,
        )
    return {"core_lattice_id": core_lattice_id, "sandbox_lattice_id": sandbox_lattice_id}


def spawn_zone_lattices_from_config(
    state: dict,
    zone: dict[str, Any],
    cfg: dict[str, Any],
    *,
    default_core: str,
    default_sandbox: str,
    default_core_prefix: str,
    default_sandbox_prefix: str,
) -> dict[str, str]:
    core_lid = str(cfg.get("core_lattice_id") or zone.get("core_lattice_id") or default_core)
    sandbox_lid = str(cfg.get("sandbox_lattice_id") or zone.get("sandbox_lattice_id") or default_sandbox)
    rep = ensure_core_sandbox_lattices(
        state,
        core_lattice_id=core_lid,
        sandbox_lattice_id=sandbox_lid,
        concept_prefix_core=str(cfg.get("concept_prefix_core") or default_core_prefix),
        concept_prefix_sandbox=str(cfg.get("concept_prefix_sandbox") or default_sandbox_prefix),
    )
    zone["core_lattice_id"] = core_lid
    zone["sandbox_lattice_id"] = sandbox_lid
    return rep
