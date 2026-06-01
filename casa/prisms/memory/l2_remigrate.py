#!/usr/bin/env python3
"""L2 monolith → sharded network (root cause fix before ltm export / thin checkpoint)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any, Callable

LexProgressFn = Callable[[int, int, str], None] | None

from casa.prisms.memory.lexicon_shard import (
    DEFAULT_NUM_SHARDS,
    LEGACY_L2,
    L2_CONCEPT_PREFIX,
    L2_SHARD_PREFIX,
    clear_l2_shards,
    configure_lex_sharding,
    lattice_vocab_size,
    sharding_config,
)
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.stack import decode_lattice
from casa.prisms.memory.vocab import norm_word

# ltm_pack v0: vocab_n is u16 in header
LTM_VOCAB_U16_MAX = 0xFFFF


def words_from_l2_monolith(state: dict, *, lattice_id: str | None = None) -> list[str]:
    """Unique headwords still stored on legacy L2_word monolith."""
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    lid = lattice_id or str(cfg.get("legacy_lattice") or LEGACY_L2)
    lat = memory_lattices(state).get(lid) or {}
    if not lat.get("cells"):
        return []

    words: list[str] = []
    seen: set[str] = set()
    dec = decode_lattice(lat, min_votes=1)
    for c in dec.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if not cid.startswith(L2_CONCEPT_PREFIX):
            continue
        w = norm_word(cid[len(L2_CONCEPT_PREFIX) :])
        if w and w not in seen:
            seen.add(w)
            words.append(w)

    if words:
        return words

    for cell in lat.get("cells") or []:
        for t in cell:
            ts = str(t)
            if ts.startswith("W:"):
                w = norm_word(ts[2:])
            elif ts.startswith(f"C:{L2_CONCEPT_PREFIX}"):
                w = norm_word(ts[len(f"C:{L2_CONCEPT_PREFIX}") :])
            else:
                continue
            if w and w not in seen:
                seen.add(w)
                words.append(w)
    return words


def monolith_over_ltm_limit(state: dict, *, lattice_id: str | None = None) -> bool:
    cfg = sharding_config(state)
    lid = lattice_id or str(cfg.get("legacy_lattice") or LEGACY_L2)
    lat = memory_lattices(state).get(lid) or {}
    return lattice_vocab_size(lat) > LTM_VOCAB_U16_MAX


def needs_l2_remigrate(state: dict) -> bool:
    """True when legacy monolith is too fat for .ltm or holds lexicon not yet on shards."""
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    legacy = str(cfg.get("legacy_lattice") or LEGACY_L2)
    lats = memory_lattices(state)
    leg = lats.get(legacy) or {}
    leg_vocab = lattice_vocab_size(leg)
    if leg_vocab == 0:
        return False
    if leg_vocab > LTM_VOCAB_U16_MAX:
        return True
    shard_ids = [lid for lid in lats if lid.startswith(L2_SHARD_PREFIX)]
    if not shard_ids:
        return leg_vocab > 0
    indexed = len(cfg.get("word_index") or {})
    words_on_monolith = len(words_from_l2_monolith(state, lattice_id=legacy))
    return words_on_monolith > 256 and indexed < words_on_monolith // 2


def clear_legacy_l2_monolith(state: dict, *, lattice_id: str | None = None) -> None:
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    lid = lattice_id or str(cfg.get("legacy_lattice") or LEGACY_L2)
    lattices = memory_lattices(state)
    lat = lattices.get(lid)
    if not lat:
        return
    n = int(lat.get("width") or 32) * int(lat.get("height") or 32)
    lat["cells"] = [[] for _ in range(n)]
    from casa.domain.prism_wire import prism_memory

    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices


def remigrate_l2_from_monolith(
    state: dict,
    words: list[str] | None = None,
    *,
    copies: int = 3,
    num_shards: int = DEFAULT_NUM_SHARDS,
    clear_monolith: bool = True,
    lex_plan: str = "corpus_quantile",
    on_word_progress: LexProgressFn = None,
    progress_every: int = 5000,
) -> dict[str, Any]:
    """Move lang.word.* off L2_word monolith onto L2_word_XX shards (canon before compact ltm)."""
    state = ensure_prisms(state)
    cfg = sharding_config(state)
    legacy = str(cfg.get("legacy_lattice") or LEGACY_L2)
    extracted = words if words is not None else words_from_l2_monolith(state, lattice_id=legacy)
    if not extracted:
        return {"status": "noop", "reason": "no_words_on_monolith", "legacy_lattice": legacy}

    locale = str((state.get("store") or {}).get("locale") or cfg.get("locale") or "ru")
    cfg["enabled"] = True
    cfg["locale"] = locale
    configure_lex_sharding(cfg, extracted, num_shards=num_shards)
    cfg["lex_plan"] = lex_plan
    state["l2_sharding"] = cfg

    clear_l2_shards(state, keep_legacy=True)

    if locale == "en":
        from casa.prisms.memory.en_lexicon import ingest_en_lex_batch

        ingest_rep = ingest_en_lex_batch(state, extracted, copies=copies, configure=False)
        on_field_key = "en_concepts_on_field"
    else:
        from casa.prisms.memory.ru_lexicon import ingest_ru_lex_batch

        ingest_rep = ingest_ru_lex_batch(
            state,
            extracted,
            copies=copies,
            configure=False,
            on_word_progress=on_word_progress,
            progress_every=progress_every,
        )
        on_field_key = "ru_concepts_on_field"

    if clear_monolith:
        clear_legacy_l2_monolith(state, lattice_id=legacy)

    from casa.prisms.tick.predictor import _L2_PREFIX_INDEX_CACHE

    state.pop(_L2_PREFIX_INDEX_CACHE, None)
    state["field_version"] = int(state.get("field_version") or 0) + 1

    shard_vocab_max = 0
    for lid in memory_lattices(state):
        if lid.startswith(L2_SHARD_PREFIX):
            shard_vocab_max = max(shard_vocab_max, lattice_vocab_size(memory_lattices(state)[lid]))

    return {
        "status": "ok",
        "legacy_lattice": legacy,
        "words_remigrated": len(extracted),
        "locale": locale,
        "lex_plan": lex_plan,
        "num_shards": num_shards,
        on_field_key: ingest_rep.get(on_field_key),
        "shard_histogram": ingest_rep.get("shard_histogram"),
        "monolith_cleared": clear_monolith,
        "max_shard_vocab": shard_vocab_max,
        "field_version": state["field_version"],
    }


def ensure_l2_sharded_for_export(
    state: dict,
    *,
    force: bool = False,
    on_word_progress: LexProgressFn = None,
    progress_every: int = 5000,
) -> dict[str, Any] | None:
    """Run remigrate when monolith blocks ltm v0 (u16 vocab) or shards are empty."""
    if not force and not needs_l2_remigrate(state):
        return None
    return remigrate_l2_from_monolith(
        state,
        on_word_progress=on_word_progress,
        progress_every=progress_every,
    )
