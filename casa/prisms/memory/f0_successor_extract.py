#!/usr/bin/env python3
"""Emergent math.num.* |successor| math.num.* from ordered episode experience."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.memory.f0_extract_gate import record_extract_provenance
from casa.prisms.memory.f0_pattern_extract import (
    constant_step,
    count_row_group_key,
    numeral_surface_to_int,
)
from casa.prisms.memory.f0_stack import decode_f0_lattice, mint_episode_links

_SCENE_STEP = re.compile(r"count_row\s+step=(\d+)", re.I)


def scene_cluster_key(scene: str) -> str | None:
    """Group ordered numerals by shared scene label (count_row or teacher scene)."""
    s = str(scene or "").strip()
    if not s:
        return None
    key = count_row_group_key(s)
    if key:
        return key
    if _SCENE_STEP.search(s):
        return None
    return s


def _successor_on_field(lattices: dict[str, dict], lattice_id: str, src: str, dst: str) -> bool:
    if lattice_id not in lattices:
        return False
    dec = decode_f0_lattice(lattices[lattice_id], min_votes=1)
    edge = f"{src}|successor|{dst}"
    return edge in set(dec.get("edges") or [])


def extract_emergent_successors(
    lattices: dict[str, dict],
    episodes: list[dict[str, Any]],
    state: dict,
    *,
    lattice_id: str = "schema-math",
    copies: int = 4,
    min_pairs: int = 2,
) -> list[dict[str, Any]]:
    """Infer successor chain from consecutive numerals in the same scene cluster."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for ep in episodes or []:
        if ep.get("kind") not in (None, "surface"):
            continue
        key = scene_cluster_key(str(ep.get("scene") or ""))
        if not key:
            continue
        cid = ep.get("concept_id")
        if not (cid and str(cid).startswith("math.num.")):
            continue
        val = numeral_surface_to_int(str(ep.get("cue") or ep.get("correct") or ""))
        if val is None:
            continue
        groups.setdefault(key, []).append({**ep, "_value": val})

    pending_links: list[dict[str, str]] = []
    pair_episodes: list[str] = []

    for _key, rows in groups.items():
        rows.sort(key=lambda r: int(r["_value"]))
        values = [int(r["_value"]) for r in rows]
        if constant_step(values) != 1:
            continue
        for i in range(len(rows) - 1):
            a, b = rows[i], rows[i + 1]
            if int(b["_value"]) - int(a["_value"]) != 1:
                continue
            src = str(a["concept_id"])
            dst = str(b["concept_id"])
            if _successor_on_field(lattices, lattice_id, src, dst):
                continue
            link = {"src": src, "relation": "successor", "dst": dst}
            if link in pending_links:
                continue
            pending_links.append(link)
            if a.get("id"):
                pair_episodes.append(str(a["id"]))
            if b.get("id"):
                pair_episodes.append(str(b["id"]))

    if len(pending_links) < min_pairs:
        return []

    minted = mint_episode_links(lattices, lattice_id=lattice_id, links=pending_links, copies=copies)
    record_extract_provenance(
        state,
        "successor:cluster",
        episode_ids=sorted(set(pair_episodes)),
        kind="emergent_successor",
    )
    return [{"kind": "emergent_successor", "links": minted, "count": len(minted), "provenance_episodes": pair_episodes}]
