"""Conceptual network: affordance/type grounding + cross-lingual validation.

Objects inherit affordances along isa; relations carry selectional constraints; a
combination validates iff both arguments afford the required roles. The map is on
concepts, so «яблоко на столе» and 'apple on the table' validate identically. The gate
checks held-out combinations (generalisation via inheritance), category errors
(negative control), and ablation of the affords edges.
"""

from __future__ import annotations

import json

from casa.curriculum import teach_glossary
from casa.curriculum.concept_net import (
    affordances_of,
    gate_concept_net,
    teach_affords,
    teach_isa,
    teach_relation,
    validate,
)
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
NET = REPO_ROOT / "lab/curriculum/concept-net-v1.json"
LAT = "schema-math"


def _ready() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    data = json.loads(NET.read_text(encoding="utf-8"))
    teach_glossary(state, [tuple(p) for p in data["glossary"]], bundle=bundle)
    teach_isa(state, LAT, [tuple(p) for p in data["isa"]])
    teach_affords(state, LAT, [tuple(p) for p in data["affords"]])
    for r in data["relations"]:
        teach_relation(state, LAT, r["rel"], arg1=r["arg1"], arg2=r["arg2"])
    return state, data


def test_affordances_inherited_along_isa() -> None:
    state, _ = _ready()
    assert affordances_of(state, LAT, "concept.apple") == {"edible", "positionable"}
    assert affordances_of(state, LAT, "concept.table") == {"positionable", "support_surface"}


def test_validation_is_cross_lingual_and_same_map() -> None:
    state, _ = _ready()
    assert validate(state, LAT, "on", "яблоко", "стол")["valid"] is True
    assert validate(state, LAT, "on", "apple", "table")["valid"] is True   # same concepts, same verdict
    # selectional constraints reject the implausible direction and category errors
    assert validate(state, LAT, "on", "стол", "яблоко")["valid"] is False  # apple is not a surface
    assert validate(state, LAT, "on", "идея", "стол")["valid"] is False    # idea is not positionable
    assert validate(state, LAT, "eat", "человек", "яблоко")["valid"] is True
    assert validate(state, LAT, "eat", "яблоко", "человек")["valid"] is False  # apple is not an agent


def test_generalises_to_unseen_combinations() -> None:
    state, _ = _ready()
    # never asserted as a pair; valid purely via inheritance (banana isa fruit -> positionable,
    # chair isa furniture -> support_surface)
    assert validate(state, LAT, "on", "банан", "стул")["valid"] is True
    assert validate(state, LAT, "in", "яблоко", "коробка")["valid"] is True


def test_concept_net_gate_passes_with_controls() -> None:
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
