#!/usr/bin/env python3
"""Possessive rule + examples (не лексема в gate)."""

from __future__ import annotations

from casa.prisms.visual.phrase_compose import compose_phrase_verdict, load_phrase_events
from casa.prisms.visual.phrase_permutation import check_permutation_equiv
from casa.prisms.visual.phrase_possessive import (
    POSSESSIVE_RULE_ROWS,
    check_possessive_agreement,
    expected_possessive_surface,
    infer_gender_from_referent,
    plural_possessive_trap,
)


def test_rule_table_covers_sg_genders_and_pl():
    assert len(POSSESSIVE_RULE_ROWS) == 4
    assert expected_possessive_surface("lang.meta.grammar.gender.fem", "lang.meta.grammar.number.pl") == "мои"


def test_infer_gender_from_pronoun():
    assert infer_gender_from_referent("она") == "lang.meta.grammar.gender.fem"


def test_pronoun_sg_examples_all_pass():
    entry = next(e for e in load_phrase_events() if e.get("event_id") == "lang.event.possessive.pronoun.sg.v0")
    for ex in entry["examples"]:
        reads = [{"surface": w["surface"], "verdict": "analytic_know"} for w in ex["words"]]
        assert compose_phrase_verdict(reads, entry)["phrase_know"]


def test_head_sg_rule_with_any_noun_surface():
    """Правило fem+sg → моя; «палка» не в JSON — род из example_gender_id."""
    entry = next(e for e in load_phrase_events() if e.get("event_id") == "lang.event.possessive.head.sg.v0")
    fem_gid = "lang.meta.grammar.gender.fem"
    rep = check_possessive_agreement(
        {"head": {"surface": "палка"}, "possessive": {"surface": "моя"}},
        entry["possessive_agreement"],
        example_gender_id=fem_gid,
    )
    assert rep["ok"]
    bad = check_possessive_agreement(
        {"head": {"surface": "палка"}, "possessive": {"surface": "мой"}},
        entry["possessive_agreement"],
        example_gender_id=fem_gid,
    )
    assert not bad["ok"]


def test_head_pl_same_moi_any_head():
    entry = next(e for e in load_phrase_events() if e.get("event_id") == "lang.event.possessive.head.pl.v0")
    for head in ("дома", "книги", "окна", "бананы"):
        rep = check_possessive_agreement(
            {"head": {"surface": head}, "possessive": {"surface": "мои"}},
            entry["possessive_agreement"],
        )
        assert rep["ok"], head


def test_plural_trap_moya_with_pl_rule():
    assert plural_possessive_trap("моя", "lang.meta.grammar.number.pl") == "pl_requires_moi_not_sg_possessive"
    rep = check_possessive_agreement(
        {"head": {"surface": "книги"}, "possessive": {"surface": "моя"}},
        [{"number_id": "lang.meta.grammar.number.pl"}],
    )
    assert not rep["ok"]


def test_wrong_possessive_on_pronoun():
    entry = next(e for e in load_phrase_events() if e.get("event_id") == "lang.event.possessive.pronoun.sg.v0")
    reads = [{"surface": "она", "verdict": "analytic_know"}, {"surface": "мой", "verdict": "analytic_know"}]
    assert not compose_phrase_verdict(reads, entry)["phrase_know"]


def test_pronoun_masc_example_permutation():
    entry = next(e for e in load_phrase_events() if e.get("event_id") == "lang.event.possessive.pronoun.sg.v0")
    example = entry["examples"][0]
    from casa.prisms.visual.phrase_compose import _nfc

    spec = {_nfc(w["surface"]).lower(): w["surface"] for w in example["words"]}
    flat = {**entry, **example}

    def compose_surface(surface: str) -> dict:
        reads = []
        for token in surface.split():
            key = _nfc(token).lower()
            if key in spec:
                reads.append({"surface": spec[key], "verdict": "analytic_know"})
        return compose_phrase_verdict(reads, entry)

    rep = check_permutation_equiv(flat, compose_surface)
    assert rep.get("permutation_know")
