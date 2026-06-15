"""Grounded generation: validate a meaning triple against the conceptual network, then
render it — or refuse nonsense. Ties the concept net to the bilingual generator.
"""

from __future__ import annotations

import json

from casa.curriculum import (
    teach_clause_constructions,
    teach_conditioned_rule,
    teach_glossary,
    teach_np_order,
    teach_sentence_order,
)
from casa.curriculum.concept_net import teach_concept_net
from casa.curriculum.grounded import gate_grounded, guarded_clause, meaningful
from casa.curriculum.sentence import RU_SVO_RULE
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
NET = REPO_ROOT / "lab/curriculum/concept-net-base-v1.json"
EN_RULES = REPO_ROOT / "lab/curriculum/en-rules-v1.json"
RU_RULES = REPO_ROOT / "lab/curriculum/ru-rules-v1.json"
LAT = "schema-math"
VERBS = [("читать", "read"), ("есть", "eat"), ("пить", "drink"), ("любить", "love")]


def _ready() -> dict:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    teach_concept_net(state, LAT, json.loads(NET.read_text(encoding="utf-8")), bundle=bundle)
    teach_glossary(state, VERBS, bundle=bundle)
    en = json.loads(EN_RULES.read_text(encoding="utf-8"))["rules"]
    ru = json.loads(RU_RULES.read_text(encoding="utf-8"))["rules"]
    teach_conditioned_rule(state, LAT, "lang.rule.present3sg.en", [tuple(p) for p in en["lang.rule.present3sg.en"]])
    for rid in ("lang.rule.acc-sg.ru", "lang.rule.present3sg.ru"):
        teach_conditioned_rule(state, LAT, rid, [tuple(p) for p in ru[rid]])
    teach_clause_constructions(state, LAT)
    teach_np_order(state, LAT)
    teach_sentence_order(state, LAT, [({"subj": "кот", "verb": "читает", "obj": "книгу"}, ["кот", "читает", "книгу"])], rule_id=RU_SVO_RULE)
    return state


def test_sensible_triple_renders_bilingually() -> None:
    state = _ready()
    r = guarded_clause(state, LAT, subj="студент", verb="читать", obj="книга")
    assert r["valid"] is True
    assert r["en"] == "The student reads the book."
    assert r["ru"] == "Студент читает книгу."
    # a verb with no known constraint is unconstrained -> still generated
    assert guarded_clause(state, LAT, subj="девочка", verb="любить", obj="книга")["valid"] is True


def test_nonsense_triple_is_refused_before_rendering() -> None:
    state = _ready()
    # table cannot be the agent of read
    r = guarded_clause(state, LAT, subj="стол", verb="читать", obj="книга")
    assert r["valid"] is False and r["en"] is None and r["ru"] is None
    assert "agent" in r["reason"]
    # stone is not edible
    r = guarded_clause(state, LAT, subj="человек", verb="есть", obj="камень")
    assert r["valid"] is False and r["en"] is None
    assert "edible" in r["reason"]
    # an idea cannot read
    assert guarded_clause(state, LAT, subj="идея", verb="читать", obj="книга")["valid"] is False


def test_meaningful_is_cross_lingual() -> None:
    state = _ready()
    assert meaningful(state, LAT, "student", "read", "book")["valid"] is True
    assert meaningful(state, LAT, "table", "read", "book")["valid"] is False


def test_grounded_gate() -> None:
    state = _ready()
    rep = gate_grounded(
        state, LAT,
        sensible=[("студент", "читать", "книга"), ("девочка", "любить", "книга"), ("учитель", "читать", "книга")],
        nonsense=[("стол", "читать", "книга"), ("человек", "есть", "камень"), ("идея", "читать", "книга")],
    )
    assert rep["passed"] is True
    assert rep["sensible_render_rate"] == 1.0
    assert rep["all_nonsense_refused"] is True
