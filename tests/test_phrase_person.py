#!/usr/bin/env python3
"""L2 person in phrase agreement."""

from __future__ import annotations

from casa.prisms.visual.phrase_compose import compose_phrase_verdict, load_phrase_events
from casa.prisms.visual.phrase_person import check_person_agreement, person_id_for_agent_surface


def test_person_surface_lookup():
    assert person_id_for_agent_surface("она") == "lang.meta.grammar.person.3sg.fem"
    assert check_person_agreement("она", "lang.meta.grammar.person.3sg.fem")


def test_wash_3sg_fem_event():
    entry = next(
        e for e in load_phrase_events() if e.get("event_id") == "lang.event.transitive.wash.3sg_fem.v0"
    )
    reads = [{"surface": w["surface"], "verdict": "analytic_know"} for w in entry["words"]]
    out = compose_phrase_verdict(reads, entry)
    assert out["phrase_know"]


def test_person_mismatch_fails():
    entry = next(
        e for e in load_phrase_events() if e.get("event_id") == "lang.event.transitive.wash.3sg_fem.v0"
    )
    reads = [
        {"surface": "он", "verdict": "analytic_know"},
        {"surface": "мыл", "verdict": "analytic_know"},
        {"surface": "раму", "verdict": "analytic_know"},
    ]
    out = compose_phrase_verdict(reads, entry)
    assert out["verdict"] in ("agreement_fail", "slot_fail")
