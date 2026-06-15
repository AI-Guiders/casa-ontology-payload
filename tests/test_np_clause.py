"""The full generator: rich noun phrases inside clauses, with number-driven agreement.

Consolidates glossary + plural/3sg/past rules + NP order + clause constructions. The
subject's number selects the verb form (the cat drinks / the cats drink) and auxiliary
(Does / Do). The gate ablates the NP order (production collapses) and reverses it
(adjective/number cases must no longer match).
"""

from __future__ import annotations

import json

from casa.curriculum import (
    compose_full_clause,
    gate_full_clause,
    teach_clause_constructions,
    teach_conditioned_rule,
    teach_glossary,
    teach_np_order,
)
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
DATA = REPO_ROOT / "lab/curriculum/en-np-clause-v1.json"
RULES = REPO_ROOT / "lab/curriculum/en-rules-v1.json"
LAT = "schema-math"


def _ready() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    data = json.loads(DATA.read_text(encoding="utf-8"))
    teach_glossary(state, [tuple(p) for p in data["glossary"]], bundle=bundle)
    rules = json.loads(RULES.read_text(encoding="utf-8"))["rules"]
    for rid in ("lang.rule.plural.en", "lang.rule.present3sg.en", "lang.rule.past.en"):
        teach_conditioned_rule(state, LAT, rid, [tuple(p) for p in rules[rid]])
    teach_clause_constructions(state, LAT)
    teach_np_order(state, LAT)
    return state, data


def test_number_drives_subject_verb_agreement() -> None:
    state, _ = _ready()
    c = lambda **kw: compose_full_clause(state, LAT, obj={"noun": "вода"}, verb="пить", **kw)
    assert c(subject={"noun": "кот"}) == "The cat drinks the water."                  # singular -> 3sg
    assert c(subject={"noun": "кот", "plural": True}) == "The cats drink the water."  # plural -> base
    assert c(subject={"noun": "кот"}, mood="interrogative") == "Does the cat drink the water?"
    assert c(subject={"noun": "кот", "plural": True}, mood="interrogative") == "Do the cats drink the water?"


def test_numbers_and_adjectives_in_noun_phrases() -> None:
    state, _ = _ready()
    # number forces plural and pluralises the noun via the learned rule
    assert compose_full_clause(
        state, LAT, subject={"noun": "кот", "number": "два", "adj": "большой", "determiner": None},
        obj={"noun": "вода"}, verb="пить",
    ) == "Two big cats drink the water."
    assert compose_full_clause(
        state, LAT, subject={"noun": "кот"}, obj={"noun": "рыба", "adj": "маленький"}, verb="видеть",
    ) == "The cat sees the small fish."


def test_full_generator_gate_passes_with_controls() -> None:
    state, data = _ready()
    irr = data["irregular_past"]
    cases = [({**feat, "irregular_past": irr}, expected) for feat, expected in data["cases"]]
    rep = gate_full_clause(state, LAT, cases)
    assert rep["passed"] is True
    assert rep["held_out_pass_rate"] == 1.0
    assert rep["negative_control_passed"] is True
    assert rep["ablation_breaks_production"] is True
