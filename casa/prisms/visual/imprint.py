#!/usr/bin/env python3
"""Encode RGB frame → LRGB lattices; hippo episode (no bridge oracle)."""

from __future__ import annotations

from typing import Any

from casa.domain.prism_ids import PRISM_VISUAL
from casa.domain.prism_wire import prism_block
from casa.domain.visual_imprint import CellPlacement, VisualImprintPlan
from casa.domain.visual_tract import LATTICE_V1_LUM
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, persist_content_lattices
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.bridge_math import vis_frame_concept_id
from casa.sensory.codecs.retinal_lrgb import encode_retinal_lrgb
from casa.sensory.rgb_frame import RgbFrame


def _apply_placements(
    lat: dict,
    placements: tuple[CellPlacement, ...],
    *,
    width: int,
    height: int,
) -> int:
    cells = lat.get("cells")
    n = width * height
    if not isinstance(cells, list) or len(cells) != n:
        cells = [[] for _ in range(n)]
        lat["cells"] = cells
    count = 0
    for p in placements:
        if p.x < 0 or p.y < 0 or p.x >= width or p.y >= height:
            continue
        i = p.y * width + p.x
        bucket = cells[i]
        if p.token not in bucket:
            bucket.append(p.token)
        count += 1
    return count


def apply_visual_imprint(state: dict, plan: VisualImprintPlan) -> dict[str, Any]:
    ensure_prism_visual(state)
    block = prism_block(state, PRISM_VISUAL)
    lats = block.setdefault("lattices", {})
    per_lattice: dict[str, int] = {}
    for lid, placements in plan.placements_by_lattice.items():
        lat = lats.get(lid)
        if not lat:
            continue
        w = int(lat.get("width") or plan.grid_size)
        h = int(lat.get("height") or plan.grid_size)
        per_lattice[lid] = _apply_placements(lat, placements, width=w, height=h)
    persist_content_lattices(state, {lid: lats[lid] for lid in per_lattice if lid in lats})
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "frame_id": plan.frame_id,
        "scene_hash": plan.scene_hash[:16],
        "codec_id": plan.codec_id,
        "placements": per_lattice,
    }


def imprint_visual_frame(
    state: dict,
    frame: RgbFrame,
    *,
    frame_id: str | None = None,
    scene_label: str = "room",
    record_episode: bool = True,
) -> dict[str, Any]:
    """Encode RGB frame → LRGB lattices; optional hippo episode."""
    state = ensure_prisms(state)
    plan = encode_retinal_lrgb(frame, frame_id=frame_id)
    applied = apply_visual_imprint(state, plan)
    ep = None
    if record_episode:
        vis_cid = vis_frame_concept_id(plan.frame_id)
        links = [
            {"src": vis_cid, "relation": "imprint", "dst": lid}
            for lid in plan.lattice_ids
        ]
        ep = append_episode(
            state,
            cue=f"vis:{plan.frame_id}",
            surface_attempt="",
            correct=plan.scene_hash[:48],
            lattice_id=LATTICE_V1_LUM,
            concept_id=vis_cid,
            scene=f"{scene_label}:{plan.frame_id}",
            links=links,
            episode_source="ingest",
        )
    return {**applied, "episode_id": ep.get("id") if ep else None}
