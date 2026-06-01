#!/usr/bin/env python3
"""MP-5: lattice classification and split from prism_memory."""

from __future__ import annotations

from casa.domain.content_prism_split import lattice_content_prism_target, split_content_prisms
from casa.domain.prism_ids import PRISM_LANG_RU, PRISM_MATH, PRISM_MEMORY
from casa.domain.prism_wire import prism_block
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH


def test_lattice_content_prism_target_ru_and_math():
    assert lattice_content_prism_target("L2_word_07") == PRISM_LANG_RU
    assert lattice_content_prism_target("lexicon-ru-03") == PRISM_LANG_RU
    assert lattice_content_prism_target(SCHEMA_MATH) == PRISM_MATH
    assert lattice_content_prism_target("F0_schema") == PRISM_MATH
    assert lattice_content_prism_target("L0_grapheme_latn") is None
    assert lattice_content_prism_target("lexicon-en-01") is None


def test_split_moves_lattices_to_domain_prisms():
    state = ensure_prisms(
        {
            "schema_version": "multi_prism_v1",
            "field_version": 1,
            "prisms": {
                "prism_memory": {
                    "subsystem": "sss",
                    "lattices": {
                        "L2_word_00": {"width": 4, "height": 4, "cells": [[] for _ in range(16)]},
                        "schema-math": {"width": 4, "height": 4, "cells": [[] for _ in range(16)]},
                        "L0_grapheme_latn": {"width": 4, "height": 4, "cells": [[] for _ in range(16)]},
                    },
                },
            },
        }
    )
    rep = split_content_prisms(state, move=True)
    assert "L2_word_00" in rep["moved"][PRISM_LANG_RU]
    assert "schema-math" in rep["moved"][PRISM_MATH]
    assert "L0_grapheme_latn" in rep["remaining_in_memory"]

    mem = prism_block(state, PRISM_MEMORY)["lattices"]
    assert "L2_word_00" not in mem
    assert "L0_grapheme_latn" in mem
    assert "schema-math" in prism_block(state, PRISM_MATH)["lattices"]
    merged = memory_lattices(state)
    assert "L2_word_00" in merged and "schema-math" in merged
