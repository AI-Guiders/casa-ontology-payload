"""Generative composition: induce a rule, generate UNSEEN forms, gate verifies.

The point is anti-tautology: a memoriser fails held-out nouns; an induced rule that
lives on the field passes them, fails the negative control, and collapses under
ablation (proving production reads the rule from the field, not from Python).
"""

from __future__ import annotations

import json

from casa.curriculum import (
    apply_suffix_rule,
    compose_en_np,
    gate_suffix_rule,
    induce_suffix,
    teach_glossary,
    teach_order_rule,
    teach_suffix_rule,
)
from casa.curriculum.compose import read_order_rule
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.f0_stack import weaken_graph_edge
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
LAT = "schema-math"
PLURAL = [
    ("cat", "cats"), ("dog", "dogs"), ("book", "books"), ("hand", "hands"),
    ("house", "houses"), ("day", "days"), ("road", "roads"), ("friend", "friends"),
    ("word", "words"), ("sun", "suns"),
]


def _state() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    return state, bundle


def test_induce_suffix_finds_s_and_declines_on_mixed() -> None:
    assert induce_suffix(PLURAL) == "s"
    # mixed -s / -es is not a single regular append rule: decline rather than guess
    assert induce_suffix([("cat", "cats"), ("box", "boxes")]) is None
    # stem change is not a suffix rule
    assert induce_suffix([("man", "men")]) is None


def test_plural_rule_gate_generalises_with_controls() -> None:
    state, _ = _state()
    rep = gate_suffix_rule(state, LAT, "lang.rule.plural.en", PLURAL, held_out_ratio=0.4)
    assert rep["passed"] is True
    assert rep["induced"] == "s"
    assert rep["held_out_pass_rate"] == 1.0
    assert rep["negative_control_passed"] is True
    assert rep["ablation_breaks_production"] is True


def test_rule_generates_never_taught_plurals() -> None:
    state, _ = _state()
    teach_suffix_rule(state, LAT, "lang.rule.plural.en", PLURAL[3:])  # train on a subset
    # words the rule never saw at all still pluralise
    assert apply_suffix_rule(state, LAT, "lang.rule.plural.en", "tree") == "trees"
    assert apply_suffix_rule(state, LAT, "lang.rule.plural.en", "star") == "stars"


def test_ablating_the_field_edge_stops_production() -> None:
    state, _ = _state()
    teach_suffix_rule(state, LAT, "lang.rule.plural.en", PLURAL)
    assert apply_suffix_rule(state, LAT, "lang.rule.plural.en", "cat") == "cats"
    weaken_graph_edge(memory_lattices(state), LAT, "lang.rule.plural.en", "suffix", "lang.morph.suffix.s")
    assert apply_suffix_rule(state, LAT, "lang.rule.plural.en", "cat") is None


def test_compose_english_noun_phrase_from_two_russian_words() -> None:
    state, bundle = _state()
    teach_glossary(
        state,
        [("большой", "big"), ("маленький", "small"), ("белый", "white"),
         ("кот", "cat"), ("дом", "house"), ("собака", "dog")],
        bundle=bundle,
    )
    teach_order_rule(state, LAT, "lang.phrase.np.en", ["adj", "noun"])
    assert read_order_rule(state, LAT, "lang.phrase.np.en") == ["adj", "noun"]
    # phrases never co-presented, composed from the glossary + the order rule
    assert compose_en_np(state, LAT, "большой", "кот") == "big cat"
    assert compose_en_np(state, LAT, "белый", "дом") == "white house"
    assert compose_en_np(state, LAT, "маленький", "собака") == "small dog"


def test_compose_collapses_when_order_rule_ablated() -> None:
    state, bundle = _state()
    teach_glossary(state, [("белый", "white"), ("дом", "house")], bundle=bundle)
    teach_order_rule(state, LAT, "lang.phrase.np.en", ["adj", "noun"])
    assert compose_en_np(state, LAT, "белый", "дом") == "white house"
    for i, slot in enumerate(["adj", "noun"]):
        weaken_graph_edge(memory_lattices(state), LAT, "lang.phrase.np.en", "order", f"lang.slot.{slot}@{i}")
    assert compose_en_np(state, LAT, "белый", "дом") is None
