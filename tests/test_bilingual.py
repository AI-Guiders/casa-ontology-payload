"""Bilingual clause: one meaning triple rendered in both English and Russian.

The glossary maps lemmas across languages; each grammar inflects/orders on its own.
Translates a GIVEN role triple (either source language), not free text.
"""

from __future__ import annotations

import json

from casa.curriculum import (
    bilingual_clause,
    gate_bilingual,
    teach_clause_constructions,
    teach_conditioned_rule,
    teach_glossary,
    teach_np_order,
    teach_sentence_order,
    translate_clause,
)
from casa.curriculum.sentence import RU_SVO_RULE
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
DATA = REPO_ROOT / "lab/curriculum/bilingual-v1.json"
EN_RULES = REPO_ROOT / "lab/curriculum/en-rules-v1.json"
RU_RULES = REPO_ROOT / "lab/curriculum/ru-rules-v1.json"
LAT = "schema-math"


def _ready() -> tuple[dict, dict]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    data = json.loads(DATA.read_text(encoding="utf-8"))
    teach_glossary(state, [tuple(p) for p in data["glossary"]], bundle=bundle)
    en = json.loads(EN_RULES.read_text(encoding="utf-8"))["rules"]
    ru = json.loads(RU_RULES.read_text(encoding="utf-8"))["rules"]
    teach_conditioned_rule(state, LAT, "lang.rule.present3sg.en", [tuple(p) for p in en["lang.rule.present3sg.en"]])
    for rid in ("lang.rule.acc-sg.ru", "lang.rule.present3sg.ru"):
        teach_conditioned_rule(state, LAT, rid, [tuple(p) for p in ru[rid]])
    teach_clause_constructions(state, LAT)
    teach_np_order(state, LAT)
    teach_sentence_order(state, LAT, [(r, s) for r, s in data["ru_order_examples"]], rule_id=RU_SVO_RULE)
    return state, data


def test_one_meaning_both_languages() -> None:
    state, _ = _ready()
    # from Russian
    out = bilingual_clause(state, LAT, subj="девочка", verb="читать", obj="книга", source="ru")
    assert out == {"ru": "Девочка читает книгу.", "en": "The girl reads the book."}
    # from English (same meaning, both renderings)
    out = bilingual_clause(state, LAT, subj="boy", verb="love", obj="dog", source="en")
    assert out == {"ru": "Мальчик любит собаку.", "en": "The boy loves the dog."}
    # directional helper, with a sibilant verb agreement on the EN side
    assert translate_clause(state, LAT, subj="кот", verb="ловить", obj="рыба", source="ru", target="en") == "The cat catches the fish."
    # unknown word -> that side declines rather than invent
    assert bilingual_clause(state, LAT, subj="дракон", verb="читать", obj="книга", source="ru")["en"] is None


def test_bilingual_gate_passes_with_controls() -> None:
    state, data = _ready()
    cases = [(triple, ru, en) for triple, ru, en in data["cases"]]
    rep = gate_bilingual(state, LAT, cases)
    assert rep["passed"] is True
    assert rep["both_languages_pass_rate"] == 1.0
    assert rep["ablation_breaks_production"] is True
