#!/usr/bin/env python3
"""Hot-context prism — edges only (ADR-0016)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import time
from typing import Any

from casa.prisms.shared.prism_state import PRISM_HOT_CONTEXT, normalize_prisms, prism_hot_context
from casa.prisms.memory.memory_prisms import ensure_prisms


def _edge_id() -> str:
    return f"e-{int(time.time() * 1000) % 10_000_000}"


def _norm_edge(src: str, relation: str, dst: str) -> tuple[str, str, str]:
    return src.strip()[:120], relation.strip()[:48], dst.strip()[:120]


def hot_edges(state: dict) -> list[dict[str, Any]]:
    normalize_prisms(state)
    return list(prism_hot_context(state).get("edges") or [])


def add_hot_edge(
    state: dict,
    src: str,
    relation: str,
    dst: str,
    *,
    salience: float = 1.0,
    ttl_ticks: int | None = None,
    provenance: str = "tick",
    dedupe: bool = True,
) -> dict[str, Any]:
    """Append or bump salience on matching edge."""
    ensure_prisms(state)
    block = prism_hot_context(state)
    src_n, rel_n, dst_n = _norm_edge(src, relation, dst)
    if not src_n or not rel_n or not dst_n:
        raise ValueError("src, relation, dst required")

    edges: list[dict[str, Any]] = block.setdefault("edges", [])
    if dedupe:
        for row in edges:
            if row.get("src") == src_n and row.get("relation") == rel_n and row.get("dst") == dst_n:
                row["salience"] = float(row.get("salience") or 0) + salience
                row["last_tick"] = int(state.get("field_version") or 0)
                if ttl_ticks is not None:
                    row["ttl_ticks"] = ttl_ticks
                state["field_version"] = int(state.get("field_version") or 0) + 1
                return row

    max_edges = int(block.get("max_edges") or 4096)
    if len(edges) >= max_edges:
        prune_hot_context(state, max_edges=max_edges - 1)

    row = {
        "id": _edge_id(),
        "src": src_n,
        "relation": rel_n,
        "dst": dst_n,
        "salience": float(salience),
        "provenance": provenance[:64],
        "created_field_version": int(state.get("field_version") or 0),
        "last_tick": int(state.get("field_version") or 0),
    }
    if ttl_ticks is not None:
        row["ttl_ticks"] = int(ttl_ticks)
    edges.append(row)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return row


def prune_hot_context(
    state: dict,
    *,
    max_edges: int = 2048,
    min_salience: float = 0.05,
) -> dict[str, Any]:
    block = prism_hot_context(state)
    edges = list(block.get("edges") or [])
    fv = int(state.get("field_version") or 0)
    kept: list[dict[str, Any]] = []
    for row in edges:
        sal = float(row.get("salience") or 0)
        ttl = row.get("ttl_ticks")
        created = int(row.get("created_field_version") or 0)
        if sal < min_salience:
            continue
        if ttl is not None and fv - created > int(ttl):
            continue
        kept.append(row)
    kept.sort(key=lambda r: float(r.get("salience") or 0), reverse=True)
    kept = kept[:max_edges]
    removed = len(edges) - len(kept)
    block["edges"] = kept
    if removed:
        state["field_version"] = fv + 1
    return {"kept": len(kept), "removed": removed}


def hot_neighbors(
    state: dict,
    node: str,
    *,
    min_salience: float = 0.1,
) -> list[dict[str, Any]]:
    """Edges touching node (src or dst), sorted by salience."""
    node = node.strip()[:120]
    out: list[dict[str, Any]] = []
    for row in hot_edges(state):
        if float(row.get("salience") or 0) < min_salience:
            continue
        if row.get("src") == node or row.get("dst") == node:
            out.append(row)
    out.sort(key=lambda r: float(r.get("salience") or 0), reverse=True)
    return out


def hot_digest_for_cue(state: dict, cue: str, *, limit: int = 16) -> list[str]:
    """Concept/token ids linked to cue prefix for predict bias."""
    cue = cue.strip().lower()[:48]
    if not cue:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for row in hot_edges(state):
        src = str(row.get("src") or "")
        dst = str(row.get("dst") or "")
        if cue not in src.lower() and cue not in dst.lower():
            continue
        for tok in (dst, src):
            if tok.startswith("C:") or tok.startswith("lang.") or tok.startswith("math."):
                if tok not in seen:
                    seen.add(tok)
                    out.append(tok)
        if len(out) >= limit:
            break
    return out
