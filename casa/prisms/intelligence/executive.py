#!/usr/bin/env python3
"""Executive Intelligence Zone — predict, FPN mode (ADR-0061 P1)."""

from __future__ import annotations

from typing import Any

from casa.prisms.control import predict as lp
from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root, zone_proportion_scale
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

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
    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix=SANDBOX_PREFIX,
    )
    if cfg.get("zone_policy"):
        zone["zone_policy"].update(cfg["zone_policy"])
    return rep


def executive_before_compose(
    state: dict,
    *,
    query: str,
    concept_hints: list[str] | None = None,
    prior_digest: list[str] | None = None,
) -> dict[str, Any]:
    """Partner-side predict/surprise before tract bind (ADR-0061 tick order)."""
    hints = list(concept_hints or [])
    if not hints and (query or "").strip():
        from casa.prisms.tick.tract.model import parse_math_ops

        hints = list(parse_math_ops(query))
    return executive_after_turn(
        state,
        query=query,
        concept_hints=hints,
        prior_digest=prior_digest,
    )


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
    scale = zone_proportion_scale(state, "executive", 1.0)
    if surprise > 0:
        boosts["general"] += int(min(12, surprise * 4) * scale)
    has_math = any(str(h).startswith("math.") for h in (concept_hints or []))
    if has_math:
        boosts["math"] += int(14 * scale)
        boosts["social"] -= int(8 * scale)
    return boosts
