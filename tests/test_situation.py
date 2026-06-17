"""Situation fingerprint: a deterministic, language-independent handle for a meaning graph.

Paraphrases (synonym predicates, edge order, language) collapse to one id; a sub-situation
is contained in the larger one (fingerprint of "apple on table" inside "apple on table near
window"); distinct situations differ.
"""

from __future__ import annotations

import json

from casa.curriculum.concept_net import teach_concept_net
from casa.curriculum.situation import (
    contains,
    gate_situation,
    graph_from_predicates,
    same_situation,
    similarity,
    situation_fingerprint,
)
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


def test_paraphrases_share_one_fingerprint() -> None:
    state = _state()
    ids = {
        situation_fingerprint(state, LAT, [(p, "яблоко", "стол")])["id"]
        for p in ("лежит", "стоит", "на", "находится")
    }
    assert len(ids) == 1  # synonym predicates -> one situation id
    # language-independent: the English phrasing lands on the same id
    assert situation_fingerprint(state, LAT, [("on", "apple", "table")])["id"] == next(iter(ids))


def test_subsituation_is_contained() -> None:
    state = _state()
    inner = graph_from_predicates(state, LAT, [("на", "яблоко", "стол")])
    outer = graph_from_predicates(state, LAT, [("на", "яблоко", "стол"), ("у", "стол", "окно")])
    assert contains(outer, inner) is True
    assert contains(inner, outer) is False
    assert 0.0 < similarity(inner, outer) < 1.0


def test_distinct_situations_differ() -> None:
    state = _state()
    a = graph_from_predicates(state, LAT, [("на", "яблоко", "стол")])
    b = graph_from_predicates(state, LAT, [("в", "яблоко", "коробка")])
    assert same_situation(a, b) is False
    assert situation_fingerprint(state, LAT, [("на", "яблоко", "стол")])["id"] != \
        situation_fingerprint(state, LAT, [("в", "яблоко", "коробка")])["id"]


def test_situation_gate() -> None:
    state = _state()
    rep = gate_situation(
        state, LAT,
        paraphrase_sets=[
            [[("лежит", "яблоко", "стол")], [("на", "яблоко", "стол")], [("on", "apple", "table")]],
            [[("ест", "собака", "мясо")], [("eat", "dog", "meat")]],
        ],
        nested_pairs=[([("на", "яблоко", "стол"), ("у", "стол", "окно")], [("на", "яблоко", "стол")])],
        distinct_pairs=[([("на", "яблоко", "стол")], [("в", "яблоко", "коробка")])],
    )
    assert rep["passed"] is True
    assert rep["paraphrases_collapse"] and rep["nesting_holds"] and rep["distinct_differ"]
