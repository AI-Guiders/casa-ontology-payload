#!/usr/bin/env python3
"""Russian L2 lexicon helpers: batch imprint (mirror en_lexicon_v0)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.tick.predictor_v0 import _L2_PREFIX_INDEX_CACHE
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.memory.sss_l2_shard_v0 import (
    DEFAULT_NUM_SHARDS,
    L2_CONCEPT_PREFIX,
    configure_lex_sharding,
    lattice_digest_l2_network,
    sharding_config,
)
from casa.prisms.memory.sss_vocab_v0 import _strengthen_word_on_l2, norm_word


def configure_ru_store(state: dict, words: list[str], *, num_shards: int = DEFAULT_NUM_SHARDS) -> dict[str, Any]:
    """Mark store as RU locale; corpus-quantile L2 sharding from headwords."""
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    cfg["locale"] = "ru"
    cfg["enabled"] = True
    configure_lex_sharding(cfg, words, num_shards=num_shards)
    state["l2_sharding"] = cfg
    state.setdefault("store", {})["locale"] = "ru"
    return cfg


def ingest_ru_lex_batch(
    state: dict,
    words: list[str],
    *,
    copies: int = 3,
    configure: bool = True,
) -> dict[str, Any]:
    """Fast batch RU lexicon imprint (field-only, no listen episodes)."""
    state = ensure_prisms(state)
    unique = list(dict.fromkeys(norm_word(w) for w in words if norm_word(w)))
    if configure:
        configure_ru_store(state, unique)

    shards: dict[str, int] = {}
    for w in unique:
        lid = _strengthen_word_on_l2(state, w, copies=copies)
        shards[lid] = shards.get(lid, 0) + 1

    state.pop(_L2_PREFIX_INDEX_CACHE, None)
    state["field_version"] = int(state.get("field_version") or 0) + 1

    digest = lattice_digest_l2_network(state)
    word_set = set(unique)
    ru_on_field = sum(
        1
        for cid, _ in digest
        if cid.startswith(L2_CONCEPT_PREFIX) and norm_word(cid[len(L2_CONCEPT_PREFIX) :]) in word_set
    )
    return {
        "words_requested": len(words),
        "words_unique": len(unique),
        "ru_concepts_on_field": ru_on_field,
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
