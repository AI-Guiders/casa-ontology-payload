"""Russian sentence generation: meaning triple -> conjugated, case-marked clause.

Mirror of the English generator: subject nominative, verb conjugated to 3sg, object
declined to the accusative, S-V-O order induced and field-stored. The gate verifies
held-out triples, a negative control (reversed order), and ablation.
"""

from __future__ import annotations

import json

from casa.curriculum import (
    compose_ru_clause,
    gate_ru_clause,
    teach_conditioned_rule,
    teach_sentence_order,
)
from casa.curriculum.sentence import RU_SVO_RULE
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
SENT = REPO_ROOT / "lab/curriculum/ru-sentence-v1.json"
RULES = REPO_ROOT / "lab/curriculum/ru-rules-v1.json"
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
    rules = json.loads(RULES.read_text(encoding="utf-8"))["rules"]
    for rid in ("lang.rule.acc-sg.ru", "lang.rule.present3sg.ru"):
        teach_conditioned_rule(state, LAT, rid, [tuple(p) for p in rules[rid]])
    return state, _data()


def test_composes_conjugated_case_marked_russian_clauses() -> None:
    state, data = _ready()
    teach_sentence_order(state, LAT, data["order_examples"], rule_id=RU_SVO_RULE)
    # never-composed triples: conjugation (читать->читает) + accusative (книга->книгу)
    assert compose_ru_clause(state, LAT, subj="девочка", verb="читать", obj="книга") == "Девочка читает книгу."
    assert compose_ru_clause(state, LAT, subj="кот", verb="ловить", obj="рыба") == "Кот ловит рыбу."
    # masculine inanimate object stays nominative in the accusative
    assert compose_ru_clause(state, LAT, subj="человек", verb="строить", obj="дом") == "Человек строит дом."


def test_ru_sentence_gate_passes_with_controls() -> None:
    state, data = _ready()
    rep = gate_ru_clause(state, LAT, data["order_examples"], data["held_out"])
    assert rep["passed"] is True
    assert rep["order"] == ["subj", "verb", "obj"]
    assert rep["held_out_pass_rate"] == 1.0
    assert rep["negative_control_passed"] is True
    assert rep["ablation_breaks_production"] is True
