#!/usr/bin/env python3
"""Lookup POS for a surface word via L3 has_pos edges."""

from __future__ import annotations

from typing import Any

from hub_neighbors_v0 import _l3_edges, _anchor_to_concept  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore


def word_pos(state: dict, word: str, *, min_votes: int = 1) -> dict[str, Any]:
    cid = _anchor_to_concept(word)
    edges = _l3_edges(ensure_prisms(state), min_votes=min_votes)
    pos_ids: list[str] = []
    for src, rel, dst in edges:
        if src == cid and rel == "has_pos" and dst.startswith("pos."):
            pos_ids.append(dst)
    pos_ids = sorted(set(pos_ids))
    return {
        "word": norm_word(word),
        "concept_id": cid,
        "pos_ids": pos_ids,
        "pos": pos_ids[0] if pos_ids else None,
    }
