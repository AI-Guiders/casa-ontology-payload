#!/usr/bin/env python3
"""Teacher pedagogy maps + paradigm LTM."""

from __future__ import annotations

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.visual.paradigm_ltm import co_occur_groups_from_events, paradigm_ltm_report
from casa.prisms.visual.phrase_compose import load_phrase_events
from teacher_pedagogy import (
    MATH_PALOCHKI_PROBE,
    all_literacy_stages_have_probe,
    all_visual_stages_have_probe,
    stage_probe_for,
)
from casa.domain.teacher_gate import GateKind


def test_all_literacy_stages_mapped():
    assert all_literacy_stages_have_probe()


def test_all_visual_stages_mapped():
    assert all_visual_stages_have_probe()


def test_lexical_stage_uses_agent_ksa():
    spec = stage_probe_for("lessons/lexical-cards-ru", "stage-01-a-ya")
    assert spec is not None
    assert spec.gate_kind is GateKind.AGENT_KSA
    assert spec.script == "probe_stage_quiz.py"


def test_math_palochki_is_sidecar():
    assert MATH_PALOCHKI_PROBE.gate_kind is GateKind.SIDECAR_SPEC


def test_paradigm_co_occur_groups():
    entries = load_phrase_events()
    groups = co_occur_groups_from_events(entries)
    assert groups
    assert all(len(g["slugs"]) >= 2 for g in groups)


def test_paradigm_ltm_report_empty_store():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    rep = paradigm_ltm_report(state)
    assert rep["total_clusters"] >= 1
    assert rep["complete_clusters"] == 0
