#!/usr/bin/env python3
"""Motor speech efferent + self-listen loop tests (ADR-0082)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from casa.body.speech_tract import read_efferent_cue
from casa.domain.motor_speech_plan import self_listen_aud_concept_id
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.motor.speech_tick import maybe_motor_speech_on_tick


def test_motor_speech_babble_loop() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        state["motor_speech"] = {"enabled": True, "babble": True}
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
