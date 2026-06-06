#!/usr/bin/env python3
"""phrase_compose_slice + pilot_paradigm_gate."""

from __future__ import annotations

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.visual.phrase_compose import load_phrase_events, phrase_compose_slice
from casa.prisms.visual.paradigm_ltm import pilot_paradigm_gate


def test_phrase_compose_slice_uses_first_example():
    entries = load_phrase_events()
    poss = next(e for e in entries if e.get("event_id") == "lang.event.possessive.pronoun.sg.v0")
    sliced = phrase_compose_slice(poss)
    assert sliced.get("words")
    assert sliced["words"][0].get("role") == "referent"


def test_pilot_paradigm_gate_empty_store():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    rep = pilot_paradigm_gate(state)
    assert rep["ok"] is False
    assert rep["complete_sets"] == 0
