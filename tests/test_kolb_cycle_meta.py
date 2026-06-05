#!/usr/bin/env python3
"""Domain-neutral Kolb cycle — dispatch only."""

from __future__ import annotations

from pathlib import Path

from casa.domain.kolb_cycle import KolbContext, KolbPhase, maybe_kolb_revise_tick
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions


def test_kolb_phase_enum_maps_executor_steps():
    assert KolbPhase.REFLECTIVE_OBSERVATION.value == "reflective_observation"


def test_maybe_kolb_revise_returns_none_without_signals():
    rep = maybe_kolb_revise_tick(
        KolbContext(
            store_dir=Path("/none"),
            state={},
            wm=WorkingMemory(),
            control=ControlExtensions(
                predicted=(),
                surprise=(),
                prediction_error=0.0,
                dan_mask=(),
                sparse_ratio=0.0,
                masked_digest=(),
                value=0.0,
            ),
            hippo_ep=None,
            cue="",
            min_surprise_value=0.5,
        )
    )
    assert rep is None
