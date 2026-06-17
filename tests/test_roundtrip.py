"""Translation through meaning: text -> conceptual graph -> text, with a language switch.

«Перевод с русского на русский»: a sentence round-trips to a normalised paraphrase in the
same language, and to a translation in the other — all through one language-independent graph.
"""

from __future__ import annotations

import json

from casa.curriculum.clause import teach_clause_constructions
from casa.curriculum.compose import teach_conditioned_rule, teach_np_order
from casa.curriculum.concept_net import teach_concept_net
from casa.curriculum.roundtrip import round_trip, translate_through_meaning
from casa.curriculum.sentence import RU_SVO_RULE, teach_sentence_order
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa._paths import REPO_ROOT

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
NET = REPO_ROOT / "lab/curriculum/concept-net-base-v1.json"
RU = REPO_ROOT / "lab/curriculum/ru-rules-v1.json"
EN = REPO_ROOT / "lab/curriculum/en-rules-v1.json"
LAT = "schema-math"
RU_RULES = ("lang.rule.acc-sg.ru", "lang.rule.present3sg.ru", "lang.rule.prep-sg.ru",
            "lang.rule.gen-sg-m.ru", "lang.rule.gen-sg-n.ru", "lang.rule.gen-sg-f.ru")


def _ready() -> dict:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    teach_concept_net(state, LAT, json.loads(NET.read_text(encoding="utf-8")), bundle=bundle)
    ru = json.loads(RU.read_text(encoding="utf-8"))["rules"]
    en = json.loads(EN.read_text(encoding="utf-8"))["rules"]
    for rid in RU_RULES:
        teach_conditioned_rule(state, LAT, rid, [tuple(p) for p in ru[rid]])
    teach_conditioned_rule(state, LAT, "lang.rule.present3sg.en", [tuple(p) for p in en["lang.rule.present3sg.en"]])
    teach_clause_constructions(state, LAT)
    teach_np_order(state, LAT)
    teach_sentence_order(state, LAT, [({"subj": "кот", "verb": "читает", "obj": "книгу"}, ["кот", "читает", "книгу"])], rule_id=RU_SVO_RULE)
    return state


def test_russian_to_russian_normalises_paraphrases() -> None:
    state = _ready()
    for t in ("яблоко лежит на столе", "на столе яблоко", "на столе лежит яблоко"):
        assert round_trip(state, LAT, t, target="ru") == "Яблоко на столе."


def test_round_trip_is_translation_with_a_language_switch() -> None:
    state = _ready()
    # same source, both targets — one meaning rendered in each language
    assert round_trip(state, LAT, "яблоко лежит на столе", target="en") == "The apple is on the table."
    assert round_trip(state, LAT, "apple on the table", target="ru") == "Яблоко на столе."
    both = translate_through_meaning(state, LAT, "на столе яблоко")
    assert both == {"ru": "Яблоко на столе.", "en": "The apple is on the table."}


def test_prepositions_take_the_right_russian_case() -> None:
    state = _ready()
    assert round_trip(state, LAT, "яблоко на столе у окна", target="ru") == "Яблоко на столе у окна."  # на+prep, у+gen
    assert round_trip(state, LAT, "книга в коробке", target="ru") == "Книга в коробке."


def test_transitive_clause_round_trips_both_ways() -> None:
    state = _ready()
    assert round_trip(state, LAT, "студент читает книгу", target="ru") == "Студент читает книгу."
    assert round_trip(state, LAT, "студент читает книгу", target="en") == "The student reads the book."
