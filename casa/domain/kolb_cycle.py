#!/usr/bin/env python3
"""Kolb learning cycle — domain-neutral META (ADR-0034).

Concrete experience → Reflect → Abstract → Active experiment.
Domains plug in only at *revise* (phases 2–4); the loop shape is the same for
literacy, math, grammar, motor, J0.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions


class KolbPhase(str, Enum):
    CONCRETE_EXPERIENCE = "concrete_experience"
    REFLECTIVE_OBSERVATION = "reflective_observation"
    ABSTRACT_CONCEPTUALIZATION = "abstract_conceptualization"
    ACTIVE_EXPERIMENTATION = "active_experimentation"


# ADR-0034 step mapping (same for every domain)
KOLB_TO_EXECUTOR_STEP: dict[KolbPhase, str] = {
    KolbPhase.CONCRETE_EXPERIENCE: "4_synthesize",
    KolbPhase.REFLECTIVE_OBSERVATION: "5_verify_fail",
    KolbPhase.ABSTRACT_CONCEPTUALIZATION: "2_3_classify_methods",
    KolbPhase.ACTIVE_EXPERIMENTATION: "4_synthesize_retry",
}


@dataclass(frozen=True, slots=True)
class KolbContext:
    """Inputs for one Kolb revise attempt — no domain fields here."""

    store_dir: Path
    state: dict
    wm: WorkingMemory
    control: ControlExtensions
    hippo_ep: dict[str, Any] | None
    cue: str
    min_surprise_value: float


KolbReviseHandler = Callable[[KolbContext], dict[str, Any] | None]


def _handlers() -> tuple[KolbReviseHandler, ...]:
    from casa.prisms.tick.kolb_handlers import (
        revise_crosslink_vis_lex,
        revise_math_pattern,
        revise_route_capability,
    )

    return (
        revise_crosslink_vis_lex,
        revise_math_pattern,
        revise_route_capability,
    )


def maybe_kolb_revise_tick(ctx: KolbContext) -> dict[str, Any] | None:
    """Active experimentation: try domain handlers until one revises field/routes."""
    if not ctx.control.surprise and not ctx.hippo_ep:
        return None

    from casa.prisms.tick.kolb_relink_tick import agent_wants_kolb

    if ctx.control.value < ctx.min_surprise_value and not agent_wants_kolb(ctx.store_dir):
        return None

    for handler in _handlers():
        rep = handler(ctx)
        if rep is None:
            continue
        if rep.get("skipped"):
            continue
        return {
            "kolb_phase": KolbPhase.ACTIVE_EXPERIMENTATION.value,
            "domain": rep.get("domain"),
            **rep,
        }
    return None


def kolb_phase_from_surprise(*, has_surprise: bool, revised: bool) -> str | None:
    if revised:
        return KolbPhase.ACTIVE_EXPERIMENTATION.value
    if has_surprise:
        return KolbPhase.REFLECTIVE_OBSERVATION.value
    return None
