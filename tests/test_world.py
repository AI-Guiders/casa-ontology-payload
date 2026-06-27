"""build_meaning_state: one call yields a conceptual-network state ready for round-trip.

This is what the chat's /meaning command uses — ontology + morphology + grammars taught,
so text -> graph -> text works out of the box.
"""

from __future__ import annotations

from casa.curriculum.parse import parse_triples
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.world import build_meaning_state


def test_meaning_state_supports_round_trip() -> None:
    state, lat = build_meaning_state()
    assert lat == "schema-math"
    # parses to one meaning and renders back in both languages
    assert parse_triples(state, lat, "яблоко лежит на столе") == [("on", "concept.apple", "concept.table")]
    tr = translate_through_meaning(state, lat, "на столе яблоко")
    assert tr == {"ru": "Яблоко на столе.", "en": "The apple is on the table."}
    assert translate_through_meaning(state, lat, "apple on the table")["ru"] == "Яблоко на столе."


def test_meaning_state_validates_and_refuses() -> None:
    from casa.curriculum.concept_net import validate

    state, lat = build_meaning_state()
    assert validate(state, lat, "on", "яблоко", "стол")["valid"] is True
    assert validate(state, lat, "on", "идея", "стол")["valid"] is False
