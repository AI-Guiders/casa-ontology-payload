#!/usr/bin/env python3
"""Persist situation memory on the field — fingerprints as edge-tokens on a lattice.

The in-session memory (situation_memory.py) becomes durable by minting each remembered
situation as edges on the CASA field, so it lives in field_state and survives across
sessions like everything else:

    sit.<id>|edge|on(lex.apple,lex.table)
    sit.<id>|edge|near(lex.table,lex.window)
    sit.<id>|label|яблоко_на_столе_у_окна

load_memory decodes the lattice and reconstructs the in-memory structure that the
recall functions (seen / recall_containing / recall_similar) already operate on. Same
substrate (strengthen/decode/weaken) as the rest of the conceptual network — auditable,
no separate database.
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.situation import canonical_edges, fingerprint

_SIT = "sit."
_EDGE = "edge"
_LABEL = "label"


def _lats(state: dict) -> dict:
    from casa.prisms.memory.memory_prisms import memory_lattices

    return memory_lattices(state)


def persist_situation(state: dict, lattice_id: str, graph: dict[str, Any], *, label: str | None = None) -> int | None:
    """Mint a sensible situation onto the field. Returns its id, or None for a non-situation."""
    from casa.prisms.memory.f0_stack import strengthen_graph_edge

    edges = canonical_edges(graph)
    if not edges:
        return None
    fid = fingerprint(graph)["id"]
    src = f"{_SIT}{fid}"
    lats = _lats(state)
    for ek in edges:
        strengthen_graph_edge(lats, lattice_id, src, _EDGE, ek)
    if label:
        strengthen_graph_edge(lats, lattice_id, src, _LABEL, label.strip().replace(" ", "_"))
    return fid


def load_memory(state: dict, lattice_id: str) -> dict[str, Any]:
    """Reconstruct the situation memory from the field (compatible with recall_*)."""
    from casa.prisms.memory.f0_stack import decode_f0_lattice

    lat = _lats(state).get(lattice_id)
    edges = decode_f0_lattice(lat).get("edges") or [] if lat else []
    sits: dict[int, dict[str, Any]] = {}
    for e in edges:
        if not e.startswith(_SIT):
            continue
        parts = e.split("|", 2)
        if len(parts) != 3:
            continue
        src, rel, dst = parts
        try:
            sid = int(src[len(_SIT):])
        except ValueError:
            continue
        rec = sits.setdefault(sid, {"id": sid, "edges": set(), "label": None})
        if rel == _EDGE:
            rec["edges"].add(dst)
        elif rel == _LABEL:
            rec["label"] = dst.replace("_", " ")
    memory: dict[str, Any] = {"situations": []}
    for sid, rec in sits.items():
        ek = sorted(rec["edges"])
        memory["situations"].append({"id": sid, "edges": ek, "key": " & ".join(ek), "label": rec["label"]})
    memory["situations"].sort(key=lambda r: r["key"])
    return memory


def forget_situation(state: dict, lattice_id: str, fid: int) -> int:
    """Remove a persisted situation's edges from the field. Returns edges removed."""
    from casa.prisms.memory.f0_stack import decode_f0_lattice, weaken_graph_edge

    lat = _lats(state).get(lattice_id)
    if not lat:
        return 0
    src = f"{_SIT}{fid}"
    removed = 0
    for e in list(decode_f0_lattice(lat).get("edges") or []):
        if e.startswith(f"{src}|"):
            s, rel, dst = e.split("|", 2)
            removed += 1 if weaken_graph_edge(_lats(state), lattice_id, s, rel, dst) else 0
    return removed
