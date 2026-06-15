#!/usr/bin/env python3
"""Situation memory — store situation fingerprints and recall by identity, containment,
or similarity. «Видел ли я такую конфигурацию?» on top of the conceptual network.

A remembered situation is its canonical edge set + stable id. Because edges are sets,
recall is exact set algebra over CONCEPTS (language-independent):
  * seen()             — exact id match (have I seen this exact situation?),
  * recall_containing()— stored situations that INCLUDE the query as a sub-situation
                         (query «яблоко на столе» finds stored «яблоко на столе у окна»),
  * recall_contained() — stored situations CONTAINED in the query,
  * recall_similar()   — ranked by edge-set overlap (Jaccard).

This is the CASA-native retrieval primitive: the fingerprint's bag-of-edges is the key;
overlap is the metric. Exact and auditable, unlike opaque vector search. (For persistence
the edge tokens can live on a lattice; here the memory is an in-session structure.)
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.situation import canonical_edges, fingerprint


def new_memory() -> dict[str, Any]:
    return {"situations": []}


def remember(memory: dict[str, Any], graph: dict[str, Any], *, label: str | None = None) -> dict[str, Any] | None:
    """Store a situation (deduplicated by id). Only SENSIBLE situations are stored — a
    graph with no satisfiable edge (e.g. a category error) is not a situation; returns
    None. Otherwise returns the stored record."""
    edges = canonical_edges(graph)  # satisfied edges only
    if not edges:
        return None
    fid = fingerprint(graph)["id"]
    for rec in memory["situations"]:
        if rec["id"] == fid:
            return rec
    rec = {"id": fid, "edges": edges, "key": " & ".join(edges), "label": label}
    memory["situations"].append(rec)
    return rec


def seen(memory: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any] | None:
    """The stored record for this exact situation, or None."""
    fid = fingerprint(graph)["id"]
    return next((rec for rec in memory["situations"] if rec["id"] == fid), None)


def recall_containing(memory: dict[str, Any], query: dict[str, Any]) -> list[dict[str, Any]]:
    """Stored situations whose edge set INCLUDES the query (query is a sub-situation)."""
    q = set(canonical_edges(query))
    if not q:  # an empty query is vacuously contained in everything — not useful
        return []
    return [rec for rec in memory["situations"] if q <= set(rec["edges"])]


def recall_contained(memory: dict[str, Any], query: dict[str, Any]) -> list[dict[str, Any]]:
    """Stored situations CONTAINED in the query (they are sub-situations of it)."""
    q = set(canonical_edges(query))
    return [rec for rec in memory["situations"] if set(rec["edges"]) <= q]


def recall_similar(
    memory: dict[str, Any], query: dict[str, Any], *, top: int = 5, min_sim: float = 0.0
) -> list[tuple[dict[str, Any], float]]:
    """Stored situations ranked by Jaccard overlap with the query (most similar first)."""
    q = set(canonical_edges(query))
    scored: list[tuple[dict[str, Any], float]] = []
    for rec in memory["situations"]:
        e = set(rec["edges"])
        union = q | e
        sim = (len(q & e) / len(union)) if union else 1.0
        if sim >= min_sim:
            scored.append((rec, round(sim, 3)))
    scored.sort(key=lambda rs: (-rs[1], rs[0]["key"]))
    return scored[:top]


def gate_situation_memory(
    memory: dict[str, Any],
    seen_graphs: list[dict[str, Any]],
    novel_graph: dict[str, Any],
    sub_graph: dict[str, Any],
    super_graph: dict[str, Any],
) -> dict[str, Any]:
    """Verify recall: stored situations are seen and novel ones are not; a sub-situation
    query recalls the stored super-situation that contains it; similarity is ordered."""
    seen_ok = all(seen(memory, g) is not None for g in seen_graphs)
    novel_ok = seen(memory, novel_graph) is None
    containing = recall_containing(memory, sub_graph)
    contain_ok = any(rec["id"] == fingerprint(super_graph)["id"] for rec in containing)
    sims = recall_similar(memory, sub_graph)
    ordered = sims == sorted(sims, key=lambda rs: -rs[1])
    return {
        "passed": bool(seen_ok and novel_ok and contain_ok and ordered),
        "seen_known": seen_ok,
        "novel_unseen": novel_ok,
        "containment_recall": contain_ok,
        "similarity_ordered": ordered,
    }
