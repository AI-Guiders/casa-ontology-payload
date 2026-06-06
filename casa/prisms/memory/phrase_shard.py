#!/usr/bin/env python3
"""L3 phrase lattice sharding — route field tokens across phrase shard grids."""

from __future__ import annotations

import re
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
PHRASES_MONOLITH = "phrases"
PHRASES_NUMERIC_RE = re.compile(r"^phrases-\d{2}$")
PHRASES_SHARD_PREFIX = "phrases-"
L3_Z_LEVEL = 3
DEFAULT_L3_NUM_SHARDS = 64
DEFAULT_LATTICE_SIZE = 32

SHARD_NAMING_NUMERIC = "numeric"
SHARD_NAMING_TOKEN_RANGE = "token_range"
DEFAULT_SHARD_NAMING = SHARD_NAMING_NUMERIC

DEFAULT_TOKEN_SLUG_LEN = 20


def phrase_token_label(token: str) -> str:
    """Entity head before payload (full label for manifest)."""
    t = str(token or "").strip()
    return t.split("|", 1)[0]


def phrase_token_kind_hint(token: str) -> str:
    """Human hint: entity / word / meta."""
    head = phrase_token_label(token)
    if head.startswith("E:lang.word."):
        return "word entity"
    if head.startswith("E:"):
        return "entity"
    if head.startswith("M:"):
        return "meta"
    if head.startswith("C:"):
        return "concept"
    return "field token"


def phrase_token_slug_part(token: str, *, max_len: int = DEFAULT_TOKEN_SLUG_LEN) -> str:
    """Filesystem-safe slug from a field token head (~20 chars)."""
    head = phrase_token_label(token)
    if len(head) >= 2 and head[1] == ":":
        head = head[2:]
    chars: list[str] = []
    for ch in head:
        if ch.isalnum() or ch in ".-_":
            chars.append(ch)
        elif ch.isspace():
            chars.append("-")
    out = "".join(chars).strip("-")
    if not out:
        return "empty"
    return out[:max_len] if len(out) > max_len else out


def phrase_token_range_slug(token_lo: str, token_hi: str) -> str:
    lo = phrase_token_slug_part(token_lo)
    hi = phrase_token_slug_part(token_hi)
    if lo == hi:
        return lo
    return f"{lo}-{hi}"


def phrase_token_range_lattice_id(token_lo: str, token_hi: str) -> str:
    return f"{PHRASES_SHARD_PREFIX}{phrase_token_range_slug(token_lo, token_hi)}"


def attach_token_range_shard_ids(ranges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill shard_id on each quantile range row (token_lo–token_hi slug)."""
    out: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for row in ranges:
        r = dict(row)
        lo = str(r.get("token_lo") or "")
        hi = str(r.get("token_hi") or "")
        base = phrase_token_range_lattice_id(lo, hi)
        if base in seen:
            seen[base] += 1
            r["shard_id"] = f"{base}-{seen[base]}"
        else:
            seen[base] = 0
            r["shard_id"] = base
        if lo:
            r.setdefault("token_hint", phrase_token_kind_hint(lo))
        out.append(r)
    return out


def token_range_shard_id(cfg: dict[str, Any], shard_index: int) -> str | None:
    ranges = cfg.get("token_ranges") or []
    if shard_index < 0 or shard_index >= len(ranges):
        return None
    row = ranges[shard_index]
    sid = row.get("shard_id")
    if sid:
        return str(sid)
    lo = str(row.get("token_lo") or "")
    hi = str(row.get("token_hi") or "")
    if lo or hi:
        return phrase_token_range_lattice_id(lo, hi)
    return None


def build_semantic_l3_rename_map(cfg: dict[str, Any]) -> dict[str, str]:
    """Map legacy numeric shard ids → token-range phrase ids."""
    ranges = attach_token_range_shard_ids(list(cfg.get("token_ranges") or []))
    mapping: dict[str, str] = {}
    for row in ranges:
        idx = int(row.get("shard", -1))
        if idx < 0:
            continue
        new_id = str(row.get("shard_id") or "")
        if not new_id:
            continue
        for old in (f"{L3_SHARD_PREFIX}{idx:02d}", f"{PHRASES_SHARD_PREFIX}{idx:02d}"):
            if old != new_id:
                mapping[old] = new_id
    return mapping


def infer_token_ranges_from_shards(
    state: dict,
    *,
    num_shards: int | None = None,
) -> list[dict[str, Any]]:
    """Derive token_lo/hi per shard from live lattice contents (post-crash debug)."""
    cfg = phrase_sharding_config(state)
    n = int(num_shards if num_shards is not None else cfg.get("num_shards") or DEFAULT_L3_NUM_SHARDS)
    lattices = memory_lattices(state)
    from casa.prisms.memory.nca_codec import tokens_from_lattice

    ranges: list[dict[str, Any]] = []
    for shard in range(max(1, n)):
        lid = f"{L3_SHARD_PREFIX}{shard:02d}"
        if lid not in lattices:
            alt = f"{PHRASES_SHARD_PREFIX}{shard:02d}"
            lid = alt if alt in lattices else lid
        toks = sorted(tokens_from_lattice(lattices.get(lid) or {}))
        count = len(toks)
        if count == 0:
            lo = hi = ""
            label = "∅"
            hint = ""
        else:
            lo, hi = toks[0], toks[-1]
            label = _range_label(phrase_token_label(lo), phrase_token_label(hi), max_len=72)
            hint = phrase_token_kind_hint(lo)
        ranges.append(
            {
                "shard": shard,
                "plan": LEX_PLAN_CORPUS_QUANTILE,
                "token_lo": lo,
                "token_hi": hi,
                "label": label,
                "token_count": count,
                "token_hint": hint,
            }
        )
    return ranges


def is_l3_phrase_lattice(lattice_id: str) -> bool:
    lid = str(lattice_id)
    return (
        lid in (LEGACY_L3, PHRASES_MONOLITH)
        or lid.startswith(L3_SHARD_PREFIX)
        or PHRASES_NUMERIC_RE.fullmatch(lid) is not None
        or (lid.startswith(PHRASES_SHARD_PREFIX) and lid != PHRASES_MONOLITH)
    )


def _l3_shard_index(lattice_id: str, token_ranges: list[dict[str, Any]] | None = None) -> int | None:
    lid = str(lattice_id)
    if token_ranges:
        for row in token_ranges:
            if str(row.get("shard_id") or "") == lid:
                return int(row.get("shard", -1))
    if lid.startswith(L3_SHARD_PREFIX):
        try:
            return int(lid[len(L3_SHARD_PREFIX) :])
        except ValueError:
            return None
    m = PHRASES_NUMERIC_RE.fullmatch(lid)
    if m:
        return int(lid.split("-", 1)[1])
    return None


def phrase_sharding_config(state: dict) -> dict[str, Any]:
    state = ensure_prisms(state)
    cfg = dict(state.get("l3_sharding") or {})
    cfg.setdefault("enabled", True)
    cfg.setdefault("num_shards", DEFAULT_L3_NUM_SHARDS)
    cfg.setdefault("legacy_lattice", LEGACY_L3)
    cfg.setdefault("shard_prefix", L3_SHARD_PREFIX)
    cfg.setdefault("shard_naming", DEFAULT_SHARD_NAMING)
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
                "label": _range_label(phrase_token_label(lo), phrase_token_label(hi), max_len=72) if count else "∅",
                "token_count": count,
                "token_hint": phrase_token_kind_hint(lo) if lo else "",
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
    sharding_cfg: dict[str, Any] | None = None,
) -> str:
    if mode == SHARD_MODE_HASH:
        idx = l3_shard_index_hash(token, num_shards=num_shards)
    else:
        starts = shard_starts or []
        idx = l3_shard_index_quantile(token, num_shards=num_shards, shard_starts=starts)
    cfg = sharding_cfg or {}
    if str(cfg.get("shard_naming") or DEFAULT_SHARD_NAMING) == SHARD_NAMING_TOKEN_RANGE:
        sid = token_range_shard_id(cfg, idx)
        if sid:
            return sid
    prefix = shard_prefix or str(cfg.get("shard_prefix") or L3_SHARD_PREFIX)
    if prefix.startswith(PHRASES_SHARD_PREFIX) and prefix != PHRASES_SHARD_PREFIX:
        return f"{prefix}{idx:02d}"
    return f"{prefix}{idx:02d}"


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
        sharding_cfg=cfg,
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


def phrase_shard_stats(state: dict) -> dict[str, Any]:
    from casa.prisms.memory.nca_codec import tokens_from_lattice

    cfg = phrase_sharding_config(state)
    ranges = list(cfg.get("token_ranges") or [])
    lattices = memory_lattices(state)
    naming = str(cfg.get("shard_naming") or DEFAULT_SHARD_NAMING)
    rows: list[dict[str, Any]] = []
    if naming == SHARD_NAMING_TOKEN_RANGE and ranges:
        for row in ranges:
            sid = int(row.get("shard", -1))
            lid = str(row.get("shard_id") or "")
            if not lid and sid >= 0:
                lid = token_range_shard_id(cfg, sid) or f"{cfg.get('shard_prefix', L3_SHARD_PREFIX)}{sid:02d}"
            lat = lattices.get(lid) or {}
            toks = tokens_from_lattice(lat)
            rows.append(
                {
                    "lattice_id": lid,
                    "shard_index": sid,
                    "token_count": len(toks),
                    "token_range": row.get("label"),
                    "token_hint": row.get("token_hint"),
                    "plan_token_count": row.get("token_count"),
                }
            )
    else:
        for lid in l3_phrase_lattice_ids(state):
            if lid in (LEGACY_L3, PHRASES_MONOLITH):
                continue
            lat = lattices.get(lid) or {}
            toks = tokens_from_lattice(lat)
            row: dict[str, Any] = {"lattice_id": lid, "token_count": len(toks)}
            sid = _l3_shard_index(lid, ranges)
            if sid is not None:
                row["shard_index"] = sid
                if sid < len(ranges):
                    row["token_range"] = ranges[sid].get("label")
                    row["token_hint"] = ranges[sid].get("token_hint")
                    row["plan_token_count"] = ranges[sid].get("token_count")
            rows.append(row)
    return {
        "enabled": cfg.get("enabled"),
        "mode": cfg.get("mode"),
        "lex_plan": cfg.get("lex_plan"),
        "num_shards": cfg.get("num_shards"),
        "legacy_lattice": cfg.get("legacy_lattice"),
        "indexed_tokens": len(cfg.get("token_index") or {}),
        "token_ranges": ranges if cfg.get("mode") == SHARD_MODE_LEXICOGRAPHIC else None,
        "shard_naming": cfg.get("shard_naming"),
        "lattices": rows,
    }


def monolith_over_ltm_limit(state: dict, *, lattice_id: str | None = None) -> bool:
    cfg = phrase_sharding_config(state)
    lid = lattice_id or str(cfg.get("legacy_lattice") or LEGACY_L3)
    lat = memory_lattices(state).get(lid) or {}
    from casa.prisms.memory.l2_remigrate import LTM_VOCAB_U16_MAX

    return lattice_vocab_size(lat) > LTM_VOCAB_U16_MAX
