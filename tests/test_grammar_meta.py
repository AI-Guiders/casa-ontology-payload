#!/usr/bin/env python3
"""Grammar meta L2/L3 registry and quiz (ADR-0030)."""

from __future__ import annotations

from casa.prisms.visual.grammar_meta import (
    agreement_concept_for_pair,
    case_concept_for_surface,
    check_agreement_registry,
    check_case_registry,
    check_person_registry,
    grammar_meta_report,
    person_concept_for_surface,
    quiz_agreement_pair,
)


def test_person_registry():
    reg = check_person_registry()
    assert reg["ok"]
    assert person_concept_for_surface("я") == "lang.meta.grammar.person.1sg"
    assert person_concept_for_surface("они") == "lang.meta.grammar.person.3pl"


def test_agreement_registry():
    reg = check_agreement_registry()
    assert reg["ok"]
    assert agreement_concept_for_pair("мама", "мыла") == "lang.meta.grammar.agreement.subjectVerb.fem.sg.past"
    assert agreement_concept_for_pair("брат", "мыл") == "lang.meta.grammar.agreement.subjectVerb.masc.sg.past"


def test_case_registry():
    reg = check_case_registry()
    assert reg["ok"]
    assert case_concept_for_surface("именительный падеж") == "lang.meta.grammar.case.nom"
    assert case_concept_for_surface("винительный падеж") == "lang.meta.grammar.case.acc"


def test_grammar_meta_reports_pass():
    for probe in ("meta-grammar-person", "meta-grammar-agreement", "meta-grammar-case"):
        rep = grammar_meta_report(probe)
        assert rep["pass"], probe


def test_agreement_quiz_wrong_hint():
    row = quiz_agreement_pair("мама", "мыл", hint="lang.meta.grammar.agreement.subjectVerb.fem.sg.past")
    assert row["verdict"] == "wrong"
