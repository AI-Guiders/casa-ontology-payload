#!/usr/bin/env python3
"""Agency gate for motor phonation (ADR-0082)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from casa.domain.subject_agency import SubjectAction
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.motor.speech_disposition import resolve_motor_phonation_disposition
from casa.prisms.motor.speech_tick import maybe_motor_speech_on_tick


def test_phonation_follows_symbolic_compose() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        state["subject"] = {"subject_mode": True}
        disp = resolve_motor_phonation_disposition(
            store,
            state,
            dialogue_rep={"reply_text": "привет", "subject_mode": True},
            task=None,
            mem_prep={"goal_arbiter": {"subject_disposition": {"action": SubjectAction.ACCEPT.value}}},
        )
        assert disp.should_phonate is True
        assert disp.intent == "parallel_compose"


def test_phonation_skips_without_agency() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        rep = maybe_motor_speech_on_tick(store, state, tick=1, dialogue_rep={})
        assert rep.get("skipped") is True
        assert rep.get("reason") == "not_subject_mode"
