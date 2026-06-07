"""Emotional Zone — limbic core + agent sandbox (ADR-0060)."""

from casa.prisms.affect.model import (
    CORE_PREFIX,
    DEFAULT_CORE_LATTICE,
    DEFAULT_SANDBOX_LATTICE,
    AffectAxes,
    CoreAffectState,
    SandboxExperiment,
)
from casa.prisms.affect.zone import (
    affect_after_turn,
    affect_compose_bias,
    core_affect_state,
    ensure_emotional_zone,
    infer_life_event_from_turn,
    promote_sandbox_experiment,
    sandbox_record_experiment,
    spawn_emotional_zone,
)

__all__ = [
    "CORE_PREFIX",
    "DEFAULT_CORE_LATTICE",
    "DEFAULT_SANDBOX_LATTICE",
    "AffectAxes",
    "CoreAffectState",
    "SandboxExperiment",
    "affect_after_turn",
    "affect_compose_bias",
    "core_affect_state",
    "ensure_emotional_zone",
    "infer_life_event_from_turn",
    "promote_sandbox_experiment",
    "sandbox_record_experiment",
    "spawn_emotional_zone",
]
