#!/usr/bin/env python3
"""Emotional Zone — limbic core + agent sandbox (ADR-0060, wire under intelligence_zones)."""

from __future__ import annotations

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
from casa.prisms.memory.agent_prism import ensure_agent_prism


def _intelligence_root(state: dict) -> dict:
    from casa.prisms.intelligence.model import intelligence_root

    return intelligence_root(state)

_EVENT_DELTAS: dict[str, dict[str, float]] = {
    "partner_greeting": {"valence": 0.08, "arousal": 0.05, "security": 0.06},
    "self_failure": {"valence": -0.12, "arousal": 0.15, "security": -0.1},
    "partner_repair_invite": {"valence": 0.02, "arousal": 0.1, "security": -0.04},
    "self_repair_success": {"valence": 0.1, "arousal": -0.05, "security": 0.12},
    "partner_trust": {"valence": 0.08, "security": 0.1},
    "prediction_error": {"valence": -0.05, "arousal": 0.12},
    "security_threat": {"valence": -0.18, "arousal": 0.28, "security": -0.22},
    "caregiver_violation": {"valence": -0.25, "arousal": 0.32, "security": -0.3},
}

_EPISODIC_FLAGS: dict[str, tuple[str, float]] = {
    "self_failure": ("dialog.repair_pending", 1.0),
    "self_repair_success": ("dialog.repair_pending", 0.0),
    "partner_repair_invite": ("dialog.repair_invited", 1.0),
}


def migrate_legacy_emotional_zone(state: dict) -> bool:
    """Move prism_agent.emotional_zone → intelligence_zones.emotional (idempotent)."""
    block = ensure_agent_prism(state)
    legacy = block.get("emotional_zone")
    if not isinstance(legacy, dict) or not legacy:
        return False
    root = _intelligence_root(state)
    current = root.get("emotional")
    if isinstance(current, dict) and current.get("core"):
        block.pop("emotional_zone", None)
        return False
    root["emotional"] = legacy
    block.pop("emotional_zone", None)
    return True


def consolidate_emotional_zone_wire(state: dict) -> bool:
    """Ensure canonical wire: emotional lives only under intelligence_zones."""
    migrated = migrate_legacy_emotional_zone(state)
    block = ensure_agent_prism(state)
    if "emotional_zone" in block:
        block.pop("emotional_zone", None)
        migrated = True
    return migrated


def ensure_emotional_zone(state: dict) -> dict[str, Any]:
    migrate_legacy_emotional_zone(state)
    root = _intelligence_root(state)
    zone = root.setdefault("emotional", {})
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
    zone.setdefault("core_lattice_id", DEFAULT_CORE_LATTICE)
    zone.setdefault("sandbox_lattice_id", DEFAULT_SANDBOX_LATTICE)
    return zone


def spawn_emotional_zone(
    state: dict,
    *,
    tick: int = 0,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cold boot: core limbic lattice + sandbox test lattice + neutral axes."""
    cfg = config or {}
    initial = cfg.get("initial_axes") if isinstance(cfg.get("initial_axes"), dict) else DEFAULT_AXES
    policy = cfg.get("zone_policy") if isinstance(cfg.get("zone_policy"), dict) else {}

    zone = ensure_emotional_zone(state)
    if policy:
        zone["zone_policy"].update(policy)

    from casa.prisms.intelligence.zone_spawner import spawn_zone_lattices_from_config

    rep = spawn_zone_lattices_from_config(
        state,
        zone,
        cfg,
        default_core=DEFAULT_CORE_LATTICE,
        default_sandbox=DEFAULT_SANDBOX_LATTICE,
        default_core_prefix=CORE_PREFIX,
        default_sandbox_prefix=SANDBOX_PREFIX,
    )
    core_lid = rep["core_lattice_id"]
    sandbox_lid = rep["sandbox_lattice_id"]

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


def affect_after_listen_scene(
    state: dict,
    scene_id: str,
    *,
    scene: dict[str, Any] | None = None,
    caption_cluster: str = "",
    tick: int = 0,
) -> CoreAffectState:
    """Passive listen — theme/cluster bias only (no text oracle, wire-gap W5)."""
    zone = ensure_emotional_zone(state)
    core = CoreAffectState.from_dict(zone.get("core"))
    cluster = (caption_cluster or listen_theme_cluster(scene or {})).strip().lower()
    deltas = dict(_LISTEN_THEME_DELTAS.get(cluster, _LISTEN_THEME_DEFAULT))
    core.axes = _apply_deltas(core.axes, deltas)
    core.last_event = f"listen_scene:{cluster or scene_id}"
    core.tick = int(tick)
    zone["core"] = core.to_dict()
    return core


def listen_theme_cluster(scene: dict[str, Any]) -> str:
    """Map manifest metadata → coarse theme (collection, profile, tags)."""
    for key in ("collection", "profile", "playlist", "series"):
        raw = str(scene.get(key) or "").strip().lower()
        if raw:
            return raw.split("/")[0].split(":")[0]
    caption = str(scene.get("caption") or scene.get("chapter_title") or "").strip().lower()
    if any(word in caption for word in ("сон", "bedtime", "спать")):
        return "bedtime"
    if any(word in caption for word in ("эмоц", "emotion", "чувств")):
        return "emotions"
    return "listen"


_LISTEN_THEME_DEFAULT: dict[str, float] = {"arousal": 0.04}
_LISTEN_THEME_DELTAS: dict[str, dict[str, float]] = {
    "emotions": {"valence": 0.03, "arousal": 0.08},
    "bedtime": {"valence": 0.05, "arousal": -0.06, "security": 0.04},
    "speech": {"valence": 0.02, "arousal": 0.05},
    "listen": {"arousal": 0.04},
}


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
    if "arousal" in deltas:
        try:
            from casa.prisms.genetic import genetic_constant

            gain = float(genetic_constant(state, "surprise_gains.affect_arousal", 0.15))
            deltas["arousal"] = float(deltas["arousal"]) * (gain / 0.15)
        except Exception:
            pass
    if extra_deltas:
        deltas.update({k: float(v) for k, v in extra_deltas.items() if k in DEFAULT_AXES})
    try:
        from casa.prisms.neuromodulator import neuromodulator_is_active, scale_affect_event_deltas

        if neuromodulator_is_active(state):
            deltas = scale_affect_event_deltas(state, deltas)
    except ImportError:
        pass
    if event == "partner_trust":
        from casa.prisms.intelligence.partner_cues import bump_partner_trust

        bump_partner_trust(state)
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
    invited = float(core.episodic.get("dialog.repair_invited") or 0.0)
    repair_active = repair > 0 or invited > 0
    return {
        "valence": axes.valence,
        "arousal": axes.arousal,
        "security": axes.security,
        "repair_pending": repair_active,
        "repair_invited": invited > 0,
        "budget_scale": max(0.6, min(1.4, 1.0 + 0.25 * axes.arousal - 0.15 * repair)),
        "social_affinity_delta": int(round(8 * axes.security)),
        "honest_defer_bias": repair > 0 and axes.security < 0.45,
    }


def infer_partner_life_event(partner_text: str, *, query_intent: str = "") -> str | None:
    """Partner-only cues — safe before subject compose (ADR-0057)."""
    from casa.prisms.intelligence.partner_cues import infer_partner_life_event_name

    return infer_partner_life_event_name(partner_text, query_intent=query_intent)


def infer_life_event_from_turn(
    state: dict,
    *,
    partner_text: str,
    subject_reply: str,
    query_intent: str = "",
    disposition: str = "",
) -> str | None:
    """Lightweight event inference for dialogue tick wiring."""
    reply = (subject_reply or "").strip()
    try:
        from casa.prisms.defense.infer import infer_trauma_life_event

        trauma = infer_trauma_life_event(
            partner_text, subject_reply=subject_reply, query_intent=query_intent
        )
        if trauma:
            return trauma
    except ImportError:
        pass
    core = core_affect_state(state)
    partner_only = infer_partner_life_event(partner_text, query_intent=query_intent)
    if partner_only and not reply:
        return partner_only
    if disposition in {"defer", "refuse"} and not reply:
        return "self_failure"
    if not reply and query_intent in {"math", "social", "general", "explain"}:
        return "self_failure"
    if reply and core.episodic.get("dialog.repair_pending"):
        return "self_repair_success"
    return None
