#!/usr/bin/env python3
"""Executive Intelligence Zone — predict, FPN mode (ADR-0061 P1)."""

from __future__ import annotations

from typing import Any

from casa.prisms.control import predict as lp
from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root
from casa.prisms.memory.agent_prism import agent_lattices, create_agent_lattice

CORE_LATTICE = "agent-exec-core"
SANDBOX_LATTICE = "agent-exec-sandbox"
CORE_PREFIX = "agent.exec."
SANDBOX_PREFIX = "agent.exec.lab."


def ensure_executive_zone(state: dict) -> dict[str, Any]:
    root = intelligence_root(state)
    zone = root.setdefault("executive", {})
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", SANDBOX_LATTICE)
    zone.setdefault("predict_surprise_n", 0)
    zone.setdefault("fpn_mode", "dialogue")
    zone.setdefault("zone_policy", dict(DEFAULT_ZONE_POLICY))
    zone.setdefault("sandbox", {"experiments": [], "next_experiment_id": 1})
    return zone


def spawn_executive_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_executive_zone(state)
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
    if cfg.get("zone_policy"):
        zone["zone_policy"].update(cfg["zone_policy"])
    return {"core_lattice_id": core_lid, "sandbox_lattice_id": sandbox_lid}


def executive_after_turn(
    state: dict,
    *,
    query: str,
    concept_hints: list[str] | None = None,
    prior_digest: list[str] | None = None,
) -> dict[str, Any]:
    zone = ensure_executive_zone(state)
    hints = list(concept_hints or [])
    digest = hints[:8]
    model = lp.fit_transitions([prior_digest or [], digest]) if prior_digest is not None else {}
    expected = lp.predict_next(digest, model) if model.get("succ") else set()
    observed = set(digest)
    err = lp.prediction_error(observed, expected) if expected else set()
    zone["predict_surprise_n"] = len(err)
    zone["last_digest_size"] = len(digest)
    return {"surprise_n": len(err), "prediction_error": sorted(err)}


def executive_tract_boosts(state: dict, *, concept_hints: list[str] | None = None) -> dict[str, int]:
    zone = ensure_executive_zone(state)
    boosts = {"math": 0, "social": 0, "general": 0, "explain": 0}
    surprise = int(zone.get("predict_surprise_n") or 0)
    if surprise > 0:
        boosts["general"] += min(12, surprise * 4)
    has_math = any(str(h).startswith("math.") for h in (concept_hints or []))
    if has_math:
        boosts["math"] += 14
        boosts["social"] -= 8
    return boosts
