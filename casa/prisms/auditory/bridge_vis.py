#!/usr/bin/env python3
"""Emergent aud↔vis bridges from co-occurring listen episodes (wire-gap W1)."""

from __future__ import annotations

from typing import Any

from casa.domain.auditory_tract import LATTICE_AUDIO_SPECTRUM
from casa.domain.prism_ids import PRISM_AUDITORY, PRISM_VISUAL
from casa.domain.prism_wire import prism_block
from casa.domain.visual_tract import LATTICE_V1_LUM, PREFIX_VIS_LUM
from casa.prisms.auditory.bootstrap import ensure_prism_auditory
from casa.prisms.memory.f0_stack import strengthen_graph_edge
from casa.prisms.memory.memory_prisms import memory_lattices, persist_content_lattices
from casa.prisms.memory.prism_hot_context import add_hot_edge
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.bridge_math import (
    DEFAULT_RELATION,
    _edge_token,
    _strengthen_on_visual_lum,
    bridge_exists_on_field,
)

_AUD_PREFIX = "aud.window."
_MAX_PAIRS = 48


def _aud_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ep in episodes:
        if str(ep.get("lattice_id") or "") != LATTICE_AUDIO_SPECTRUM:
            continue
        cid = str(ep.get("concept_id") or "")
        if cid.startswith(_AUD_PREFIX):
            out.append(ep)
    return out


def _vis_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ep in episodes:
        if str(ep.get("lattice_id") or "") != LATTICE_V1_LUM:
            continue
        cid = str(ep.get("concept_id") or "")
        if cid.startswith(f"{PREFIX_VIS_LUM}frame."):
            out.append(ep)
    return out


def _same_listen_scene(aep: dict[str, Any], vep: dict[str, Any]) -> bool:
    sa = str(aep.get("scene") or "").strip()
    sb = str(vep.get("scene") or "").strip()
    return bool(sa and sb and sa == sb)


def bind_av_coactive_on_tick(state: dict, *, copies: int = 2) -> dict[str, Any] | None:
    """Life tick: mint aud↔vis co_occurs when joint percept is co-active (before sleep)."""
    block = state.get("_perceptual_turn")
    if not isinstance(block, dict) or not block.get("coactive"):
        return None
    wid = str(block.get("aud_window_id") or "").strip()
    fid = str(block.get("vis_frame_id") or "").strip()
    if not (wid and fid):
        return None
    from casa.prisms.visual.bridge_math import vis_frame_concept_id

    aud_cid = f"aud.window.{wid}"
    vis_cid = vis_frame_concept_id(fid)
    row = mint_aud_vis_bridge(
        state,
        aud_cid=aud_cid,
        vis_cid=vis_cid,
        copies=copies,
        provenance="life_tick_coactive",
    )
    if row:
        return {
            "bound": True,
            "aud_concept_id": aud_cid,
            "vis_concept_id": vis_cid,
            "extract": row,
        }
    lats = memory_lattices(state)
    if bridge_exists_on_field(lats, src=aud_cid, relation=DEFAULT_RELATION, dst=vis_cid, state=state):
        return {
            "bound": False,
            "already": True,
            "aud_concept_id": aud_cid,
            "vis_concept_id": vis_cid,
        }
    return None


def mint_aud_vis_bridge(
    state: dict,
    *,
    aud_cid: str,
    vis_cid: str,
    relation: str = DEFAULT_RELATION,
    copies: int = 4,
    provenance: str = "sleep_co_occurs",
) -> dict[str, str] | None:
    """Crosslink auditory window concept ↔ visual frame concept."""
    aud_cid = aud_cid.strip()
    vis_cid = vis_cid.strip()
    if not (aud_cid.startswith(_AUD_PREFIX) and vis_cid.startswith(PREFIX_VIS_LUM)):
        return None
    lats = memory_lattices(state)
    if bridge_exists_on_field(lats, src=aud_cid, relation=relation, dst=vis_cid, state=state):
        return None
    ensure_prism_auditory(state)
    ensure_prism_visual(state)
    on_vis = _strengthen_on_visual_lum(state, src=vis_cid, relation=relation, dst=aud_cid, copies=copies)
    on_aud = strengthen_graph_edge(lats, LATTICE_AUDIO_SPECTRUM, aud_cid, relation, vis_cid, copies=copies)
    if not (on_vis or on_aud):
        return None
    add_hot_edge(state, aud_cid, relation, vis_cid, salience=1.0, provenance=provenance)
    persist_content_lattices(state, lats)
    aud_lat = (prism_block(state, PRISM_AUDITORY).get("lattices") or {}).get(LATTICE_AUDIO_SPECTRUM)
    if aud_lat:
        persist_content_lattices(state, {LATTICE_AUDIO_SPECTRUM: aud_lat})
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "src": aud_cid,
        "relation": relation,
        "dst": vis_cid,
        "edge": _edge_token(aud_cid, relation, vis_cid),
        "on_visual": on_vis,
        "on_auditory": on_aud,
        "provenance": provenance,
    }


def extract_emergent_aud_vis_bridges(
    lattices: dict[str, dict],
    episodes: list[dict[str, Any]],
    state: dict,
    *,
    copies: int = 4,
) -> list[dict[str, Any]]:
    """Sleep extract: co-occurring aud.window.* + vis frame on shared scene_id."""
    _ = lattices
    aud_eps = _aud_episodes(episodes)
    vis_eps = _vis_episodes(episodes)
    if not aud_eps or not vis_eps:
        return []

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for aep in aud_eps:
        aud_cid = str(aep.get("concept_id") or "")
        for vep in vis_eps:
            if not _same_listen_scene(aep, vep):
                continue
            vis_cid = str(vep.get("concept_id") or "")
            key = (aud_cid, vis_cid)
            if key in seen:
                continue
            seen.add(key)
            row = mint_aud_vis_bridge(
                state,
                aud_cid=aud_cid,
                vis_cid=vis_cid,
                copies=copies,
                provenance="sleep_co_occurs",
            )
            if row:
                out.append(
                    {
                        "episode_id": str(aep.get("id") or vep.get("id") or ""),
                        "kind": "emergent_aud_vis",
                        "aud_concept_id": aud_cid,
                        "vis_concept_id": vis_cid,
                        "extract": row,
                    }
                )
            if len(seen) >= _MAX_PAIRS:
                return out
    return out
