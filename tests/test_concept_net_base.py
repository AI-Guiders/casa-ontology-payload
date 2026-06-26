"""Base conceptual network (~280 concepts): every concept grounds, validation holds.

Rebuild the JSON with scripts/build_concept_net.py. Categories carry types/affordances;
leaf concepts inherit by membership. Cross-lingual via glossary names edges.
"""

from __future__ import annotations

import json

from casa.curriculum.concept_net import (
    affordances_of,
    concept_of,
    gate_concept_net,
    has_part,
    isa_closure,
    meaning_graph,
    parts_of,
    relation_map,
    teach_concept_net,
    validate,
)
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
NET = REPO_ROOT / "lab/curriculum/concept-net-base-v1.json"
LAT = "schema-math"


def _ready() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    data = json.loads(NET.read_text(encoding="utf-8"))
    teach_concept_net(state, LAT, data, bundle=bundle)
    return state, data


def test_base_ontology_size_and_grounding() -> None:
    state, data = _ready()
    n = sum(len(v) for v in data["concepts"].values())
    assert n >= 250  # a few hundred concepts
    # every leaf concept reaches its category in the isa-closure — no typo'd category
    for category, members in data["concepts"].items():
        for _ru, en in members:
            cid = f"concept.{en.strip().lower().replace(' ', '_')}"
            assert category in isa_closure(state, LAT, cid), (cid, category)


def test_inherited_affordances_by_category() -> None:
    state, _ = _ready()
    assert {"edible", "positionable"} <= affordances_of(state, LAT, concept_of(state, LAT, "яблоко"))
    assert "rideable" in affordances_of(state, LAT, concept_of(state, LAT, "машина"))
    assert "wearable" in affordances_of(state, LAT, concept_of(state, LAT, "рубашка"))
    assert "drinkable" in affordances_of(state, LAT, concept_of(state, LAT, "вода"))
    assert "agent" in affordances_of(state, LAT, concept_of(state, LAT, "собака"))
    assert affordances_of(state, LAT, concept_of(state, LAT, "идея")) == set()  # abstract


def test_validation_cross_lingual_and_plausibility() -> None:
    state, _ = _ready()
    assert validate(state, LAT, "on", "яблоко", "стол")["valid"] is True
    assert validate(state, LAT, "on", "apple", "table")["valid"] is True       # same map, EN
    assert validate(state, LAT, "ride", "мальчик", "велосипед")["valid"] is True
    assert validate(state, LAT, "wear", "женщина", "платье")["valid"] is True
    assert validate(state, LAT, "eat", "стол", "яблоко")["valid"] is False      # table is not an agent
    assert validate(state, LAT, "drink", "идея", "вода")["valid"] is False      # idea is not an agent


def test_location_possession_material_relations() -> None:
    state, _ = _ready()
    assert validate(state, LAT, "at", "человек", "парк")["valid"] is True       # positionable in a place
    assert validate(state, LAT, "at", "человек", "яблоко")["valid"] is False     # apple is not a location
    assert validate(state, LAT, "has", "женщина", "машина")["valid"] is True     # agent owns an object
    assert validate(state, LAT, "has", "стол", "машина")["valid"] is False       # a table cannot own
    assert validate(state, LAT, "made_of", "стол", "древесина")["valid"] is True  # object of a material
    assert validate(state, LAT, "made_of", "стол", "идея")["valid"] is False      # idea is not a material


def test_mereology_inherited_per_type() -> None:
    state, _ = _ready()
    # parts inherit along isa: a car is a vehicle (-> wheel) and a car (-> engine)
    assert has_part(state, LAT, "машина", "колесо") is True
    assert has_part(state, LAT, "машина", "двигатель") is True
    assert has_part(state, LAT, "велосипед", "колесо") is True
    assert has_part(state, LAT, "велосипед", "двигатель") is False   # a bicycle has no engine
    assert has_part(state, LAT, "человек", "рука") is True
    assert has_part(state, LAT, "яблоко", "колесо") is False
    assert "concept.wheel" in parts_of(state, LAT, concept_of(state, LAT, "машина"))


def test_relation_map_is_language_independent() -> None:
    state, _ = _ready()
    mru = relation_map(state, LAT, "on", "яблоко", "стол")
    men = relation_map(state, LAT, "on", "apple", "table")
    assert mru == men  # same concept map regardless of the input language
    assert mru["valid"] is True
    assert mru["subject"]["concept"] == "concept.apple"
    assert "physical_object" in mru["subject"]["types"]
    assert mru["subject"]["names"] == {"ru": ["яблоко"], "en": ["apple"]}
    assert mru["edge"]["needs"] == {"arg1": "positionable", "arg2": "support_surface"}
    # an invalid combination still maps, marked unsatisfied with a reason
    bad = relation_map(state, LAT, "on", "идея", "стол")
    assert bad["valid"] is False and bad["edge"]["satisfied"] is False


def test_meaning_graph_multi_edge_and_language_independent() -> None:
    state, _ = _ready()
    # «яблоко на столе у окна» = on(apple, table) + near(table, window)
    ru = meaning_graph(state, LAT, [("on", "яблоко", "стол"), ("near", "стол", "окно")])
    en = meaning_graph(state, LAT, [("on", "apple", "table"), ("near", "table", "window")])
    assert ru == en                                   # same graph regardless of language
    assert ru["valid"] is True
    assert set(ru["nodes"]) == {"concept.apple", "concept.table", "concept.window"}  # shared node deduped
    assert len(ru["edges"]) == 2
    # one nonsense edge flags the whole graph, with the offending edge marked
    bad = meaning_graph(state, LAT, [("on", "книга", "стол"), ("eat", "стол", "яблоко")])
    assert bad["valid"] is False
    assert [e["satisfied"] for e in bad["edges"]] == [True, False]


def test_new_concept_inherits_group_rules_by_one_edge() -> None:
    # the economy of the hierarchy: a brand-new word joins a group with ONE isa edge and
    # inherits everything — no per-word affordance or relation rules needed
    from casa.curriculum.concept_net import teach_isa
    from casa.curriculum.glossary import teach_glossary

    state, bundle = _ready()
    teach_glossary(state, [("айва", "quince")], bundle=bundle)
    teach_isa(state, LAT, [("concept.quince", "fruit")])  # the only thing added for «айва»
    assert affordances_of(state, LAT, "concept.quince") == {"edible", "ownable", "positionable"}
    assert validate(state, LAT, "on", "айва", "стол")["valid"] is True       # via inherited positionable
    assert validate(state, LAT, "eat", "человек", "айва")["valid"] is True   # via inherited edible
    assert validate(state, LAT, "on", "идея", "айва")["valid"] is False      # quince is not a surface


def test_base_concept_net_gate() -> None:
    state, data = _ready()
    rep = gate_concept_net(
        state, LAT,
        valid_cases=[tuple(c) for c in data["valid"]],
        invalid_cases=[tuple(c) for c in data["invalid"]],
    )
    assert rep["passed"] is True
    assert rep["valid_pass_rate"] == 1.0
    assert rep["negative_control_passed"] is True
    assert rep["ablation_breaks_validation"] is True
