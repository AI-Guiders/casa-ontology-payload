#!/usr/bin/env python3
"""Tests for motor↔heard bridges (ADR-0082)."""

from __future__ import annotations

from casa.domain.auditory_tract import LATTICE_AUDIO_SPECTRUM
from casa.domain.motor_speech_plan import motor_plan_concept_id, self_listen_aud_concept_id
from casa.prisms.auditory.bridge_motor import bind_motor_heard_on_tick, extract_emergent_motor_heard_bridges
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_extract_motor_heard_same_plan() -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    plan_id = "abc123"
    motor_cid = motor_plan_concept_id(plan_id)
    aud_cid = self_listen_aud_concept_id(plan_id)
    episodes = [
        {
            "id": "ep-m",
            "lattice_id": LATTICE_AUDIO_SPECTRUM,
            "concept_id": motor_cid,
            "scene": "self",
        },
        {
            "id": "ep-a",
            "lattice_id": LATTICE_AUDIO_SPECTRUM,
            "concept_id": aud_cid,
            "scene": "self",
        },
    ]
    out = extract_emergent_motor_heard_bridges({}, episodes, state, copies=2)
    assert len(out) == 1
    assert out[0]["motor_concept_id"] == motor_cid
    assert out[0]["aud_concept_id"] == aud_cid


def test_bind_motor_heard_on_tick_mints_bridge() -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    plan_id = "plan001"
    state["_motor_self_listen"] = {
        "plan_id": plan_id,
        "aud_window_id": f"self-{plan_id}",
        "units": ["A:ph:ма"],
        "tick": 1,
    }
    rep = bind_motor_heard_on_tick(state)
    assert rep is not None
    assert rep.get("bound") is True
    assert rep.get("motor_concept_id") == motor_plan_concept_id(plan_id)
