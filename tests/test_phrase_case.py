#!/usr/bin/env python3
"""Case frames via question-frames (ADR-0033)."""

from __future__ import annotations

from casa.prisms.visual.phrase_case import check_case_frames, compose_case_verdict
from casa.prisms.visual.phrase_compose import bind_slots, compose_phrase_verdict, load_phrase_events


def test_case_frames_wash_v0():
    entry = next(
        e for e in load_phrase_events() if e.get("event_id") == "lang.event.transitive.wash.v0"
    )
    reads = [{"surface": w["surface"], "verdict": "analytic_know"} for w in entry["words"]]
    slots = bind_slots(reads, entry["words"])["slots"]
    out = compose_case_verdict(slots, entry)
    assert out["case_know"]


def test_case_fail_missing_slot():
    check = check_case_frames(
        {"agent": {"surface": "мама"}},
        [{"role": "patient", "case_id": "lang.meta.grammar.case.acc", "question_id": "q"}],
    )
    assert not check["ok"]


def test_compose_includes_case_gate():
    entry = next(
        e for e in load_phrase_events() if e.get("event_id") == "lang.event.transitive.wash.v0"
    )
    reads = [{"surface": w["surface"], "verdict": "analytic_know"} for w in entry["words"]]
    out = compose_phrase_verdict(reads, entry)
    assert out["phrase_know"]
    assert out.get("case", {}).get("case_know")
