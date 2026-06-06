#!/usr/bin/env python3
"""Circumstantial slots P2 (ADR-0033 §6.1)."""

from __future__ import annotations

from casa.prisms.visual.phrase_circumstantial import check_circumstantials
from casa.prisms.visual.phrase_compose import bind_slots, compose_phrase_verdict


def _reads() -> list[dict]:
    return [
        {"surface": "мама", "verdict": "analytic_know"},
        {"surface": "вчера", "verdict": "analytic_know"},
        {"surface": "быстро", "verdict": "analytic_know"},
        {"surface": "мыла", "verdict": "analytic_know"},
        {"surface": "раму", "verdict": "analytic_know"},
    ]


def test_circumstantial_slots_ok():
    words = [
        {"role": "agent", "surface": "мама"},
        {"role": "circumstantial.time", "surface": "вчера"},
        {"role": "circumstantial.manner", "surface": "быстро"},
        {"role": "verb", "surface": "мыла"},
        {"role": "patient", "surface": "раму"},
    ]
    slots = bind_slots(_reads(), words)["slots"]
    specs = [
        {"kind": "time", "role": "circumstantial.time", "surface": "вчера"},
        {"kind": "manner", "role": "circumstantial.manner", "surface": "быстро"},
    ]
    out = check_circumstantials(slots, specs)
    assert out["ok"]


def test_compose_phrase_with_circumstantials():
    entry = {
        "event_id": "lang.event.transitive.wash.circ.v0",
        "words": [
            {"role": "agent", "surface": "мама"},
            {"role": "circumstantial.time", "surface": "вчера"},
            {"role": "circumstantial.manner", "surface": "быстро"},
            {"role": "verb", "surface": "мыла"},
            {"role": "patient", "surface": "раму"},
        ],
        "agreement": [{"agent": "мама", "verb": "мыла"}],
        "circumstantials": [
            {"kind": "time", "role": "circumstantial.time", "surface": "вчера"},
            {"kind": "manner", "role": "circumstantial.manner", "surface": "быстро"},
        ],
        "question_frames": [
            {
                "anchor_surface": "мыла",
                "question_id": "lang.meta.grammar.question.when",
                "expected_surface": "вчера",
                "expected_role": "circumstantial.time",
            }
        ],
    }
    out = compose_phrase_verdict(_reads(), entry)
    assert out["phrase_know"]
    assert out["circumstantials"]["ok"]
