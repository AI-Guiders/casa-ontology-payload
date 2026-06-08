#!/usr/bin/env python3
"""Neuromodulator Zone — interoceptive dynamics + gain bus (ADR-0066)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.model import DEFAULT_ZONE_POLICY, intelligence_root
from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

CORE_LATTICE = "agent-neuromod-core"
SANDBOX_LATTICE = "agent-neuromod-sandbox"
CORE_PREFIX = "agent.neuromod."

DEFAULT_CORE = {
    "arousal_drive": 0.08,
    "threat_tone": 0.12,
    "approach": 0.45,
    "regulatory_load": 0.05,
}

DEFAULT_POLICY: dict[str, Any] = {
    "decay_halflife_ticks": {
        "arousal_drive": 4.0,
        "threat_tone": 12.0,
        "approach": 8.0,
        "regulatory_load": 3.0,
    },
    "panic_arousal_threshold": 0.65,
    "panic_threat_threshold": 0.5,
    "panic_risk_regulatory_step": 0.1,
    "panic_risk_regulatory_cutoff": 0.7,
    "metabolic_compose_arousal_gain": 0.5,
    "compose_budget_regulatory_penalty": 0.4,
    "surprise_arousal_per_n": 0.04,
}

_EVENT_DRIVES: dict[str, dict[str, float]] = {
    "self_failure": {"arousal_drive": 0.22, "threat_tone": 0.08, "regulatory_load": 0.06},
    "partner_repair_invite": {"arousal_drive": 0.06, "threat_tone": 0.04},
    "self_repair_success": {"approach": 0.08, "threat_tone": -0.05, "regulatory_load": -0.04},
    "partner_trust": {"approach": 0.12, "threat_tone": -0.06},
    "partner_greeting": {"approach": 0.04, "threat_tone": -0.02},
    "prediction_error": {"arousal_drive": 0.10, "threat_tone": 0.03},
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _decay_factor(halflife_ticks: float) -> float:
    return 0.5 ** (1.0 / max(1.0, float(halflife_ticks)))


def _genetic_policy(state: dict) -> dict[str, Any]:
    merged = dict(DEFAULT_POLICY)
    try:
        from casa.prisms.genetic import genetic_constant

        surprise = genetic_constant(state, "surprise_gains.neuromod_arousal_per_surprise", None)
        if surprise is not None:
            merged["surprise_arousal_per_n"] = float(surprise)
        threat = genetic_constant(state, "surprise_gains.neuromod_threat_on_self_failure", None)
        if threat is not None:
            merged["self_failure_threat_tone"] = float(threat)
    except ImportError:
        pass
    return merged


def _event_drives(state: dict, event: str) -> dict[str, float]:
    drives = dict(_EVENT_DRIVES.get(event) or {})
    if event == "self_failure":
        policy = neuromodulator_policy(state)
        override = policy.get("self_failure_threat_tone")
        if override is not None:
            drives["threat_tone"] = float(override)
    return drives


def ensure_neuromodulator_zone(state: dict) -> dict[str, Any]:
    root = intelligence_root(state)
    zone = root.setdefault("neuromodulator", {})
    core = zone.setdefault("core", {})
    for key, val in DEFAULT_CORE.items():
        core.setdefault(key, val)
    core.setdefault("tick_last", 0)
    zone.setdefault("interoception", {})
    zone.setdefault("gains", {})
    zone.setdefault("core_lattice_id", CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", SANDBOX_LATTICE)
    zone.setdefault("zone_policy", dict(DEFAULT_ZONE_POLICY))
    zone.setdefault("policy", dict(DEFAULT_POLICY))
    return zone


def neuromodulator_is_active(state: dict) -> bool:
    root = intelligence_root(state)
    zone = root.get("neuromodulator")
    if not isinstance(zone, dict):
        return False
    core = zone.get("core")
    return isinstance(core, dict) and "arousal_drive" in core


def neuromodulator_policy(state: dict) -> dict[str, Any]:
    zone = ensure_neuromodulator_zone(state)
    merged = _genetic_policy(state)
    stored = zone.get("policy")
    if isinstance(stored, dict):
        for key, val in stored.items():
            if key == "decay_halflife_ticks" and isinstance(val, dict):
                halflives = dict(merged.get("decay_halflife_ticks") or {})
                halflives.update({k: float(v) for k, v in val.items()})
                merged["decay_halflife_ticks"] = halflives
            elif key in DEFAULT_POLICY:
                merged[key] = val
    zone["policy"] = merged
    return merged


def spawn_neuromodulator_zone(state: dict, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    zone = ensure_neuromodulator_zone(state)
    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=CORE_LATTICE,
        default_sandbox=SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix="agent.neuromod.lab.",
    )
    initial = cfg.get("initial_core")
    if isinstance(initial, dict):
        core = zone.setdefault("core", {})
        for key, val in initial.items():
            if key in DEFAULT_CORE:
                core[key] = _clamp01(float(val))
    if isinstance(cfg.get("policy"), dict):
        zone["policy"] = {**neuromodulator_policy(state), **cfg["policy"]}
    return rep


def _read_core(zone: dict[str, Any]) -> dict[str, float]:
    core = zone.get("core") or {}
    return {k: _clamp01(float(core.get(k) or DEFAULT_CORE[k])) for k in DEFAULT_CORE}


def _write_core(zone: dict[str, Any], values: dict[str, float]) -> None:
    core = zone.setdefault("core", {})
    for key in DEFAULT_CORE:
        core[key] = _clamp01(float(values.get(key, core.get(key) or DEFAULT_CORE[key])))


def interoception_read(
    state: dict,
    *,
    surprise_n: int = 0,
    idle: bool = False,
) -> dict[str, float]:
    zone = ensure_neuromodulator_zone(state)
    core = _read_core(zone)
    policy = neuromodulator_policy(state)

    atp = 1.0
    fatigue = 0.0
    try:
        from casa.prisms.metabolic import metabolic_snapshot

        meta = metabolic_snapshot(state)
        atp = float(meta.get("atp_current") or 1.0)
        fatigue = float(meta.get("fatigue_ema") or 0.0)
    except ImportError:
        pass

    autonomic = _clamp01(0.35 * (1.0 - atp) + 0.25 * fatigue + 0.08 * max(0, int(surprise_n)))
    panic_arousal = float(policy.get("panic_arousal_threshold") or 0.65)
    panic_threat = float(policy.get("panic_threat_threshold") or 0.5)
    arousal_excess = max(0.0, core["arousal_drive"] - panic_arousal * 0.85)
    threat_excess = max(0.0, core["threat_tone"] - panic_threat * 0.85)
    low_atp = max(0.0, 0.45 - atp)
    panic_risk = _clamp01(0.45 * arousal_excess + 0.35 * threat_excess + 0.25 * low_atp + 0.15 * autonomic)
    recovery_bias = 0.12 if idle else 0.04 * core["approach"]
    if atp > 0.7 and fatigue < 0.2:
        recovery_bias += 0.04

    intero = {
        "autonomic_load": round(autonomic, 4),
        "panic_risk": round(panic_risk, 4),
        "recovery_bias": round(recovery_bias, 4),
    }
    zone["interoception"] = intero
    return intero


def _decay_core(state: dict) -> dict[str, float]:
    zone = ensure_neuromodulator_zone(state)
    policy = neuromodulator_policy(state)
    halflives = policy.get("decay_halflife_ticks") or {}
    core = _read_core(zone)
    intero = zone.get("interoception") or {}
    recovery = float(intero.get("recovery_bias") or 0.0)

    for key in DEFAULT_CORE:
        factor = _decay_factor(float(halflives.get(key) or DEFAULT_POLICY["decay_halflife_ticks"][key]))
        baseline = float(DEFAULT_CORE[key])
        delta = core[key] - baseline
        core[key] = _clamp01(baseline + delta * factor + recovery * (baseline - core[key]) * 0.15)
    _write_core(zone, core)
    return core


def _couple_panic(state: dict) -> dict[str, float]:
    zone = ensure_neuromodulator_zone(state)
    policy = neuromodulator_policy(state)
    core = _read_core(zone)
    intero = zone.get("interoception") or {}
    panic_risk = float(intero.get("panic_risk") or 0.0)
    cutoff = float(policy.get("panic_risk_regulatory_cutoff") or 0.7)
    step = float(policy.get("panic_risk_regulatory_step") or 0.1)
    if panic_risk >= cutoff:
        core["regulatory_load"] = _clamp01(core["regulatory_load"] + step)
        _write_core(zone, core)
    return core


def neuromodulator_gain_scales(state: dict) -> dict[str, float]:
    zone = ensure_neuromodulator_zone(state)
    core = _read_core(zone)
    intero = zone.get("interoception") or {}
    panic_risk = float(intero.get("panic_risk") or 0.0)
    policy = neuromodulator_policy(state)
    reg_penalty = float(policy.get("compose_budget_regulatory_penalty") or 0.4)
    gains = {
        "affect_arousal": 1.0 + core["arousal_drive"],
        "affect_valence_threat": 1.0 + 0.25 * core["threat_tone"],
        "tract_social": 1.0 + 0.35 * core["approach"],
        "tract_math_penalty": core["threat_tone"] * panic_risk,
        "metabolic_compose": 1.0 + float(policy.get("metabolic_compose_arousal_gain") or 0.5) * core["arousal_drive"],
        "compose_budget": 1.0 - reg_penalty * core["regulatory_load"] if panic_risk > 0.45 else 1.0,
        "dan_cap": max(0.35, 1.0 - core["regulatory_load"]),
        "defer_bias": core["regulatory_load"] * 0.35 + core["threat_tone"] * 0.15,
    }
    zone["gains"] = {k: round(float(v), 4) for k, v in gains.items()}
    return gains


def neuromodulator_begin_tick(
    state: dict,
    *,
    tick: int = 0,
    surprise_n: int = 0,
    idle: bool = False,
) -> dict[str, Any]:
    """Decay + interoception + coupling + publish gains (ADR-0066 tick order)."""
    if not neuromodulator_is_active(state):
        return {}
    _decay_core(state)
    intero = interoception_read(state, surprise_n=surprise_n, idle=idle)
    core = _couple_panic(state)
    gains = neuromodulator_gain_scales(state)
    zone = ensure_neuromodulator_zone(state)
    zone.setdefault("core", {})["tick_last"] = int(tick)
    return neuromodulator_snapshot(state) | {"interoception": intero, "gains": gains, "core": core}


def neuromodulator_after_event(
    state: dict,
    event: str,
    *,
    tick: int = 0,
    surprise_n: int = 0,
) -> dict[str, Any]:
    if not neuromodulator_is_active(state):
        return {}
    zone = ensure_neuromodulator_zone(state)
    policy = neuromodulator_policy(state)
    core = _read_core(zone)
    drives = _event_drives(state, event)
    if event == "prediction_error" and surprise_n > 0:
        k = float(policy.get("surprise_arousal_per_n") or 0.04)
        drives["arousal_drive"] = float(drives.get("arousal_drive") or 0.0) + k * int(surprise_n)
    for key, delta in drives.items():
        if key in core:
            core[key] = _clamp01(core[key] + float(delta))
    _write_core(zone, core)
    zone.setdefault("core", {})["tick_last"] = int(tick)
    interoception_read(state, surprise_n=surprise_n)
    _couple_panic(state)
    neuromodulator_gain_scales(state)
    return {"event": event, "drives": drives}


def scale_affect_event_deltas(state: dict, deltas: dict[str, float]) -> dict[str, float]:
    if not neuromodulator_is_active(state):
        return dict(deltas)
    gains = neuromodulator_gain_scales(state)
    scaled = dict(deltas)
    if "arousal" in scaled:
        scaled["arousal"] = float(scaled["arousal"]) * float(gains.get("affect_arousal") or 1.0)
    if "security" in scaled:
        threat = float(gains.get("affect_valence_threat") or 1.0)
        scaled["security"] = float(scaled["security"]) * (2.0 - threat) if float(scaled["security"]) < 0 else float(scaled["security"]) * threat
    if "valence" in scaled and float(scaled["valence"]) < 0:
        scaled["valence"] = float(scaled["valence"]) * float(gains.get("affect_valence_threat") or 1.0)
    return scaled


def neuromodulator_metabolic_compose_scale(state: dict) -> float:
    if not neuromodulator_is_active(state):
        return 1.0
    gains = neuromodulator_gain_scales(state)
    return float(gains.get("metabolic_compose") or 1.0)


def neuromodulator_compose_budget_scale(state: dict) -> float:
    if not neuromodulator_is_active(state):
        return 1.0
    gains = neuromodulator_gain_scales(state)
    return max(0.35, float(gains.get("compose_budget") or 1.0))


def neuromodulator_panic_surcharge(state: dict) -> float:
    if not neuromodulator_is_active(state):
        return 0.0
    intero = ensure_neuromodulator_zone(state).get("interoception") or {}
    panic = float(intero.get("panic_risk") or 0.0)
    if panic <= 0.5:
        return 0.0
    return 0.05 * panic


def neuromodulator_after_sleep(state: dict) -> dict[str, Any]:
    if not neuromodulator_is_active(state):
        return {}
    zone = ensure_neuromodulator_zone(state)
    core = _read_core(zone)
    core["arousal_drive"] = _clamp01(core["arousal_drive"] * 0.4)
    core["threat_tone"] = _clamp01(core["threat_tone"] * 0.7)
    core["regulatory_load"] = _clamp01(core["regulatory_load"] * 0.5)
    _write_core(zone, core)
    interoception_read(state, surprise_n=0, idle=True)
    neuromodulator_gain_scales(state)
    return neuromodulator_snapshot(state)


def neuromodulator_snapshot(state: dict) -> dict[str, Any]:
    zone = ensure_neuromodulator_zone(state)
    core = _read_core(zone)
    intero = zone.get("interoception") or {}
    gains = zone.get("gains") or {}
    return {
        "arousal_drive": round(core["arousal_drive"], 4),
        "threat_tone": round(core["threat_tone"], 4),
        "approach": round(core["approach"], 4),
        "regulatory_load": round(core["regulatory_load"], 4),
        "tick_last": int((zone.get("core") or {}).get("tick_last") or 0),
        "panic_risk": round(float(intero.get("panic_risk") or 0.0), 4),
        "gains": dict(gains),
    }
