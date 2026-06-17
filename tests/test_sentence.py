"""Sentence-level generation: build an English clause from a RU meaning triple.

Stacks the glossary + 3sg agreement + an induced, field-stored S-V-O order. The gate
checks generalisation to held-out triples, a negative control (reversed order must not
match), and ablation (removing the order edges collapses production).
"""

from __future__ import annotations

import json

from casa.curriculum import (
    compose_sentence,
    gate_sentence_order,
    induce_order_from_examples,
    teach_conditioned_rule,
    teach_glossary,
    teach_sentence_order,
)
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
SENT = REPO_ROOT / "lab/curriculum/en-sentence-v1.json"
RULES = REPO_ROOT / "lab/curriculum/en-rules-v1.json"
LAT = "schema-math"


def _data() -> dict:
    d = json.loads(SENT.read_text(encoding="utf-8"))
    d["order_examples"] = [(roles, surface) for roles, surface in d["order_examples"]]
    d["held_out"] = [(triple, expected) for triple, expected in d["held_out"]]
    return d


def _ready() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    data = _data()
    teach_glossary(state, [tuple(p) for p in data["glossary"]], bundle=bundle)
    p3 = json.loads(RULES.read_text(encoding="utf-8"))["rules"]["lang.rule.present3sg.en"]
    teach_conditioned_rule(state, LAT, "lang.rule.present3sg.en", [tuple(p) for p in p3])
    return state, data


def test_order_induced_from_examples_is_svo() -> None:
    data = _data()
    assert induce_order_from_examples(data["order_examples"]) == ["subj", "verb", "obj"]


def test_composes_agreeing_sentences_from_russian_triples() -> None:
    state, data = _ready()
    teach_sentence_order(state, LAT, data["order_examples"])
    # never-composed triples: glossary + 3sg agreement + induced order
    assert compose_sentence(state, LAT, subj="кот", verb="пить", obj="вода") == "The cat drinks the water."
    assert compose_sentence(state, LAT, subj="девочка", verb="нести", obj="молоко") == "The girl carries the milk."
    # unknown word -> declines rather than invent
    assert compose_sentence(state, LAT, subj="дракон", verb="пить", obj="вода") is None


def test_sentence_order_gate_passes_with_controls() -> None:
    state, data = _ready()
    rep = gate_sentence_order(state, LAT, data["order_examples"], data["held_out"])
    assert rep["passed"] is True
    assert rep["order"] == ["subj", "verb", "obj"]
    assert rep["held_out_pass_rate"] == 1.0
    assert rep["negative_control_passed"] is True
    assert rep["ablation_breaks_production"] is True
