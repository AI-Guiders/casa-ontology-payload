#!/usr/bin/env python3
"""Corpus-range lexicon shard id slugs."""

from __future__ import annotations

from casa.prisms.memory.lexicon_shard import (
    attach_corpus_range_shard_ids,
    build_semantic_l2_rename_map,
    lexicon_corpus_range_lattice_id,
    lexicon_range_slug,
)


def test_lexicon_range_slug():
    assert lexicon_range_slug("а", "андрейкин") == "а-андрейкин"
    assert lexicon_range_slug("бушевать", "вершинин") == "бушевать-вершинин"


def test_corpus_range_lattice_id():
    assert lexicon_corpus_range_lattice_id("ru", "а", "андрейкин") == "lexicon-ru-а-андрейкин"


def test_attach_shard_ids_unique():
    ranges = [
        {"shard": 0, "word_lo": "а", "word_hi": "андрейкин"},
        {"shard": 1, "word_lo": "андрес", "word_hi": "базыр"},
    ]
    out = attach_corpus_range_shard_ids(ranges, locale="ru")
    ids = [r["shard_id"] for r in out]
    assert len(set(ids)) == len(ids)


def test_build_rename_map():
    cfg = {
        "letter_ranges": [
            {"shard": 0, "word_lo": "а", "word_hi": "андрейкин"},
        ]
    }
    m = build_semantic_l2_rename_map(cfg, locale="ru")
    assert m["L2_word_00"] == "lexicon-ru-а-андрейкин"
    assert m["lexicon-ru-00"] == "lexicon-ru-а-андрейкин"
