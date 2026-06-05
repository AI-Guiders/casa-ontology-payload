"""Unit tests for analytic_read compose (no store)."""

from __future__ import annotations

from casa.prisms.visual.analytic_read import (
    chain_surface,
    compose_analytic_read,
    r1_novel_bind,
    syllable_chain_status,
)


def _predict_factory(scores: dict[str, list[tuple[str, int]]]):
    def predict(_state, fid: str, *, top_k: int = 5):
        return scores.get(fid, [])[:top_k]

    return predict


def test_chain_surface():
    assert chain_surface(["мо", "ло", "ко"]) == "молоко"


def test_compose_analytic_know_via_lexicon():
    entry = {
        "surface": "молоко",
        "slug": "69f91741a4c2",
        "syllables": ["мо", "ло", "ко"],
        "syllable_concept_ids": ["syllable.мо", "syllable.ло", "syllable.ко"],
    }
    predict = _predict_factory(
        {
            "syllable-мо-sans": [("syllable.мо", 4)],
            "syllable-ло-sans": [("syllable.ло", 4)],
            "syllable-ко-sans": [("syllable.ко", 4)],
            "word-69f91741a4c2-sans": [("lang.word.69f91741a4c2", 4)],
            "analytic-probe-69f91741a4c2-sans": [("grapheme.cyrl.ko.lower", 1)],
        }
    )
    row = compose_analytic_read(
        {},
        entry,
        novel_preds=[("grapheme.cyrl.ko.lower", 1)],
        novel_metrics={"lum_ink_cells": 8},
        predict=predict,
    )

    assert row["verdict"] == "analytic_know"
    assert row["r1_novel_bind"] is True
    assert row["r1_novel_via"] == "novel_compose"
    assert row["chain"]["chain_know"] is True


def test_r1_novel_compose_bind():
    chain = {
        "chain_know": True,
        "surface_match": True,
        "segments": [{"top_score": 4}, {"top_score": 4}],
    }
    ok, via, score = r1_novel_bind(
        chain=chain,
        corpus_word_hit=True,
        word_cid="lang.word.d2a8dc30e406",
        novel_preds=[],
        novel_metrics={"lum_ink_cells": 10},
        min_syllable_votes=2,
    )
    assert ok and via == "novel_compose" and score == 4


def test_compose_chain_incomplete():
    entry = {
        "surface": "мама",
        "slug": "d2a8dc30e406",
        "syllables": ["ма", "ма"],
        "syllable_concept_ids": ["syllable.ма", "syllable.ма"],
    }
    predict = _predict_factory({"syllable-ма-sans": [("syllable.ма", 4), ("syllable.па", 4)]})
    row = compose_analytic_read({}, entry, novel_preds=[], predict=predict)
    assert row["verdict"] == "chain_incomplete"
