#!/usr/bin/env python3
"""Lookup entity type for a surface word via L3 denotes → instanceOf."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.hub_neighbors_v0 import _anchor_to_concept, _l3_edges
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.memory.sss_vocab_v0 import norm_word


def _entity_for_surface(state: dict, word: str, *, min_votes: int = 1) -> str | None:
    cid = _anchor_to_concept(word)
    edges = _l3_edges(ensure_prisms(state), min_votes=min_votes)
    for src, rel, dst in edges:
        if src == cid and rel == "denotes" and dst.startswith("entity."):
            return dst
    return None


def entity_type_for_word(state: dict, word: str, *, min_votes: int = 1) -> dict[str, Any]:
    """Return entity id + taxonomy type (entity.animal, …) if present."""
    eid = _entity_for_surface(state, word, min_votes=min_votes)
    if not eid:
        return {"word": norm_word(word), "entity_id": None, "type_id": None}

    edges = _l3_edges(ensure_prisms(state), min_votes=min_votes)
    types: list[str] = []
    for src, rel, dst in edges:
        if src == eid and rel == "instanceOf" and dst.startswith("entity."):
            types.append(dst)
    types = sorted(set(types))
    return {
        "word": norm_word(word),
        "entity_id": eid,
        "type_id": types[0] if types else None,
        "type_ids": types,
    }


def taxonomy_bonus(state: dict | None, word: str, *, min_votes: int = 1) -> float:
    """Small preview prior when word maps to a typed entity (sleep/L3 only)."""
    if state is None:
        return 0.0
    info = entity_type_for_word(state, word, min_votes=min_votes)
    if not info.get("type_id"):
        return 0.0
    return 8.0
