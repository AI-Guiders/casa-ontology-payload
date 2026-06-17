"""Situation memory: store fingerprints, recall by identity, containment, similarity.

«Видел ли я такую конфигурацию?» — exact recall is paraphrase/language-invariant for
single-relation clauses; recall_containing finds stored super-situations of a sub-graph;
recall_similar ranks by edge overlap.
"""

from __future__ import annotations

import json

from casa.curriculum.concept_net import teach_concept_net
from casa.curriculum.parse import parse_graph
from casa.curriculum.situation_memory import (
    gate_situation_memory,
    new_memory,
    recall_containing,
    recall_similar,
    remember,
    seen,
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


def _mem(state: dict) -> dict:
    m = new_memory()
    for t in ["яблоко на столе у окна", "собака ест мясо", "книга на столе", "студент читает книгу"]:
        remember(m, parse_graph(state, LAT, t), label=t)
    return m


def test_seen_is_paraphrase_and_language_invariant() -> None:
    state = _state()
    m = new_memory()
    remember(m, parse_graph(state, LAT, "яблоко на столе"))
    # single-relation paraphrases (order + language) recall the same stored situation
    assert seen(m, parse_graph(state, LAT, "на столе яблоко")) is not None
    assert seen(m, parse_graph(state, LAT, "apple on the table")) is not None
    # an unstored configuration is not seen
    assert seen(m, parse_graph(state, LAT, "собака ест мясо")) is None


def test_recall_containing_finds_super_situation() -> None:
    state = _state()
    m = _mem(state)
    hits = recall_containing(m, parse_graph(state, LAT, "яблоко на столе"))
    assert any(r["label"] == "яблоко на столе у окна" for r in hits)  # the stored super-situation


def test_recall_similar_ranks_by_overlap() -> None:
    state = _state()
    m = _mem(state)
    ranked = recall_similar(m, parse_graph(state, LAT, "apple on the table"), top=4)
    assert ranked[0][0]["label"] == "яблоко на столе у окна"  # shares on(apple,table)
    assert ranked[0][1] > ranked[-1][1]                       # ordered by similarity


def test_situation_memory_gate() -> None:
    state = _state()
    m = _mem(state)
    rep = gate_situation_memory(
        m,
        seen_graphs=[parse_graph(state, LAT, "собака ест мясо"), parse_graph(state, LAT, "книга на столе")],
        novel_graph=parse_graph(state, LAT, "кот на столе"),
        sub_graph=parse_graph(state, LAT, "яблоко на столе"),
        super_graph=parse_graph(state, LAT, "яблоко на столе у окна"),
    )
    assert rep["passed"] is True
