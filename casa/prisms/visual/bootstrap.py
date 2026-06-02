#!/usr/bin/env python3
"""Bootstrap prism_visual + LRGB lattices (ADR-0028 / ADR-0018)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
from casa.domain.prism_ids import PRISM_KIND_CONTENT, PRISM_VISUAL
from casa.domain.prism_wire import prism_block, prisms
from casa.domain.visual_tract import (
    LEGACY_LATTICE_V1_OBJECT,
    LATTICE_V1_LUM,
    VISUAL_LATTICE_IDS,
    VISUAL_LATTICE_SPECS,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_router import add_route
from casa.prisms.memory.prism_spawn import empty_content_lattice, spawn_prism
from casa.prisms.shared.config_io import load_config

VIS_STACK = Path("design/prisms/visual/stack.json")
# ADR-0018 alias — primary object/lum lattice
VIS_OBJECT = LATTICE_V1_LUM
VIS_CONCEPT_PREFIX = "vis."


def _load_vis_stack() -> dict:
    return load_config(REPO_ROOT / VIS_STACK)


def _migrate_legacy_v1_object(lattices: dict[str, dict]) -> None:
    if LEGACY_LATTICE_V1_OBJECT not in lattices:
        return
    legacy = lattices.pop(LEGACY_LATTICE_V1_OBJECT)
    if LATTICE_V1_LUM not in lattices:
        legacy["concept_prefix"] = "vis.lum."
        lattices[LATTICE_V1_LUM] = legacy


def ensure_visual_lattices(state: dict, *, include_scene: bool = False) -> list[str]:
    """Ensure LRGB lattices from stack; return newly created ids."""
    block = prism_block(state, PRISM_VISUAL)
    lats = block.setdefault("lattices", {})
    _migrate_legacy_v1_object(lats)
    stack = _load_vis_stack()
    created: list[str] = []
    for lat in stack.get("lattices") or []:
        if lat.get("status") == "optional_v0" and not include_scene:
            continue
        lid = str(lat.get("legacy_id") or lat.get("lattice_id") or "")
        if not lid:
            continue
        if lid in lats:
            lat_w = lats[lid]
            lat_w.setdefault("concept_prefix", str(lat.get("concept_prefix") or ""))
            lat_w.setdefault("prism_id", PRISM_VISUAL)
            continue
        size = lat.get("size") or {}
        lats[lid] = empty_content_lattice(
            width=int(size.get("width") or 32),
            height=int(size.get("height") or 32),
            z_level=int(lat.get("z_level") or 0),
            concept_prefix=str(lat.get("concept_prefix") or ""),
        )
        lats[lid]["prism_id"] = PRISM_VISUAL
        created.append(lid)
    for spec in VISUAL_LATTICE_SPECS:
        if spec.lattice_id in lats:
            continue
        lats[spec.lattice_id] = empty_content_lattice(
            width=32,
            height=32,
            z_level=spec.z_level,
            concept_prefix=spec.concept_prefix,
        )
        lats[spec.lattice_id]["prism_id"] = PRISM_VISUAL
        created.append(spec.lattice_id)
    if LATTICE_V1_LUM in lats and not block.get("active_lattice"):
        block["active_lattice"] = LATTICE_V1_LUM
    return created


def ensure_prism_visual_routes(state: dict) -> None:
    add_route(
        state,
        {"modality": "vis"},
        PRISM_VISUAL,
        lattice_hint=LATTICE_V1_LUM,
        priority=95,
    )
    add_route(
        state,
        {"modality": "image"},
        PRISM_VISUAL,
        lattice_hint=LATTICE_V1_LUM,
        priority=95,
    )


def ensure_prism_visual(state: dict, *, include_scene: bool = False) -> dict[str, Any]:
    """Mount prism_visual + LRGB lattices + router hints."""
    state = ensure_prisms(state)
    stack_path = str((REPO_ROOT / VIS_STACK).resolve())
    if PRISM_VISUAL not in prisms(state):
        spawn_prism(
            state,
            PRISM_VISUAL,
            kind=PRISM_KIND_CONTENT,
            stack=stack_path,
        )
    else:
        block = prism_block(state, PRISM_VISUAL)
        block.setdefault("kind", PRISM_KIND_CONTENT)
        if not block.get("stack"):
            block["stack"] = stack_path
    created = ensure_visual_lattices(state, include_scene=include_scene)
    ensure_prism_visual_routes(state)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "prism_id": PRISM_VISUAL,
        "lattice_ids": list(VISUAL_LATTICE_IDS),
        "created_lattices": created,
    }
