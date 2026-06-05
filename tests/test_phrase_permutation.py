#!/usr/bin/env python3
"""Phrase permutation equivalence (ADR-0033)."""

from __future__ import annotations

from casa.prisms.visual.phrase_compose import compose_phrase_verdict
from casa.prisms.visual.phrase_permutation import check_permutation_equiv


def _wash_entry() -> dict:
    return {
        "event_id": "lang.event.transitive.wash.v0",
        "surfaces": ["Мама мыла раму", "Мыла раму мама", "Раму мама мыла"],
        "words": [
            {"role": "agent", "surface": "мама"},
            {"role": "verb", "surface": "мыла"},
            {"role": "patient", "surface": "раму"},
        ],
        "agreement": [{"agent": "мама", "verb": "мыла"}],
    }


def _reads() -> list[dict]:
    return [
        {"surface": "мама", "verdict": "analytic_know"},
        {"surface": "мыла", "verdict": "analytic_know"},
        {"surface": "раму", "verdict": "analytic_know"},
    ]


def test_permutation_equiv_ok():
    entry = _wash_entry()

    def compose(_surface: str) -> dict:
        return compose_phrase_verdict(_reads(), entry, check_questions=False)

    out = check_permutation_equiv(entry, compose)
    assert out["permutation_know"]
    assert len(out["surfaces"]) == 3


def test_permutation_equiv_fail():
    entry = _wash_entry()

    def compose(surface: str) -> dict:
        reads = _reads()
        if "мыл" in surface.lower() and "мама" in surface.lower():
            reads[1] = {"surface": "мыл", "verdict": "analytic_know"}
        return compose_phrase_verdict(reads, entry, check_questions=False)

    out = check_permutation_equiv(entry, compose)
    assert not out["permutation_know"]
