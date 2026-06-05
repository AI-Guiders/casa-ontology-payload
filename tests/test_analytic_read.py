"""Unit tests for analytic_read compose (no store)."""

from __future__ import annotations

from casa.prisms.visual.analytic_read import (
    chain_surface,
    compose_analytic_read,
    lookup_analytic_entry,
    r1_novel_bind,
    slug_from_vis_frame,
    syllable_chain_status,
    verify_analytic_read_frame,
)
from casa.prisms.visual.bridge_math import frame_id_from_vis_cue, vis_cue_from_frame_id
from casa.prisms.visual.corpus_lexicon import analytic_entry_from_corpus
from casa.prisms.visual.syllabify_ru import syllabify_ru


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
        lex_in_ltm=True,
        word_cid="lang.word.d2a8dc30e406",
        novel_preds=[],
        novel_metrics={"lum_ink_cells": 10},
        min_syllable_votes=2,
    )
    assert ok and via == "novel_compose" and score == 4


def test_slug_from_vis_frame():
    assert slug_from_vis_frame("phrase-probe-d2a8dc30e406-sans") == "d2a8dc30e406"
    assert slug_from_vis_frame("vis:word-27dae5010f7e-sans") == "27dae5010f7e"


def test_frame_id_from_vis_cue():
    assert frame_id_from_vis_cue("vis:word-x-sans") == "word-x-sans"
    assert frame_id_from_vis_cue("word-x-sans") == "word-x-sans"
    assert frame_id_from_vis_cue("  VIS:phrase-probe-y-sans  ") == "phrase-probe-y-sans"
    assert vis_cue_from_frame_id("word-x-sans") == "vis:word-x-sans"
    assert vis_cue_from_frame_id("vis:word-x-sans") == "vis:word-x-sans"


def test_verify_analytic_read_frame_corpus_bridge():
    entry_scores = {
        "syllable-ма-sans": [("syllable.ма", 4)],
        "word-d2a8dc30e406-sans": [("lang.word.d2a8dc30e406", 4)],
        "analytic-probe-d2a8dc30e406-sans": [],
        "phrase-probe-d2a8dc30e406-sans": [],
    }
    predict = _predict_factory(entry_scores)
    assert verify_analytic_read_frame(
        {},
        "phrase-probe-d2a8dc30e406-sans",
        predict=predict,
    )


def test_syllabify_gosudarstvo():
    assert syllabify_ru("государство") == ["го", "су", "дар", "ство"]


def test_analytic_entry_from_corpus():
    ent = analytic_entry_from_corpus(slug="79ace4ce330a")
    assert ent is not None
    assert ent["surface"] == "государство"
    assert ent["syllables"] == ["го", "су", "дар", "ство"]
    assert ent["source"] == "corpus_lexicon"


def test_corpus_align_without_syllable_cards():
    entry = analytic_entry_from_corpus(slug="79ace4ce330a")
    assert entry is not None
    predict = _predict_factory(
        {
            "word-79ace4ce330a-sans": [("lang.word.79ace4ce330a", 4)],
            "analytic-probe-79ace4ce330a-sans": [],
        }
    )
    row = compose_analytic_read(
        {},
        entry,
        novel_preds=[],
        novel_metrics={"lum_ink_cells": 5},
        predict=predict,
    )
    assert row["verdict"] == "analytic_know"
    assert row["r1_novel_via"] == "corpus_align"
    assert row["chain"]["chain_know"] is False


def test_r1_corpus_align_bind():
    chain = {
        "chain_know": False,
        "surface_match": True,
        "segments": [],
    }
    ok, via, _ = r1_novel_bind(
        chain=chain,
        corpus_word_hit=True,
        lex_in_ltm=True,
        word_cid="lang.word.79ace4ce330a",
        novel_preds=[],
        novel_metrics={"lum_ink_cells": 3},
    )
    assert ok and via == "corpus_align"


def test_lookup_analytic_entry_corpus_first():
    ent = lookup_analytic_entry(None, "79ace4ce330a")
    assert ent is not None
    assert ent["surface"] == "государство"


def test_compose_chain_incomplete():
    entry = {
        "surface": "мама",
        "slug": "d2a8dc30e406",
        "syllables": ["ма", "ма"],
        "syllable_concept_ids": ["syllable.ма", "syllable.ма"],
    }
    predict = _predict_factory(
        {
            "syllable-ма-sans": [("syllable.ма", 4), ("syllable.па", 4)],
            "word-d2a8dc30e406-sans": [("lang.word.d2a8dc30e406", 4)],
            "analytic-probe-d2a8dc30e406-sans": [],
        }
    )
    row = compose_analytic_read({}, entry, novel_preds=[], predict=predict)
    assert row["verdict"] == "chain_incomplete"
