#!/usr/bin/env python3
"""Empty alphabet-ru / lexicon-ru lattices for literacy lesson moments."""

from __future__ import annotations

from casa.domain.prism_ids import PRISM_LANG_RU
from casa.prisms.memory.memory_prisms import import_lattice_into_prism, memory_lattices
from casa.prisms.shared.lattice_names_v1 import (
    ALPHABET_EN,
    ALPHABET_RU,
    LEXICON_EN,
    LEXICON_RU,
    SYLLABLES_EN,
    SYLLABLES_RU,
)


def lattice_for_lex_concept(concept_id: str) -> str | None:
    cid = str(concept_id or "")
    if cid.startswith("grapheme.latn."):
        return ALPHABET_EN
    if cid.startswith("grapheme."):
        return ALPHABET_RU
    if cid.startswith("lang.word.") or cid.startswith("lang.meta."):
        return LEXICON_RU
    if cid.startswith("syllable."):
        return SYLLABLES_RU
    return None


def _empty_lattice(*, width: int = 32, height: int = 32) -> dict:
    n = width * height
    return {"width": width, "height": height, "cells": [[] for _ in range(n)]}


def ensure_lexical_lattices(state: dict) -> None:
    """Like schema-math bootstrap — required before grapheme/word ingest on von-neumann."""
    lats = memory_lattices(state)
    for lid in (ALPHABET_RU, LEXICON_RU, SYLLABLES_RU, ALPHABET_EN, LEXICON_EN, SYLLABLES_EN):
        lat = lats.get(lid) or {}
        if lat.get("cells") or lat.get("_cells_in_ltm"):
            continue
        # bootstrap context: creating the empty lattice container for immutable
        # lattices (alphabet-ru, syllables) must bypass the hot-write gate
        import_lattice_into_prism(state, PRISM_LANG_RU, lid, _empty_lattice(), write_context="bootstrap")
