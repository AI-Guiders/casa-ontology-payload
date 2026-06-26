#!/usr/bin/env python3
"""Motor speech efferent + self-listen loop tests (ADR-0082)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from casa.body.speech_tract import read_efferent_cue
from casa.domain.motor_speech_plan import self_listen_aud_concept_id
from casa.prisms.auditory.imprint import imprint_auditory_window
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.motor.speech_compose import collect_field_motor_candidates, compose_motor_units
from casa.prisms.motor.speech_tick import maybe_motor_speech_on_tick
from casa.sensory.load_wav import write_synthetic_contour_wav


def _seed_listen_on_field(state: dict, store: Path, *, scene_id: str = "lab-babble") -> None:
    wav = store / "seed_listen.wav"
    write_synthetic_contour_wav(wav)
    imprint_auditory_window(state, wav, scene_id=scene_id, window_id=f"{scene_id}-w0")


def test_babble_requires_field_material() -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    assert compose_motor_units(state, tick=1, intent="babble") == []
    assert collect_field_motor_candidates(state) == []


def test_babble_draws_from_auditory_imprint() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        _seed_listen_on_field(state, store)
        units = compose_motor_units(state, tick=2, intent="babble")
        assert units
        assert all(u.startswith("A:") for u in units)


def test_motor_speech_babble_loop() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        _seed_listen_on_field(state, store)
        rep = maybe_motor_speech_on_tick(store, state, tick=3, force=True)
        assert rep.get("spoken") is True
        assert rep.get("units")
        plan = rep.get("plan") or {}
        plan_id = str(plan.get("plan_id") or "")
        assert plan_id
        cue = read_efferent_cue(store)
        assert cue is not None
        assert cue.get("status") == "done"
        assert self_listen_aud_concept_id(plan_id) == str(rep.get("self_listen", {}).get("aud_concept_id"))
        assert state.get("_motor_self_listen", {}).get("plan_id") == plan_id
        block = state.get("_perceptual_turn") or {}
        assert block.get("motor_active") is True
