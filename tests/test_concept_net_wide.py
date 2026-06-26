"""Wide conceptual network (~2.5k concepts, WordNet-classified) — scale + core integrity.

The curated core keeps its fine affordances; the WordNet layer adds breadth with coarse
supersense-level types. Core validations must still hold. (The full gate is covered by
the 282-concept base test; here we check scale and a sample to stay fast.)
"""

from __future__ import annotations

import json

from casa.curriculum.concept_net import affordances_of, concept_of, isa_closure, teach_concept_net, validate
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
WIDE = REPO_ROOT / "lab/curriculum/concept-net-wide-v1.json"
LAT = "schema-math"


def _ready() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    data = json.loads(WIDE.read_text(encoding="utf-8"))
    teach_concept_net(state, LAT, data, bundle=bundle)
    return state, data


def test_wide_network_scale_and_grounding() -> None:
    state, data = _ready()
    n = sum(len(v) for v in data["concepts"].values())
    assert n >= 2000  # a few thousand concepts
    # spot-check grounding (no orphans) on a sample
    for cat, members in list(data["concepts"].items()):
        for _ru, en in members[:5]:
            cid = f"concept.{en.strip().lower().replace(' ', '_')}"
            assert cat in isa_closure(state, LAT, cid), (cid, cat)


def test_core_validations_survive_in_the_wide_network() -> None:
    state, _ = _ready()
    assert validate(state, LAT, "on", "яблоко", "стол")["valid"] is True
    assert validate(state, LAT, "eat", "собака", "мясо")["valid"] is True   # core word not shadowed
    assert validate(state, LAT, "on", "идея", "стол")["valid"] is False
    # WordNet-layer concepts get coarse supersense affordances
    assert "positionable" in affordances_of(state, LAT, concept_of(state, LAT, "лампа"))   # artifact
    assert affordances_of(state, LAT, concept_of(state, LAT, "музыка")) == set()           # abstract
