#!/usr/bin/env python3
"""Numeral + noun rule (не таблица по лексемам)."""

from __future__ import annotations

from casa.prisms.visual.phrase_compose import compose_phrase_verdict, load_phrase_events
from casa.prisms.visual.phrase_numeral import (
    DECLENSION_FEM_A_PALATAL,
    NUMERAL_CLASS_FEW,
    NUMERAL_CLASS_MANY,
    NUMERAL_CLASS_ONE,
    NUMERAL_RULE_ROWS,
    check_numeral_agreement,
    expected_head_surface,
    expected_numeral_surface,
    numeral_form_class,
    parse_numeral_value,
)


def test_numeral_form_class_pilot():
    assert numeral_form_class(1) == NUMERAL_CLASS_ONE
    assert numeral_form_class(2) == NUMERAL_CLASS_FEW
    assert numeral_form_class(5) == NUMERAL_CLASS_MANY
    assert numeral_form_class(11) == NUMERAL_CLASS_MANY
    assert numeral_form_class(21) == NUMERAL_CLASS_ONE
    assert numeral_form_class(22) == NUMERAL_CLASS_FEW


def test_expected_numeral_fem():
    gid = "lang.meta.grammar.gender.fem"
    assert expected_numeral_surface(1, gid) == "одна"
    assert expected_numeral_surface(2, gid) == "две"
    assert expected_numeral_surface(5, gid) == "пять"


def test_palka_paradigm_rule():
    gid = "lang.meta.grammar.gender.fem"
    lemma = "палка"
    assert expected_head_surface(lemma, NUMERAL_CLASS_ONE, declension_id=DECLENSION_FEM_A_PALATAL) == "палка"
    assert expected_head_surface(lemma, NUMERAL_CLASS_FEW, declension_id=DECLENSION_FEM_A_PALATAL) == "палки"
    assert expected_head_surface(lemma, NUMERAL_CLASS_MANY, declension_id=DECLENSION_FEM_A_PALATAL) == "палок"
    row = [{"gender_id": gid, "declension_id": DECLENSION_FEM_A_PALATAL}]
    assert check_numeral_agreement(
        {"numeral": {"surface": "одна"}, "head": {"surface": "палка"}},
        row,
        example_lemma=lemma,
    )["ok"]
    assert check_numeral_agreement(
        {"numeral": {"surface": "пять"}, "head": {"surface": "палки"}},
        row,
        example_lemma=lemma,
    )["ok"] is False
    assert check_numeral_agreement(
        {"numeral": {"surface": "пять"}, "head": {"surface": "палок"}},
        row,
        example_lemma=lemma,
    )["ok"]


def test_all_pilot_examples_compose():
    entry = next(e for e in load_phrase_events() if e.get("event_id") == "lang.event.numeral.head.v0")
    for ex in entry["examples"]:
        reads = [{"surface": w["surface"], "verdict": "analytic_know"} for w in ex["words"]]
        assert compose_phrase_verdict(reads, entry)["phrase_know"], ex


def test_rule_rows_count():
    assert len(NUMERAL_RULE_ROWS) == 3
    assert parse_numeral_value("одна") == 1
