#!/usr/bin/env python3
"""Tests for aud↔vis sleep bridges (wire-gap W1)."""

from __future__ import annotations

from casa.domain.auditory_tract import LATTICE_AUDIO_SPECTRUM
from casa.domain.visual_tract import LATTICE_V1_LUM, PREFIX_VIS_LUM
from casa.prisms.auditory.bridge_vis import bind_av_coactive_on_tick, extract_emergent_aud_vis_bridges
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_extract_aud_vis_co_occurs_same_scene() -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    episodes = [
        {
            "id": "ep-a",
            "lattice_id": LATTICE_AUDIO_SPECTRUM,
            "concept_id": "aud.window.ch00-b002",
            "scene": "lalabook-ch00",
        },
        {
            "id": "ep-v",
            "lattice_id": LATTICE_V1_LUM,
            "concept_id": f"{PREFIX_VIS_LUM}frame.ch00-b002",
            "scene": "lalabook-ch00",
        },
    ]
    out = extract_emergent_aud_vis_bridges({}, episodes, state, copies=2)
    assert len(out) == 1
    assert out[0]["aud_concept_id"] == "aud.window.ch00-b002"
    assert out[0]["vis_concept_id"].startswith(PREFIX_VIS_LUM)


def test_bind_av_coactive_on_tick_mints_bridge() -> None:
    from casa.prisms.perceptual import perceptual_prepare_life_sensory

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    perceptual_prepare_life_sensory(
        state,
        stream_id="ch00",
        seq=1,
        t_rel=9.0,
        visual_delta=0.3,
        audio_active=True,
        audio_placements=3,
        aud_window_id="ch00-tick0001",
        vis_frame_id="ch00-tick0001",
    )
    rep = bind_av_coactive_on_tick(state)
    assert rep is not None
    assert rep.get("bound") is True
    assert rep.get("aud_concept_id") == "aud.window.ch00-tick0001"


def test_extract_aud_vis_skips_different_scene() -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    episodes = [
        {
            "id": "ep-a",
            "lattice_id": LATTICE_AUDIO_SPECTRUM,
            "concept_id": "aud.window.a",
            "scene": "scene-a",
        },
        {
            "id": "ep-v",
            "lattice_id": LATTICE_V1_LUM,
            "concept_id": f"{PREFIX_VIS_LUM}frame.x",
            "scene": "scene-b",
        },
    ]
    assert extract_emergent_aud_vis_bridges({}, episodes, state) == []
