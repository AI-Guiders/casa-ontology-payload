#!/usr/bin/env python3
"""Semantic memory layer names (memory.grapheme … memory.phrase)."""

from __future__ import annotations

from casa.prisms.shared.memory_layer_names import (
    legacy_l_code_to_layer,
    memory_layer_for_lattice_id,
    memory_layer_for_z,
    z_level_for_memory_layer,
)


def test_z_to_layer():
    assert memory_layer_for_z(0) == "memory.grapheme"
    assert memory_layer_for_z(2) == "memory.lexicon"
    assert z_level_for_memory_layer("memory.phrase") == 3


def test_legacy_codes():
    assert legacy_l_code_to_layer("L2") == "memory.lexicon"
    assert legacy_l_code_to_layer("T0") == "memory.grapheme"
    assert legacy_l_code_to_layer("B3") == "memory.phrase"


def test_lattice_inference():
    assert memory_layer_for_lattice_id("alphabet-ru") == "memory.grapheme.cyrl"
    assert memory_layer_for_lattice_id("syllables-ru") == "memory.syllable"
    assert memory_layer_for_lattice_id("lexicon-ru-а-андрейкин") == "memory.lexicon.shard"
    assert memory_layer_for_lattice_id("phrases") == "memory.phrase"
    assert memory_layer_for_lattice_id("L3_phrase_07") == "memory.phrase"
    assert memory_layer_for_lattice_id(
        "phrases-lang.word.а-ля-lang.word.андрейкин"
    ) == "memory.phrase"
