#!/usr/bin/env python3
"""English L2 lexicon helpers: batch imprint without episodic listen_word."""

from __future__ import annotations

from prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism  # type: ignore
from typing import Any

from codec_grid_v0 import Grid  # type: ignore
from predictor_v0 import _L2_PREFIX_INDEX_CACHE  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_l2_shard_v0 import (  # type: ignore
    DEFAULT_EN_NUM_SHARDS,
    L2_CONCEPT_PREFIX,
    L2_EN_SHARD_PREFIX,
    lattice_digest_l2_network,
    route_en_l2_lattice,
)
from sss_stack_v0 import _place_token  # type: ignore
from sss_vocab_v0 import norm_word, w_token  # type: ignore


def configure_en_store(state: dict, *, num_shards: int = DEFAULT_EN_NUM_SHARDS) -> dict[str, Any]:
    """Mark store as EN locale; enable crc32 EN sharding."""
    state = ensure_prisms(state)
    cfg = dict(state.get("l2_sharding") or {})
    cfg["locale"] = "en"
    cfg["enabled"] = False
    cfg["legacy_lattice"] = f"{L2_EN_SHARD_PREFIX}00"
    cfg["en"] = {"enabled": True, "num_shards": num_shards}
    cfg.setdefault("word_index", {})
    state["l2_sharding"] = cfg
    state.setdefault("store", {})["locale"] = "en"
    return cfg


def strengthen_en_word_on_l2(state: dict, word: str, *, copies: int = 3) -> str:
    """Place W:/C: tokens on EN L2 shard (no episodic cylinder)."""
    w = norm_word(word)
    cid = f"{L2_CONCEPT_PREFIX}{w}"
    lid = route_en_l2_lattice(state, w)
    lattices = memory_lattices(state)
    lat = lattices[lid]
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
    g = _place_token(g, f"C:{cid}", f"C:{cid}", copies=copies, radius=5)
    g = _place_token(g, w_token(w), w_token(w), copies=max(2, copies), radius=4)
    lat["cells"] = g.cells
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return lid


def ingest_en_lex_batch(
    state: dict,
    words: list[str],
    *,
    copies: int = 3,
    configure: bool = True,
) -> dict[str, Any]:
    """Fast batch EN lexicon imprint (field-only, no listen episodes)."""
    state = ensure_prisms(state)
    if configure:
        configure_en_store(state)

    unique = list(dict.fromkeys(norm_word(w) for w in words if norm_word(w)))
    shards: dict[str, int] = {}
    for w in unique:
        lid = strengthen_en_word_on_l2(state, w, copies=copies)
        shards[lid] = shards.get(lid, 0) + 1

    state.pop(_L2_PREFIX_INDEX_CACHE, None)
    state["field_version"] = int(state.get("field_version") or 0) + 1

    digest = lattice_digest_l2_network(state)
    word_set = set(unique)
    en_on_field = sum(
        1
        for cid, _ in digest
        if cid.startswith(L2_CONCEPT_PREFIX) and norm_word(cid[len(L2_CONCEPT_PREFIX) :]) in word_set
    )
    return {
        "words_requested": len(words),
        "words_unique": len(unique),
        "en_concepts_on_field": en_on_field,
        "shard_histogram": dict(sorted(shards.items())),
        "field_version": state["field_version"],
    }


def read_headwords(path) -> list[str]:
    from pathlib import Path

    p = Path(path)
    words: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        w = norm_word(line.split("#", 1)[0])
        if w and not w.startswith("#"):
            words.append(w)
    return list(dict.fromkeys(words))
