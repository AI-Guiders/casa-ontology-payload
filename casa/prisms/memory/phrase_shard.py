#!/usr/bin/env python3
"""L3 phrase lattice sharding — route field tokens across L3_phrase_XX grids."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import zlib

from casa.prisms.memory.lexicon_shard import (
    DEFAULT_SHARD_MODE,
    LEX_PLAN_CORPUS_QUANTILE,
    SHARD_MODE_HASH,
    SHARD_MODE_LEXICOGRAPHIC,
    _range_label,
    lattice_vocab_size,
)
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.domain.prism_wire import prism_memory

LEGACY_L3 = "L3_phrase"
L3_SHARD_PREFIX = "L3_phrase_"
L3_Z_LEVEL = 3
DEFAULT_L3_NUM_SHARDS = 64
DEFAULT_LATTICE_SIZE = 32


def is_l3_phrase_lattice(lattice_id: str) -> bool:
    lid = str(lattice_id)
    return lid == LEGACY_L3 or lid.startswith(L3_SHARD_PREFIX)


def phrase_sharding_config(state: dict) -> dict[str, Any]:
    state = ensure_prisms(state)
    cfg = dict(state.get("l3_sharding") or {})
    cfg.setdefault("enabled", True)
    cfg.setdefault("num_shards", DEFAULT_L3_NUM_SHARDS)
    cfg.setdefault("legacy_lattice", LEGACY_L3)
    cfg.setdefault("shard_prefix", L3_SHARD_PREFIX)
    cfg.setdefault("mode", DEFAULT_SHARD_MODE)
    cfg.setdefault("lex_plan", LEX_PLAN_CORPUS_QUANTILE)
    cfg.setdefault("token_index", {})
    state["l3_sharding"] = cfg
    return cfg


def build_token_quantile_ranges(
    tokens: Iterable[str],
    *,
    num_shards: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Equal-count bins over sorted unique token strings."""
    unique = sorted({str(t) for t in tokens if t})
    n = len(unique)
    starts: list[str] = []
    ranges: list[dict[str, Any]] = []

    for shard in range(max(1, num_shards)):
        if n == 0:
            starts.append("")
            ranges.append(
                {
                    "shard": shard,
                    "plan": LEX_PLAN_CORPUS_QUANTILE,
                    "token_lo": "",
                    "token_hi": "",
                    "label": "∅",
                    "token_count": 0,
                }
            )
            continue

        i0 = (shard * n) // num_shards
        i1 = ((shard + 1) * n) // num_shards
        if i0 >= n:
            starts.append(unique[-1])
            ranges.append(
                {
                    "shard": shard,
                    "plan": LEX_PLAN_CORPUS_QUANTILE,
                    "token_lo": "",
                    "token_hi": "",
                    "label": "∅",
                    "token_count": 0,
                }
            )
            continue

        starts.append(unique[i0])
        count = max(0, i1 - i0)
        if count == 0:
            lo = hi = unique[min(i0, n - 1)]
        else:
            lo = unique[i0]
            hi = unique[i1 - 1]
        ranges.append(
            {
                "shard": shard,
                "plan": LEX_PLAN_CORPUS_QUANTILE,
                "token_lo": lo,
                "token_hi": hi,
                "label": _range_label(lo[:20], hi[:20], max_len=40) if count else "∅",
                "token_count": count,
            }
        )

    return ranges, starts


def configure_phrase_sharding(cfg: dict[str, Any], tokens: Iterable[str], *, num_shards: int | None = None) -> None:
    n = int(num_shards if num_shards is not None else cfg.get("num_shards") or DEFAULT_L3_NUM_SHARDS)
    ranges, starts = build_token_quantile_ranges(tokens, num_shards=n)
    cfg["num_shards"] = n
    cfg["lex_plan"] = LEX_PLAN_CORPUS_QUANTILE
    cfg["token_ranges"] = ranges
    cfg["token_shard_starts"] = starts


def l3_shard_index_hash(token: str, *, num_shards: int) -> int:
    return zlib.crc32(str(token).encode("utf-8")) % max(1, num_shards)


def l3_shard_index_quantile(token: str, *, num_shards: int, shard_starts: list[str]) -> int:
    if not token or not shard_starts:
        return 0
    shard = 0
    for s in range(1, min(num_shards, len(shard_starts))):
        if shard_starts[s] <= token:
            shard = s
        else:
            break
    return shard


def l3_shard_id(
    token: str,
    *,
    num_shards: int = DEFAULT_L3_NUM_SHARDS,
    mode: str = DEFAULT_SHARD_MODE,
    shard_starts: list[str] | None = None,
    shard_prefix: str = L3_SHARD_PREFIX,
) -> str:
    if mode == SHARD_MODE_HASH:
        idx = l3_shard_index_hash(token, num_shards=num_shards)
    else:
        starts = shard_starts or []
        idx = l3_shard_index_quantile(token, num_shards=num_shards, shard_starts=starts)
    return f"{shard_prefix}{idx:02d}"


def empty_l3_lattice(*, width: int = DEFAULT_LATTICE_SIZE, height: int = DEFAULT_LATTICE_SIZE) -> dict:
    n = width * height
    return {
        "z_level": L3_Z_LEVEL,
        "width": width,
        "height": height,
        "cells": [[] for _ in range(n)],
        "shard": True,
    }


def ensure_l3_lattice(state: dict, lattice_id: str) -> dict:
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    if lattice_id not in lattices:
        lattices[lattice_id] = empty_l3_lattice()
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return lattices[lattice_id]


def register_token_shard(state: dict, token: str, lattice_id: str) -> None:
    cfg = phrase_sharding_config(state)
    idx = dict(cfg.get("token_index") or {})
    idx[str(token)] = lattice_id
    cfg["token_index"] = idx
    state["l3_sharding"] = cfg


def route_l3_lattice(state: dict, token: str) -> str:
    state = ensure_prisms(state)
    cfg = phrase_sharding_config(state)
    ts = str(token)
    if not ts:
        return str(cfg.get("legacy_lattice") or LEGACY_L3)
    idx = cfg.get("token_index") or {}
    if ts in idx:
        return str(idx[ts])
    if not cfg.get("enabled", True):
        return str(cfg.get("legacy_lattice") or LEGACY_L3)
    num = int(cfg.get("num_shards") or DEFAULT_L3_NUM_SHARDS)
    mode = str(cfg.get("mode") or DEFAULT_SHARD_MODE)
    shard = l3_shard_id(
        ts,
        num_shards=num,
        mode=mode,
        shard_starts=cfg.get("token_shard_starts"),
        shard_prefix=str(cfg.get("shard_prefix") or L3_SHARD_PREFIX),
    )
    ensure_l3_lattice(state, shard)
    register_token_shard(state, ts, shard)
    return shard


def l3_phrase_lattice_ids(state: dict) -> list[str]:
    state = ensure_prisms(state)
    cfg = phrase_sharding_config(state)
    legacy = str(cfg.get("legacy_lattice") or LEGACY_L3)
    ids = {lid for lid in memory_lattices(state) if is_l3_phrase_lattice(lid)}
    ids.add(legacy)
    return sorted(ids, key=lambda x: (0 if x == legacy else 1, x))


def placements_by_token(lattice: dict) -> dict[str, list[tuple[int, int]]]:
    w = int(lattice.get("width") or DEFAULT_LATTICE_SIZE)
    h = int(lattice.get("height") or DEFAULT_LATTICE_SIZE)
    cells = lattice.get("cells") or []
    out: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for yi in range(h):
        for xi in range(w):
            idx = yi * w + xi
            for t in cells[idx] if idx < len(cells) else []:
                out[str(t)].append((xi, yi))
    return out


def copy_token_to_lattice(lattice: dict, token: str, positions: list[tuple[int, int]]) -> int:
    w = int(lattice.get("width") or DEFAULT_LATTICE_SIZE)
    h = int(lattice.get("height") or DEFAULT_LATTICE_SIZE)
    cells = lattice.setdefault("cells", [[] for _ in range(w * h)])
    placed = 0
    for x, y in positions:
        if x >= w or y >= h:
            continue
        idx = y * w + x
        row = cells[idx] if idx < len(cells) else []
        if token not in row:
            row.append(token)
            placed += 1
        cells[idx] = row
    lattice["cells"] = cells
    return placed


def clear_l3_shards(state: dict, *, keep_legacy: bool = True) -> None:
    state = ensure_prisms(state)
    cfg = phrase_sharding_config(state)
    lattices = memory_lattices(state)
    legacy = str(cfg.get("legacy_lattice") or LEGACY_L3)
    drop = [lid for lid in list(lattices) if is_l3_phrase_lattice(lid) and lid != legacy]
    for lid in drop:
        del lattices[lid]
    cfg["token_index"] = {}
    state["l3_sharding"] = cfg
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices


def clear_legacy_l3_monolith(state: dict, *, lattice_id: str | None = None) -> None:
    cfg = phrase_sharding_config(state)
    lid = lattice_id or str(cfg.get("legacy_lattice") or LEGACY_L3)
    lattices = memory_lattices(state)
    lat = lattices.get(lid)
    if not lat:
        return
    n = int(lat.get("width") or DEFAULT_LATTICE_SIZE) * int(lat.get("height") or DEFAULT_LATTICE_SIZE)
    lat["cells"] = [[] for _ in range(n)]
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices


def monolith_over_ltm_limit(state: dict, *, lattice_id: str | None = None) -> bool:
    cfg = phrase_sharding_config(state)
    lid = lattice_id or str(cfg.get("legacy_lattice") or LEGACY_L3)
    lat = memory_lattices(state).get(lid) or {}
    from casa.prisms.memory.l2_remigrate import LTM_VOCAB_U16_MAX

    return lattice_vocab_size(lat) > LTM_VOCAB_U16_MAX
