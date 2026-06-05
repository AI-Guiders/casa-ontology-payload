#!/usr/bin/env python3
"""Ditransitive give.v0 phrase compose (ADR-0033 valency)."""

from __future__ import annotations

from casa.prisms.visual.phrase_compose import bind_slots, compose_phrase_verdict
from casa.prisms.visual.phrase_compose import load_phrase_events


def test_give_event_registry():
    entries = load_phrase_events()
    give = next(e for e in entries if e.get("event_id") == "lang.event.ditransitive.give.v0")
    roles = {w["role"] for w in give["words"]}
    assert roles == {"agent", "verb", "recipient", "patient"}


def test_give_compose_four_slots():
    reads = [
        {"surface": "мама", "verdict": "analytic_know"},
        {"surface": "дала", "verdict": "analytic_know"},
        {"surface": "Маше", "verdict": "analytic_know"},
        {"surface": "книгу", "verdict": "analytic_know"},
    ]
    words = [
        {"role": "agent", "surface": "мама"},
        {"role": "verb", "surface": "дала"},
        {"role": "recipient", "surface": "Маше"},
        {"role": "patient", "surface": "книгу"},
    ]
    bind = bind_slots(reads, words)
    assert bind["complete"]
    entry = {
        "event_id": "lang.event.ditransitive.give.v0",
        "words": words,
        "agreement": [{"agent": "мама", "verb": "дала"}],
        "question_frames": [
            {
                "anchor_surface": "дала",
                "question_id": "lang.meta.grammar.question.to_whom",
                "expected_surface": "Маше",
                "expected_role": "recipient",
            }
        ],
    }
    out = compose_phrase_verdict(reads, entry)
    assert out["phrase_know"]
