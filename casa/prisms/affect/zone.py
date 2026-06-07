#!/usr/bin/env python3
"""Emotional Zone — limbic core + agent sandbox (ADR-0060)."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.affect.model import (
    CORE_PREFIX,
    DEFAULT_AXES,
    DEFAULT_CORE_LATTICE,
    DEFAULT_SANDBOX_LATTICE,
    DEFAULT_ZONE_POLICY,
    SANDBOX_PREFIX,
    AffectAxes,
    CoreAffectState,
    LIFE_EVENTS,
    SandboxExperiment,
)
from casa.prisms.memory.agent_prism import agent_lattices, create_agent_lattice, ensure_agent_prism

_EVENT_DELTAS: dict[str, dict[str, float]] = {
    "partner_greeting": {"valence": 0.08, "arousal": 0.05, "security": 0.06},
    "self_failure": {"valence": -0.12, "arousal": 0.15, "security": -0.1},
    "partner_repair_invite": {"valence": 0.02, "arousal": 0.1, "security": -0.04},
    "self_repair_success": {"valence": 0.1, "arousal": -0.05, "security": 0.12},
    "partner_trust": {"valence": 0.08, "security": 0.1},
    "prediction_error": {"valence": -0.05, "arousal": 0.12},
}

_EPISODIC_FLAGS: dict[str, tuple[str, float]] = {
    "self_failure": ("dialog.repair_pending", 1.0),
    "self_repair_success": ("dialog.repair_pending", 0.0),
    "partner_repair_invite": ("dialog.repair_invited", 1.0),
}


def ensure_emotional_zone(state: dict) -> dict[str, Any]:
    block = ensure_agent_prism(state)
    zone = block.setdefault("emotional_zone", {})
    zone.setdefault(
        "core",
        CoreAffectState(
            axes=AffectAxes.from_dict(DEFAULT_AXES),
            lattice_id=DEFAULT_CORE_LATTICE,
        ).to_dict(),
    )
    sandbox = zone.setdefault("sandbox", {})
    sandbox.setdefault("lattice_id", DEFAULT_SANDBOX_LATTICE)
    sandbox.setdefault("experiments", [])
    sandbox.setdefault("next_experiment_id", 1)
    policy = zone.setdefault("zone_policy", {})
    for key, val in DEFAULT_ZONE_POLICY.items():
        policy.setdefault(key, val)
    return zone


def _ensure_lattice(state: dict, lattice_id: str, *, concept_prefix: str) -> str:
    lats = agent_lattices(state)
    if lattice_id not in lats:
        create_agent_lattice(
            state,
            lattice_id,
            width=32,
            height=32,
            concept_prefix=concept_prefix,
        )
    return lattice_id


def spawn_emotional_zone(
    state: dict,
    *,
    tick: int = 0,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cold boot: core limbic lattice + sandbox test lattice + neutral axes."""
    cfg = config or {}
    core_lid = str(cfg.get("core_lattice_id") or DEFAULT_CORE_LATTICE)
    sandbox_lid = str(cfg.get("sandbox_lattice_id") or DEFAULT_SANDBOX_LATTICE)
    initial = cfg.get("initial_axes") if isinstance(cfg.get("initial_axes"), dict) else DEFAULT_AXES
    policy = cfg.get("zone_policy") if isinstance(cfg.get("zone_policy"), dict) else {}

    zone = ensure_emotional_zone(state)
    if policy:
        zone["zone_policy"].update(policy)

    _ensure_lattice(state, core_lid, concept_prefix=str(cfg.get("concept_prefix_core") or CORE_PREFIX))
    _ensure_lattice(state, sandbox_lid, concept_prefix=str(cfg.get("concept_prefix_sandbox") or SANDBOX_PREFIX))

    core = CoreAffectState(
        axes=AffectAxes.from_dict(initial),
        tick=int(tick),
        lattice_id=core_lid,
    )
    zone["core"] = core.to_dict()
    zone["sandbox"]["lattice_id"] = sandbox_lid
    zone["sandbox"]["active_lattice"] = sandbox_lid

    return {
        "core_lattice_id": core_lid,
        "sandbox_lattice_id": sandbox_lid,
        "core_axes": core.axes.to_dict(),
    }


def core_affect_state(state: dict) -> CoreAffectState:
    zone = ensure_emotional_zone(state)
    return CoreAffectState.from_dict(zone.get("core"))


def _apply_deltas(axes: AffectAxes, deltas: dict[str, float]) -> AffectAxes:
    merged = axes.to_dict()
    for key, delta in deltas.items():
        if key in merged:
            merged[key] = float(merged[key]) + float(delta)
    return AffectAxes.from_dict(merged).clamped()


def affect_after_turn(
    state: dict,
    event: str,
    *,
    tick: int = 0,
    extra_deltas: dict[str, float] | None = None,
) -> CoreAffectState:
    """Life event → core axes (not sandbox, not teacher)."""
    if event not in LIFE_EVENTS:
        raise ValueError(f"unknown affect life event: {event!r}")
    zone = ensure_emotional_zone(state)
    core = CoreAffectState.from_dict(zone.get("core"))
    deltas = dict(_EVENT_DELTAS.get(event, {}))
    if extra_deltas:
        deltas.update({k: float(v) for k, v in extra_deltas.items() if k in DEFAULT_AXES})
    core.axes = _apply_deltas(core.axes, deltas)
    flag = _EPISODIC_FLAGS.get(event)
    if flag:
        key, val = flag
        if val <= 0 and key in core.episodic:
            core.episodic.pop(key, None)
        elif val > 0:
            core.episodic[key] = val
    core.last_event = event
    core.tick = int(tick)
    zone["core"] = core.to_dict()
    return core


def sandbox_record_experiment(
    state: dict,
    *,
    deltas: dict[str, float],
    tick: int = 0,
    note: str = "",
    score: float = 0.0,
) -> SandboxExperiment:
    """Agent drafts an emotional experiment — does not touch core."""
    zone = ensure_emotional_zone(state)
    sandbox = zone.setdefault("sandbox", {})
    policy = zone.get("zone_policy") or {}
    max_exp = int(policy.get("max_experiments") or DEFAULT_ZONE_POLICY["max_experiments"])
    experiments: list[dict[str, Any]] = list(sandbox.get("experiments") or [])
    next_id = int(sandbox.get("next_experiment_id") or 1)
    exp_id = f"exp-{next_id}"
    clean_deltas = {k: float(v) for k, v in deltas.items() if k in DEFAULT_AXES}
    row = SandboxExperiment(
        experiment_id=exp_id,
        tick=int(tick),
        deltas=clean_deltas,
        note=str(note or "").strip(),
        score=float(score),
    )
    experiments.append(row.to_dict())
    if len(experiments) > max_exp:
        experiments = experiments[-max_exp:]
    sandbox["experiments"] = experiments
    sandbox["next_experiment_id"] = next_id + 1
    return row


def promote_sandbox_experiment(state: dict, experiment_id: str) -> CoreAffectState | None:
    """Agent promotes sandbox experiment → core axes (explicit, scored)."""
    zone = ensure_emotional_zone(state)
    policy = zone.get("zone_policy") or {}
    theta = float(policy.get("promote_theta") or DEFAULT_ZONE_POLICY["promote_theta"])
    sandbox = zone.get("sandbox") or {}
    experiments = list(sandbox.get("experiments") or [])
    target: dict[str, Any] | None = None
    for row in experiments:
        if str(row.get("experiment_id") or row.get("id")) == experiment_id:
            target = row
            break
    if not target or target.get("promoted"):
        return None
    score = float(target.get("score") or 0.0)
    if score < theta:
        return None
    core = CoreAffectState.from_dict(zone.get("core"))
    core.axes = _apply_deltas(core.axes, target.get("deltas") or {})
    core.last_event = f"promote:{experiment_id}"
    target["promoted"] = True
    zone["core"] = core.to_dict()
    sandbox["experiments"] = experiments
    return core


def affect_compose_bias(state: dict) -> dict[str, Any]:
    """Hints for bind/compose/disposition — derived from core only."""
    core = core_affect_state(state)
    axes = core.axes.clamped()
    repair = float(core.episodic.get("dialog.repair_pending") or 0.0)
    return {
        "valence": axes.valence,
        "arousal": axes.arousal,
        "security": axes.security,
        "repair_pending": repair > 0,
        "budget_scale": max(0.6, min(1.4, 1.0 + 0.25 * axes.arousal - 0.15 * repair)),
        "social_affinity_delta": int(round(8 * axes.security)),
        "honest_defer_bias": repair > 0 and axes.security < 0.45,
    }


def infer_life_event_from_turn(
    state: dict,
    *,
    partner_text: str,
    subject_reply: str,
    query_intent: str = "",
    disposition: str = "",
) -> str | None:
    """Lightweight event inference for dialogue tick wiring."""
    pt = (partner_text or "").strip().lower()
    reply = (subject_reply or "").strip()
    core = core_affect_state(state)
    if re.search(r"\b(прости|извини)\b", pt) and re.search(r"(неожидан|странн|молч)", pt):
        return "partner_repair_invite"
    if disposition in {"defer", "refuse"} and not reply:
        return "self_failure"
    if not reply and query_intent in {"math", "social", "general", "explain"}:
        return "self_failure"
    if re.search(r"\b(спасибо|благодар)\b", pt):
        return "partner_trust"
    if re.search(r"\b(привет|здравств)\b", pt):
        return "partner_greeting"
    if reply and core.episodic.get("dialog.repair_pending"):
        return "self_repair_success"
    return None
