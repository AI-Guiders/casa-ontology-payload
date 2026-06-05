#!/usr/bin/env python3
"""predict(..., modality=vis) — decode prism_visual LRGB + vis_refs."""

from __future__ import annotations

from typing import Any

from casa.prisms.visual.bridge_math import frame_id_from_vis_cue
from casa.domain.prism_ids import PRISM_VISUAL
from casa.domain.visual_tract import LATTICE_V1_LUM, VISUAL_LATTICE_IDS
from casa.prisms.memory.memory_prisms import content_prism_lattices, ensure_prisms
from casa.prisms.memory.stack import decode_lattice
from casa.prisms.visual.bootstrap import VIS_OBJECT, ensure_prism_visual


def _resolve_cue_to_concept_id(state: dict, cue: str) -> str:
    cue = (cue or "").strip()
    if not cue:
        return ""
    if cue.startswith("vis."):
        return cue
    refs = state.get("vis_refs") if isinstance(state.get("vis_refs"), dict) else {}
    if cue in refs:
        return str(refs[cue])
    for suffix in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
        if cue.endswith(suffix) and cue in refs:
            return str(refs[cue])
    return ""


def _rank_lattice_tokens(lat: dict, *, prefix: str = "") -> list[tuple[str, int]]:
    dec = decode_lattice(lat, min_votes=1)
    ranked: list[tuple[str, int]] = []
    for c in dec.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if prefix and not cid.startswith(prefix):
            continue
        ranked.append((cid, int(c.get("votes") or 0)))
    for cell in lat.get("cells") or []:
        if not isinstance(cell, list):
            continue
        for tok in cell:
            if not isinstance(tok, str):
                continue
            if tok.startswith("V:") and (not prefix or "vis." in tok or tok.startswith("V:vis.")):
                ranked.append((tok, 1))
    ranked.sort(key=lambda x: (-x[1], x[0]))
    return ranked


def predict_vis(state: dict, cue: str, *, top_k: int = 8) -> dict[str, Any]:
    state = ensure_prisms(state)
    ensure_prism_visual(state)
    lats = content_prism_lattices(state, PRISM_VISUAL)
    lum = lats.get(LATTICE_V1_LUM) or lats.get(VIS_OBJECT)
    if not lum:
        return {
            "schema_version": 1,
            "modality": "vis",
            "cue": cue,
            "hypothesis": None,
            "confidence": 0.0,
            "digest": {"reason": "no_V1_lum"},
        }
    target = _resolve_cue_to_concept_id(state, cue) or cue
    ranked = _rank_lattice_tokens(lum, prefix="vis.")
    frame_cue = frame_id_from_vis_cue(cue)
    if frame_cue:
        ranked = [(cid, v + (30 if frame_cue in cid else 0)) for cid, v in ranked]
        ranked.sort(key=lambda x: (-x[1], x[0]))
    if target.startswith("vis."):
        ranked = [(cid, v + (50 if cid == target else 0)) for cid, v in ranked]
        ranked.sort(key=lambda x: (-x[1], x[0]))
    if not ranked:
        for lid in VISUAL_LATTICE_IDS:
            lat = lats.get(lid)
            if lat:
                ranked.extend(_rank_lattice_tokens(lat))
        ranked.sort(key=lambda x: (-x[1], x[0]))
    top = ranked[0][0] if ranked else (target if target.startswith("vis.") else None)
    return {
        "schema_version": 1,
        "modality": "vis",
        "cue": cue,
        "hypothesis": top,
        "hypothesis_tokens": [c for c, _ in ranked[:top_k]],
        "confidence": min(1.0, (ranked[0][1] / 10.0) if ranked else 0.0),
        "digest": {"concepts": len(ranked), "lattice_id": LATTICE_V1_LUM},
        "ranked": ranked[:top_k],
        "provenance": {"engine": "vis_lrgb_decode"},
    }
