#!/usr/bin/env python3
"""L3 monolith → sharded phrase lattices (ltm v0 u16 vocab cap)."""

from __future__ import annotations

import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from casa.prisms.memory.l2_remigrate import LTM_VOCAB_U16_MAX
from casa.prisms.memory.lexicon_shard import lattice_vocab_size
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.phrase_shard import (
    DEFAULT_L3_NUM_SHARDS,
    LEGACY_L3,
    L3_SHARD_PREFIX,
    clear_legacy_l3_monolith,
    clear_l3_shards,
    configure_phrase_sharding,
    copy_token_to_lattice,
    phrase_sharding_config,
    placements_by_token,
    route_l3_lattice,
)
from casa.prisms.shared.migrate_progress import resolve_parallel_workers

TokenProgressFn = Callable[[int, int, str], None] | None

_PARALLEL_MIN_TOKENS = 2000


def tokens_from_l3_monolith(state: dict, *, lattice_id: str | None = None) -> list[str]:
    cfg = phrase_sharding_config(state)
    lid = lattice_id or str(cfg.get("legacy_lattice") or LEGACY_L3)
    lat = memory_lattices(state).get(lid) or {}
    from casa.prisms.memory.nca_codec import tokens_from_lattice

    return tokens_from_lattice(lat)


def needs_l3_remigrate(state: dict) -> bool:
    """True when legacy L3_phrase is too fat for .ltm or tokens not yet on shards."""
    state = ensure_prisms(state)
    cfg = phrase_sharding_config(state)
    legacy = str(cfg.get("legacy_lattice") or LEGACY_L3)
    lats = memory_lattices(state)
    leg = lats.get(legacy) or {}
    leg_vocab = lattice_vocab_size(leg)
    if leg_vocab == 0:
        return False
    if leg_vocab > LTM_VOCAB_U16_MAX:
        return True
    shard_ids = [lid for lid in lats if lid.startswith(L3_SHARD_PREFIX)]
    if not shard_ids:
        return leg_vocab > 0
    indexed = len(cfg.get("token_index") or {})
    on_monolith = len(tokens_from_l3_monolith(state, lattice_id=legacy))
    return on_monolith > 256 and indexed < on_monolith // 2


def _remigrate_sequential(
    state: dict,
    keys: list[str],
    by_pos: dict[str, list],
    *,
    on_token_progress: TokenProgressFn,
    progress_every: int,
) -> int:
    total = len(keys)
    copies = 0
    for i, tok in enumerate(keys, 1):
        shard = route_l3_lattice(state, tok)
        lat = memory_lattices(state)[shard]
        copies += copy_token_to_lattice(lat, tok, by_pos.get(tok, []))
        if on_token_progress and (i == 1 or i == total or i % progress_every == 0):
            on_token_progress(i, total, shard)
    return copies


def _remigrate_parallel(
    state: dict,
    keys: list[str],
    by_pos: dict[str, list],
    *,
    workers: int,
    on_token_progress: TokenProgressFn,
    progress_every: int,
) -> int:
    buckets: dict[str, list[tuple[str, list]]] = defaultdict(list)
    for tok in keys:
        shard = route_l3_lattice(state, tok)
        buckets[shard].append((tok, by_pos.get(tok, [])))

    total = len(keys)
    copies = 0
    done = 0
    lock = threading.Lock()

    def _shard_job(shard_id: str, items: list[tuple[str, list]]) -> int:
        nonlocal done
        lat = memory_lattices(state)[shard_id]
        local = 0
        for tok, pos in items:
            local += copy_token_to_lattice(lat, tok, pos)
            if on_token_progress:
                with lock:
                    done += 1
                    n = done
                if n == 1 or n == total or n % progress_every == 0:
                    on_token_progress(n, total, shard_id)
        return local

    max_workers = min(workers, max(1, len(buckets)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_shard_job, sid, items) for sid, items in buckets.items()]
        for fut in as_completed(futures):
            copies += fut.result()
    return copies


def remigrate_l3_from_monolith(
    state: dict,
    tokens: list[str] | None = None,
    *,
    num_shards: int = DEFAULT_L3_NUM_SHARDS,
    clear_monolith: bool = True,
    on_token_progress: TokenProgressFn = None,
    progress_every: int = 5000,
    parallel_workers: int = 0,
) -> dict[str, Any]:
    """Move field tokens off L3_phrase monolith onto L3_phrase_XX (preserve x,y placements)."""
    state = ensure_prisms(state)
    cfg = phrase_sharding_config(state)
    legacy = str(cfg.get("legacy_lattice") or LEGACY_L3)
    leg_lat = memory_lattices(state).get(legacy) or {}
    by_pos = placements_by_token(leg_lat)
    keys = tokens if tokens is not None else sorted(by_pos.keys())
    if not keys:
        return {"status": "noop", "reason": "no_tokens_on_monolith", "legacy_lattice": legacy}

    cfg["enabled"] = True
    configure_phrase_sharding(cfg, keys, num_shards=num_shards)
    state["l3_sharding"] = cfg

    clear_l3_shards(state, keep_legacy=True)

    workers = resolve_parallel_workers(parallel_workers)
    min_tokens = 100 if parallel_workers >= 2 else _PARALLEL_MIN_TOKENS
    use_parallel = workers >= 2 and len(keys) >= min_tokens
    if use_parallel:
        copies = _remigrate_parallel(
            state,
            keys,
            by_pos,
            workers=workers,
            on_token_progress=on_token_progress,
            progress_every=progress_every,
        )
    else:
        copies = _remigrate_sequential(
            state,
            keys,
            by_pos,
            on_token_progress=on_token_progress,
            progress_every=progress_every,
        )

    if clear_monolith:
        clear_legacy_l3_monolith(state, lattice_id=legacy)

    state["field_version"] = int(state.get("field_version") or 0) + 1

    shard_vocab_max = 0
    for lid in memory_lattices(state):
        if lid.startswith(L3_SHARD_PREFIX):
            shard_vocab_max = max(shard_vocab_max, lattice_vocab_size(memory_lattices(state)[lid]))

    return {
        "status": "ok",
        "legacy_lattice": legacy,
        "tokens_remigrated": len(keys),
        "placements_copied": copies,
        "num_shards": num_shards,
        "monolith_cleared": clear_monolith,
        "max_shard_vocab": shard_vocab_max,
        "field_version": state["field_version"],
        "parallel_workers": workers if use_parallel else 1,
    }


def ensure_l3_sharded_for_export(
    state: dict,
    *,
    force: bool = False,
    on_token_progress: TokenProgressFn = None,
    progress_every: int = 5000,
    parallel_workers: int = 0,
) -> dict[str, Any] | None:
    if not force and not needs_l3_remigrate(state):
        return None
    return remigrate_l3_from_monolith(
        state,
        on_token_progress=on_token_progress,
        progress_every=progress_every,
        parallel_workers=parallel_workers,
    )
