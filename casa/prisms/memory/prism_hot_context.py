#!/usr/bin/env python3
"""Hot-context prism — edges only (ADR-0016)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import time
from typing import Any

from casa.domain.prism_ids import PRISM_KIND_HOT_CONTEXT
from casa.domain.prism_wire import normalize_prisms, prism_kind, prisms
from casa.prisms.memory.memory_prisms import ensure_prisms


def _edge_id() -> str:
    return f"e-{int(time.time() * 1000) % 10_000_000}"


def _norm_edge(src: str, relation: str, dst: str) -> tuple[str, str, str]:
    return src.strip()[:120], relation.strip()[:48], dst.strip()[:120]


def hot_edges(state: dict) -> list[dict[str, Any]]:
    """All edges from prisms with kind=hot_context (canonical + agent-spawned)."""
    normalize_prisms(state)
    out: list[dict[str, Any]] = []
    for pid, block in prisms(state).items():
        if not isinstance(block, dict):
            continue
        if prism_kind(state, pid) != PRISM_KIND_HOT_CONTEXT:
            continue
        out.extend(block.get("edges") or [])
    return out


def add_hot_edge(
    state: dict,
    src: str,
    relation: str,
    dst: str,
    *,
    prism_id: str | None = None,
    salience: float = 1.0,
    ttl_ticks: int | None = None,
    provenance: str = "tick",
    dedupe: bool = True,
) -> dict[str, Any]:
    """Append or bump salience on matching edge (default canonical hot prism)."""
    ensure_prisms(state)
    from casa.domain.prism_ids import PRISM_HOT_CONTEXT
    from casa.domain.prism_wire import prism_block, prism_hot_context

    pid = prism_id or PRISM_HOT_CONTEXT
    block = prism_hot_context(state) if pid == PRISM_HOT_CONTEXT else prism_block(state, pid)
    if prism_kind(state, pid) != PRISM_KIND_HOT_CONTEXT:
        raise ValueError(f"prism {pid!r} is not kind hot_context")
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


def remove_hot_edge(
    state: dict,
    src: str,
    relation: str,
    dst: str,
    *,
    prism_id: str | None = None,
) -> bool:
    """Drop matching hot edge (Kolb relink / cleanup)."""
    normalize_prisms(state)
    from casa.domain.prism_ids import PRISM_HOT_CONTEXT
    from casa.domain.prism_wire import prism_block, prism_hot_context

    pid = prism_id or PRISM_HOT_CONTEXT
    block = prism_hot_context(state) if pid == PRISM_HOT_CONTEXT else prism_block(state, pid)
    if prism_kind(state, pid) != PRISM_KIND_HOT_CONTEXT:
        return False
    src_n, rel_n, dst_n = _norm_edge(src, relation, dst)
    edges: list[dict[str, Any]] = block.get("edges") or []
    kept = [
        row
        for row in edges
        if not (
            row.get("src") == src_n
            and row.get("relation") == rel_n
            and row.get("dst") == dst_n
        )
    ]
    if len(kept) == len(edges):
        return False
    block["edges"] = kept
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return True


def prune_hot_context(
    state: dict,
    *,
    max_edges: int = 2048,
    min_salience: float = 0.05,
) -> dict[str, Any]:
    normalize_prisms(state)
    fv = int(state.get("field_version") or 0)
    total_kept = 0
    total_removed = 0
    bumped = False
    for pid, block in prisms(state).items():
        if not isinstance(block, dict) or prism_kind(state, pid) != PRISM_KIND_HOT_CONTEXT:
            continue
        cap = int(block.get("max_edges") or max_edges)
        edges = list(block.get("edges") or [])
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
        kept = kept[: min(max_edges, cap)]
        removed = len(edges) - len(kept)
        block["edges"] = kept
        total_kept += len(kept)
        total_removed += removed
        if removed:
            bumped = True
    if bumped:
        state["field_version"] = fv + 1
    return {"kept": total_kept, "removed": total_removed}


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


def _headword_from_hot_token(tok: str) -> str | None:
    """Map hot edge endpoint to normalized headword when possible."""
    t = (tok or "").strip()
    if not t or t.startswith("cue:"):
        return None
    if t.startswith("C:"):
        t = t[2:]
    if t.startswith("lang.word."):
        return t[len("lang.word.") :].strip().lower()
    return None


def hot_word_salience_for_cue(state: dict, cue: str) -> dict[str, float]:
    """Headword → max salience from hot edges touching cue (for T9 re-rank)."""
    cue_l = cue.strip().lower()[:48]
    if not cue_l:
        return {}
    boosts: dict[str, float] = {}
    for row in hot_edges(state):
        src = str(row.get("src") or "").lower()
        dst = str(row.get("dst") or "")
        if cue_l not in src and cue_l not in dst.lower():
            continue
        sal = float(row.get("salience") or 0)
        for tok in (dst, str(row.get("src") or "")):
            word = _headword_from_hot_token(tok)
            if word:
                boosts[word] = max(boosts.get(word, 0.0), sal)
    return boosts


def apply_hot_boost_to_ranked(
    ranked: list[tuple[str, int]],
    boosts: dict[str, float],
    *,
    vote_scale: int = 40,
) -> list[tuple[str, int]]:
    """Re-order L2 prefix candidates using P0 hot salience (ADR-0016 / P3 order)."""
    if not boosts:
        return ranked

    def sort_key(item: tuple[str, int]) -> tuple[float, int, str]:
        word, votes = item
        w = word.strip().lower()
        bonus = int(boosts.get(w, 0.0) * vote_scale)
        return (-(votes + bonus), len(word), word)

    return sorted(ranked, key=sort_key)


HOT_SOFT_EDGE_COUNT = 1024


def merge_hot_context_digest(state: dict, cue: str, *, limit: int = 16) -> dict[str, Any]:
    """P0 digest for tick/predict (hints + budget signals)."""
    edges = hot_edges(state)
    hints = hot_digest_for_cue(state, cue, limit=limit) if cue else []
    out: dict[str, Any] = {"hints": hints, "edge_count": len(edges), "cue": cue}
    if len(edges) > HOT_SOFT_EDGE_COUNT:
        out["soft_budget_warning"] = True
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
