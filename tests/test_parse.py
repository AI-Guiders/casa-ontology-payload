"""Domain parser: a controlled clause -> meaning graph -> fingerprint (text closes the loop).

Three phrasings of one situation parse to the same triples and the same fingerprint, in
either language; chained prepositions and S-V-O parse correctly; inflected words resolve.
Honest scope: rule-based, domain clauses — not open-domain understanding.
"""

from __future__ import annotations

import json

from casa.curriculum.concept_net import teach_concept_net
from casa.curriculum.parse import parse_fingerprint, parse_triples, resolve_token
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
NET = REPO_ROOT / "lab/curriculum/concept-net-base-v1.json"
LAT = "schema-math"


def _state() -> dict:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    teach_concept_net(state, LAT, json.loads(NET.read_text(encoding="utf-8")), bundle=bundle)
    return state


def test_inflected_words_resolve_to_concepts() -> None:
    state = _state()
    assert resolve_token(state, LAT, "столе") == "concept.table"   # prepositional case
    assert resolve_token(state, LAT, "рыбу") == "concept.fish"      # accusative
    assert resolve_token(state, LAT, "окна") == "concept.window"    # genitive
    assert resolve_token(state, LAT, "apple") == "concept.apple"    # English base


def test_paraphrases_parse_to_one_situation() -> None:
    state = _state()
    phrasings = [
        "яблоко на столе", "яблоко лежит на столе", "на столе яблоко",
        "на столе лежит яблоко", "apple on the table",
    ]
    triples = [parse_triples(state, LAT, t) for t in phrasings]
    assert all(t == [("on", "concept.apple", "concept.table")] for t in triples)
    ids = {parse_fingerprint(state, LAT, t)["id"] for t in phrasings}
    assert len(ids) == 1  # one situation fingerprint across order and language


def test_chained_prepositions_and_svo() -> None:
    state = _state()
    assert parse_triples(state, LAT, "яблоко на столе у окна") == [
        ("on", "concept.apple", "concept.table"), ("near", "concept.table", "concept.window")
    ]
    assert parse_triples(state, LAT, "собака ест мясо") == [("eat", "concept.dog", "concept.meat")]
    assert parse_triples(state, LAT, "студент читает книгу") == [("read", "concept.student", "concept.book")]


def test_nested_situation_from_text() -> None:
    state = _state()
    from casa.curriculum.situation import contains
    from casa.curriculum.parse import parse_graph

    inner = parse_graph(state, LAT, "яблоко на столе")
    outer = parse_graph(state, LAT, "яблоко на столе у окна")
    assert contains(outer, inner) is True
    assert contains(inner, outer) is False
