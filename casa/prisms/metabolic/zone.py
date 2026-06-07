#!/usr/bin/env python3
"""Metabolic Zone — cognitive ATP / fatigue / sleep gate (ADR-0064)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

CORE_LATTICE = "agent-metabolic-core"
SANDBOX_LATTICE = "agent-metabolic-sandbox"
CORE_PREFIX = "agent.metabolic."

DEFAULT_POLICY: dict[str, float] = {
    "atp_per_tick_base": 0.02,
    "cost_surprise": 0.08,
    "cost_compose_token": 0.008,
    "cost_bind_block": 0.001,
    "sleep_threshold": 0.85,
    "recovery_per_idle_tick": 0.06,
    "fatigue_alpha": 0.12,
    "low_atp_tract_cutoff": 0.35,
    "critical_atp_compose_cutoff": 0.20,
}

_SECONDARY_TRACTS = frozenset({"discuss", "rewrite", "journal", "grammar", "explain", "recall"})


def _genetic_policy(state: dict) -> dict[str, float]:
    try:
        from casa.prisms.genetic import genetic_constant

        base = genetic_constant(state, "metabolic.policy", DEFAULT_POLICY)
        if isinstance(base, dict):
            merged = dict(DEFAULT_POLICY)
            merged.update({k: float(v) for k, v in base.items() if k in DEFAULT_POLICY})
            surprise = genetic_constant(state, "surprise_gains.metabolic_fatigue", None)
            if surprise is not None:
                merged["cost_surprise"] = float(surprise)
            return merged
    except ImportError:
        pass
    return dict(DEFAULT_POLICY)


def ensure_metabolic_zone(state: dict) -> dict[str, Any]:
    root = intelligence_root(state)
    zone = root.setdefault("metabolic", {})
    zone.setdefault("atp_current", 1.0)
    zone.setdefault("fatigue_ema", 0.0)
    zone.setdefault("sleep_pressure", 0.0)
    zone.setdefault("forced_sleep", False)
    zone.setdefault("tick_cost_last", {})
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", SANDBOX_LATTICE)
    zone.setdefault("zone_policy", dict(DEFAULT_ZONE_POLICY))
    zone.setdefault("policy", dict(DEFAULT_POLICY))
    return zone


def metabolic_policy(state: dict) -> dict[str, float]:
    zone = ensure_metabolic_zone(state)
    merged = _genetic_policy(state)
    stored = zone.get("policy")
    if isinstance(stored, dict):
        merged.update({k: float(v) for k, v in stored.items() if k in DEFAULT_POLICY})
    zone["policy"] = merged
    return merged


def spawn_metabolic_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_metabolic_zone(state)
    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix="agent.metabolic.lab.",
    )
    if cfg.get("initial_atp") is not None:
        zone["atp_current"] = float(cfg["initial_atp"])
    if isinstance(cfg.get("policy"), dict):
        zone["policy"] = {**metabolic_policy(state), **{k: float(v) for k, v in cfg["policy"].items()}}
    return rep


def metabolic_begin_tick(state: dict, *, tick: int = 0) -> dict[str, Any]:
    zone = ensure_metabolic_zone(state)
    policy = metabolic_policy(state)
    atp = float(zone.get("atp_current") or 1.0)
    cost = float(policy["atp_per_tick_base"])
    atp = max(0.0, atp - cost)
    zone["atp_current"] = atp
    zone["tick_cost_last"] = {"base": cost, "tick": int(tick)}
    zone["forced_sleep"] = False
    return {"atp": atp, "base_cost": cost}


def metabolic_end_tick(
    state: dict,
    *,
    surprise_n: int = 0,
    compose_tokens: int = 0,
    bind_blocks: int = 0,
    had_partner_input: bool = True,
) -> dict[str, Any]:
    zone = ensure_metabolic_zone(state)
    policy = metabolic_policy(state)
    atp = float(zone.get("atp_current") or 0.0)
    surprise_cost = float(policy["cost_surprise"]) * max(0, int(surprise_n))
    compose_cost = float(policy["cost_compose_token"]) * max(0, int(compose_tokens))
    bind_cost = float(policy["cost_bind_block"]) * max(0, int(bind_blocks))
    total = surprise_cost + compose_cost + bind_cost
    if not had_partner_input:
        atp = min(1.0, atp + float(policy["recovery_per_idle_tick"]))
    else:
        atp = max(0.0, atp - total)
    zone["atp_current"] = atp
    alpha = float(policy["fatigue_alpha"])
    load = min(1.0, total / max(0.05, 1.0 - atp + 0.05))
    zone["fatigue_ema"] = (1 - alpha) * float(zone.get("fatigue_ema") or 0.0) + alpha * load
    pressure = min(1.0, float(zone["fatigue_ema"]) + max(0.0, 0.5 - atp))
    zone["sleep_pressure"] = pressure
    zone["forced_sleep"] = pressure >= float(policy["sleep_threshold"])
    zone["tick_cost_last"] = {
        **(zone.get("tick_cost_last") or {}),
        "surprise": surprise_cost,
        "compose": compose_cost,
        "bind": bind_cost,
        "total": total,
    }
    return metabolic_snapshot(state)


def metabolic_allows_tract(state: dict, tract_id: str) -> bool:
    zone = ensure_metabolic_zone(state)
    policy = metabolic_policy(state)
    atp = float(zone.get("atp_current") or 0.0)
    if atp >= float(policy["low_atp_tract_cutoff"]):
        return True
    if tract_id in _SECONDARY_TRACTS:
        return False
    return tract_id in {"general", "social", "math", "query"}


def metabolic_compose_budget(state: dict) -> int | None:
    zone = ensure_metabolic_zone(state)
    policy = metabolic_policy(state)
    atp = float(zone.get("atp_current") or 0.0)
    if atp >= float(policy["critical_atp_compose_cutoff"]):
        return None
    return max(40, int(80 * atp / float(policy["critical_atp_compose_cutoff"])))


def metabolic_should_sleep(state: dict) -> bool:
    zone = ensure_metabolic_zone(state)
    return bool(zone.get("forced_sleep"))


def metabolic_snapshot(state: dict) -> dict[str, Any]:
    zone = ensure_metabolic_zone(state)
    return {
        "atp_current": round(float(zone.get("atp_current") or 0.0), 4),
        "fatigue_ema": round(float(zone.get("fatigue_ema") or 0.0), 4),
        "sleep_pressure": round(float(zone.get("sleep_pressure") or 0.0), 4),
        "forced_sleep": bool(zone.get("forced_sleep")),
    }
