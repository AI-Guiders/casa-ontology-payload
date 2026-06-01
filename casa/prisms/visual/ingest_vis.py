#!/usr/bin/env python3
"""Ingest visual anchors (vis.*) into prism_visual — ADR-0018 v0."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_hot_context import add_hot_edge
from casa.prisms.memory.prism_spawn import spawn_content_lattice, spawn_prism
from casa.prisms.memory.stack import _place_token
from casa.prisms.shared.codec_grid import Grid
from casa.prisms.shared.config_io import load_config
from casa.domain.prism_ids import PRISM_KIND_CONTENT, PRISM_VISUAL
from casa.domain.prism_wire import prism_block

VIS_STACK = Path("design/prisms/visual/stack.json")
VIS_OBJECT = "V1_object"
VIS_CONCEPT_PREFIX = "vis."


def _load_vis_stack() -> dict:
    return load_config(VIS_STACK)


def ensure_prism_visual(state: dict, *, include_scene: bool = False) -> dict[str, Any]:
    """Bootstrap prism_visual + V1_object (and optional V2_scene) lattices."""
    state = ensure_prisms(state)
    spawn_prism(state, PRISM_VISUAL, kind=PRISM_KIND_CONTENT, stack=str(VIS_STACK))
    stack = _load_vis_stack()
    spawned: list[str] = []
    existing = prism_block(state, PRISM_VISUAL).get("lattices") or {}
    for lat in stack.get("lattices") or []:
        if lat.get("status") == "optional_v0" and not include_scene:
            continue
        lid = str(lat.get("legacy_id") or lat.get("lattice_id") or "")
        if not lid or lid in existing:
            if lid:
                spawned.append(lid)
            continue
        spawn_content_lattice(
            state,
            PRISM_VISUAL,
            lid,
            z_level=int(lat.get("z_level") or 1),
            concept_prefix=str(lat.get("concept_prefix") or VIS_CONCEPT_PREFIX),
        )
        spawned.append(lid)
    return {"prism_id": PRISM_VISUAL, "lattice_ids": spawned}


def _strengthen_vis_on_lattice(
    state: dict,
    concept_id: str,
    *,
    lattice_id: str = VIS_OBJECT,
    copies: int = 3,
) -> None:
    cid = concept_id if concept_id.startswith(VIS_CONCEPT_PREFIX) else f"{VIS_CONCEPT_PREFIX}{concept_id}"
    block = prism_block(state, PRISM_VISUAL)
    lats = block.setdefault("lattices", {})
    lat = lats.setdefault(
        lattice_id,
        {
            "z_level": 1,
            "width": 32,
            "height": 32,
            "cells": [[] for _ in range(32 * 32)],
            "concept_prefix": VIS_CONCEPT_PREFIX,
        },
    )
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
    g = _place_token(g, f"C:{cid}", f"C:{cid}", copies=copies, radius=5)
    vtok = f"V:{cid}"
    g = _place_token(g, vtok, vtok, copies=max(2, copies), radius=4)
    lat["cells"] = g.cells


def ingest_vis_claim(
    state: dict,
    claim: dict,
    *,
    copies: int = 3,
    hot_ground: bool = True,
) -> dict[str, Any]:
    """One bundle claim: concept_id, optional image_ref, links → lang.word.*."""
    state = ensure_prisms(state)
    ensure_prism_visual(state)
    cid = str(claim.get("concept_id") or "").strip()
    if not cid:
        return {"status": "skip", "reason": "no_concept_id"}
    _strengthen_vis_on_lattice(state, cid, copies=copies)
    lat = prism_block(state, PRISM_VISUAL)["lattices"][VIS_OBJECT]
    links = claim.get("links") or []
    if isinstance(links, list):
        for dst in links:
            dst_s = str(dst).strip()
            if not dst_s:
                continue
            lang_cid = dst_s if dst_s.startswith("lang.word.") else f"lang.word.{dst_s}"
            etok = f"E:{cid}|ground|{lang_cid}"
            g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
            g = _place_token(g, etok, etok, copies=max(2, copies // 2), radius=3)
            lat["cells"] = g.cells
            if hot_ground:
                add_hot_edge(state, cid, "ground", lang_cid, salience=1.0)
    image_ref = claim.get("image_ref")
    refs = state.setdefault("vis_refs", {})
    if image_ref:
        refs[str(image_ref)] = cid
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {"status": "ok", "concept_id": cid, "image_ref": image_ref}


def ingest_vis_batch(state: dict, claims: list[dict], *, copies: int = 3) -> dict[str, Any]:
    reps = [ingest_vis_claim(state, c, copies=copies) for c in claims]
    ok = sum(1 for r in reps if r.get("status") == "ok")
    return {"claims": len(claims), "ingested": ok, "reports": reps}
