#!/usr/bin/env python3
"""Hub neighbor lookup: surface → entity → other-language surfaces on L3."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_stack_v0 import decode_lattice
from casa.prisms.memory.sss_vocab_v0 import norm_word


def _anchor_to_concept(anchor: str) -> str:
    a = (anchor or "").strip()
    if a.startswith("W:"):
        return f"lang.word.{norm_word(a[2:])}"
    if a.startswith("C:"):
        return a[2:]
    if a.startswith("lang.word.") or a.startswith("entity."):
        return a
    return f"lang.word.{norm_word(a)}"


def _parse_edge_raw(edge: str) -> tuple[str, str, str] | None:
    body = edge[2:] if edge.startswith("E:") else edge
    parts = body.split("|")
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def _l3_edges(state: dict, *, min_votes: int = 1) -> list[tuple[str, str, str]]:
    lat = memory_lattices(ensure_prisms(state)).get("L3_phrase") or {}
    dec = decode_lattice(lat, min_votes=min_votes)
    out: list[tuple[str, str, str]] = []
    for raw in dec.get("edges") or []:
        parsed = _parse_edge_raw(str(raw))
        if parsed:
            out.append(parsed)
    return out


def hub_neighbors(
    state: dict,
    anchor: str,
    *,
    rel: str = "denotes",
    via_entity: bool = True,
    min_votes: int = 1,
) -> dict[str, Any]:
    """
    Given W:cow, lang.word.cow, or entity.cow — return linked concepts on L3 hub.

    With via_entity=True (default): surface → entity → other surfaces (not word-word align).
    """
    cid = _anchor_to_concept(anchor)
    edges = _l3_edges(state, min_votes=min_votes)

    entities: list[str] = []
    neighbors: list[dict[str, Any]] = []
    seen: set[str] = {cid}

    if cid.startswith("entity."):
        entities = [cid]
    elif via_entity:
        for src, r, dst in edges:
            if src == cid and r == rel and dst.startswith("entity."):
                entities.append(dst)

    entities = sorted(set(entities))

    def add_neighbor(concept_id: str, *, via: str, relation: str) -> None:
        if concept_id in seen:
            return
        seen.add(concept_id)
        neighbors.append({"concept_id": concept_id, "via": via, "relation": relation})

    for ent in entities:
        add_neighbor(ent, via="entity", relation=rel)
        for src, r, dst in edges:
            if via_entity and r == rel and dst == ent and src.startswith("lang.word."):
                add_neighbor(src, via=ent, relation=r)
            if src == ent and r.startswith("surface.") and dst.startswith("lang.word."):
                add_neighbor(dst, via=ent, relation=r)

    if not via_entity:
        for src, r, dst in edges:
            if src == cid and r == rel:
                add_neighbor(dst, via=cid, relation=r)
            elif dst == cid and r == rel:
                add_neighbor(src, via=cid, relation=r)

    concept_ids = [n["concept_id"] for n in neighbors]
    return {
        "anchor": anchor,
        "concept_id": cid,
        "rel": rel,
        "via_entity": via_entity,
        "entities": entities,
        "neighbors": neighbors,
        "concept_ids": concept_ids,
    }


def neighbor_surfaces(
    state: dict,
    anchor: str,
    *,
    rel: str = "denotes",
    exclude_anchor: bool = True,
) -> list[str]:
    """Return lang.word.* surface concepts reachable via entity hub (excluding anchor surface)."""
    rep = hub_neighbors(state, anchor, rel=rel, via_entity=True)
    anchor_cid = rep["concept_id"]
    out: list[str] = []
    for cid in rep["concept_ids"]:
        if not cid.startswith("lang.word."):
            continue
        if exclude_anchor and cid == anchor_cid:
            continue
        out.append(cid)
    return out
