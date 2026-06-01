#!/usr/bin/env python3
"""ADR-0024: prism_control_thalamus bootstrap + tick phase."""

from __future__ import annotations

from casa.prisms.control.thalamus import ensure_control_thalamus, thalamus_tick_phase
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_router import tick_prepare_memory
from casa.prisms.memory.prism_spawn import ensure_default_router_and_hot, spawn_prism
from casa.prisms.shared.prism_state import PRISM_CONTROL_THALAMUS, active_control_prism_id, prism_block


def test_ensure_control_thalamus_spawns_stack():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_control_thalamus(state)
    block = prism_block(state, PRISM_CONTROL_THALAMUS)
    lats = block.get("lattices") or {}
    assert lats
    assert "lattice_thal_relay" in lats or "control-thal-relay" in lats


def test_thalamus_tick_phase_wake_and_vis_relay():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_default_router_and_hot(state)
    rep = thalamus_tick_phase(state, modality="vis", cue="кадр")
    assert rep["mode"] == "wake"
    assert rep["relay"] == "port.thal.forward.vis"
    assert active_control_prism_id(state) == PRISM_CONTROL_THALAMUS
    assert state["sn"]["relay_open"] == ["vis"]


def test_tick_prepare_includes_thalamus():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_default_router_and_hot(state)
    prep = tick_prepare_memory(state, cue="тест", modality="t9")
    assert "thalamus" in prep
    assert prep["thalamus"]["prism_id"] == PRISM_CONTROL_THALAMUS
