"""Generative composition: induce a rule, generate UNSEEN forms, gate verifies.

The point is anti-tautology: a memoriser fails held-out nouns; an induced rule that
lives on the field passes them, fails the negative control, and collapses under
ablation (proving production reads the rule from the field, not from Python).
"""

from __future__ import annotations

import json

from casa.curriculum import (
    apply_conditioned_rule,
    apply_suffix_rule,
    compose_en_np,
    gate_conditioned_rule,
    gate_suffix_rule,
    induce_conditioned_rule,
    induce_suffix,
    teach_conditioned_rule,
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
RULES = REPO_ROOT / "lab/curriculum/en-rules-v1.json"
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


def _rule_pairs(rule_id: str) -> list[tuple[str, str]]:
    data = json.loads(RULES.read_text(encoding="utf-8"))
    return [tuple(p) for p in data["rules"][rule_id]]


def test_conditioned_plural_induces_three_classes() -> None:
    clauses = induce_conditioned_rule(_rule_pairs("lang.rule.plural.en"))
    assert clauses is not None
    # the consonant+y class is a single general pattern (not memorised bigrams)
    assert ("Cy", 1, "ies", False) in clauses
    # sibilants take -es; the elsewhere/default class is +s (empty condition, last)
    assert any(cut == 0 and add == "es" for _, cut, add, _ in clauses)
    assert clauses[-1] == ("", 0, "s", False)


def test_conditioned_plural_gate_passes_with_controls() -> None:
    state, _ = _state()
    rep = gate_conditioned_rule(state, LAT, "lang.rule.plural.en", _rule_pairs("lang.rule.plural.en"))
    assert rep["passed"] is True
    assert rep["classes"] == 3
    assert rep["held_out_pass_rate"] >= 0.9
    assert rep["negative_control_passed"] is True
    assert rep["ablation_breaks_production"] is True


def test_conditioned_plural_generates_never_taught_words() -> None:
    state, _ = _state()
    teach_conditioned_rule(state, LAT, "lang.rule.plural.en", _rule_pairs("lang.rule.plural.en"))
    expected = {
        "fly": "flies", "puppy": "puppies", "story": "stories",   # consonant+y -> -ies
        "church": "churches", "branch": "branches", "kiss": "kisses",
        "tax": "taxes", "brush": "brushes",                        # sibilants -> -es
        "chair": "chairs", "phone": "phones",                      # default -> -s
    }
    for stem, plural in expected.items():
        assert apply_conditioned_rule(state, LAT, "lang.rule.plural.en", stem) == plural, stem


def test_conditioned_past_tense_gate_and_generation() -> None:
    state, _ = _state()
    pairs = _rule_pairs("lang.rule.past.en")
    rep = gate_conditioned_rule(state, LAT, "lang.rule.past.en", pairs)
    assert rep["passed"] is True
    teach_conditioned_rule(state, LAT, "lang.rule.past.en", pairs)
    assert apply_conditioned_rule(state, LAT, "lang.rule.past.en", "dance") == "danced"  # -e -> +d
    assert apply_conditioned_rule(state, LAT, "lang.rule.past.en", "kick") == "kicked"   # else +ed


def test_transform_detects_consonant_doubling() -> None:
    from casa.curriculum.compose import _transform

    assert _transform("big", "bigger") == (0, "er", True)   # gemination
    assert _transform("cat", "cats") == (0, "s", False)     # plain suffix
    assert _transform("baby", "babies") == (1, "ies", False)  # stem change, no double


def test_comparative_doubling_gate_and_generation() -> None:
    state, _ = _state()
    pairs = _rule_pairs("lang.rule.comparative.en")
    rep = gate_conditioned_rule(state, LAT, "lang.rule.comparative.en", pairs)
    assert rep["passed"] is True
    teach_conditioned_rule(state, LAT, "lang.rule.comparative.en", pairs)
    a = lambda w: apply_conditioned_rule(state, LAT, "lang.rule.comparative.en", w)
    assert a("mad") == "madder" and a("dim") == "dimmer"   # CVC -> double consonant
    assert a("neat") == "neater"                            # VVC -> no doubling
    assert a("tidy") == "tidier"                            # consonant+y -> -ier
    assert a("rude") == "ruder"                             # -e -> +r


def test_present3sg_gate_and_generation() -> None:
    state, _ = _state()
    pairs = _rule_pairs("lang.rule.present3sg.en")
    rep = gate_conditioned_rule(state, LAT, "lang.rule.present3sg.en", pairs)
    assert rep["passed"] is True
    teach_conditioned_rule(state, LAT, "lang.rule.present3sg.en", pairs)
    a = lambda w: apply_conditioned_rule(state, LAT, "lang.rule.present3sg.en", w)
    assert a("guess") == "guesses" and a("rush") == "rushes"  # sibilant -> -es
    assert a("spy") == "spies"                                 # consonant+y -> -ies
    assert a("sing") == "sings"                                # default -> -s


def test_compose_collapses_when_order_rule_ablated() -> None:
    state, bundle = _state()
    teach_glossary(state, [("белый", "white"), ("дом", "house")], bundle=bundle)
    teach_order_rule(state, LAT, "lang.phrase.np.en", ["adj", "noun"])
    assert compose_en_np(state, LAT, "белый", "дом") == "white house"
    for i, slot in enumerate(["adj", "noun"]):
        weaken_graph_edge(memory_lattices(state), LAT, "lang.phrase.np.en", "order", f"lang.slot.{slot}@{i}")
    assert compose_en_np(state, LAT, "белый", "дом") is None
