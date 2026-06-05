#!/usr/bin/env python3
"""Question-frame phrase gate (ADR-0033 §6)."""

from __future__ import annotations

from casa.prisms.visual.phrase_compose import bind_slots, compose_phrase_verdict
from casa.prisms.visual.phrase_question import check_question_frames, compose_question_verdict


def _slots() -> dict:
    reads = [
        {"surface": "мама", "verdict": "analytic_know"},
        {"surface": "мыла", "verdict": "analytic_know"},
        {"surface": "раму", "verdict": "analytic_know"},
    ]
    words = [
        {"role": "agent", "surface": "мама"},
        {"role": "verb", "surface": "мыла"},
        {"role": "patient", "surface": "раму"},
    ]
    return bind_slots(reads, words)["slots"]


def test_question_frames_wash():
    slots = _slots()
    frames = [
        {
            "anchor_surface": "мыла",
            "question_id": "lang.meta.grammar.question.who",
            "expected_surface": "мама",
            "expected_role": "agent",
        },
        {
            "anchor_surface": "мыла",
            "question_id": "lang.meta.grammar.question.what",
            "expected_surface": "раму",
            "expected_role": "patient",
        },
    ]
    out = check_question_frames(slots, frames)
    assert out["ok"]


def test_compose_phrase_with_questions():
    entry = {
        "event_id": "lang.event.transitive.wash.v0",
        "words": [
            {"role": "agent", "surface": "мама"},
            {"role": "verb", "surface": "мыла"},
            {"role": "patient", "surface": "раму"},
        ],
        "agreement": [{"agent": "мама", "verb": "мыла"}],
        "question_frames": [
            {
                "anchor_surface": "мыла",
                "question_id": "lang.meta.grammar.question.who",
                "expected_surface": "мама",
                "expected_role": "agent",
            }
        ],
    }
    reads = [
        {"surface": "мама", "verdict": "analytic_know"},
        {"surface": "мыла", "verdict": "analytic_know"},
        {"surface": "раму", "verdict": "analytic_know"},
    ]
    out = compose_phrase_verdict(reads, entry)
    assert out["phrase_know"]
    assert out["question"]["question_know"]


def test_question_fail_wrong_patient():
    slots = _slots()
    slots["patient"]["surface"] = "маму"
    entry = {
        "event_id": "lang.event.transitive.wash.v0",
        "question_frames": [
            {
                "anchor_surface": "мыла",
                "question_id": "lang.meta.grammar.question.what",
                "expected_surface": "раму",
                "expected_role": "patient",
            }
        ],
    }
    out = compose_question_verdict(slots, entry)
    assert not out["question_know"]
