"""Structural analogy: «эта ситуация как та» by graph structure, not shared concepts.

«кот на стуле» ~ «яблоко на столе» — same relation on(positionable, support), consistent
type-compatible concept mapping, zero shared concepts. Different relations are not analogous.
"""

from __future__ import annotations

import json

from casa.curriculum.analogy import analogous, find_analogy, recall_analogous
from casa.curriculum.concept_net import teach_concept_net
from casa.curriculum.parse import parse_graph
from casa.curriculum.situation_memory import new_memory, remember
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


def test_structural_analogy_across_disjoint_concepts() -> None:
    state = _state()
    g = lambda t: parse_graph(state, LAT, t)
    assert find_analogy(state, LAT, g("кот на стуле"), g("яблоко на столе")) == {
        "lex.cat": "lex.apple", "lex.chair": "lex.table"
    }
    # chained structure maps consistently
    assert find_analogy(state, LAT, g("кот на стуле у окна"), g("книга на столе у двери")) == {
        "lex.cat": "lex.book", "lex.chair": "lex.table", "lex.window": "lex.door"
    }
    # transitive structure
    assert find_analogy(state, LAT, g("собака ест мясо"), g("человек ест яблоко")) == {
        "lex.dog": "lex.person", "lex.meat": "lex.apple"
    }


def test_different_relations_are_not_analogous() -> None:
    state = _state()
    g = lambda t: parse_graph(state, LAT, t)
    assert analogous(state, LAT, g("кот на стуле"), g("собака ест мясо")) is False


def test_recall_analogous_finds_same_structure() -> None:
    state = _state()
    g = lambda t: parse_graph(state, LAT, t)
    m = new_memory()
    for t in ("книга на столе", "собака ест мясо", "студент читает книгу"):
        remember(m, g(t), label=t)
    hits = recall_analogous(state, LAT, m, g("кот на стуле"))  # on(physical, support)
    labels = {rec["label"] for rec, _ in hits}
    assert "книга на столе" in labels          # structural match, no shared concept
    assert "собака ест мясо" not in labels      # different relation
    rec, mapping = next((r, mp) for r, mp in hits if r["label"] == "книга на столе")
    assert mapping == {"lex.cat": "lex.book", "lex.chair": "lex.table"}
