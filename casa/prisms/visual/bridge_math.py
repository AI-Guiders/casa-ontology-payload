#!/usr/bin/env python3
"""Emergent cross-prism bridges (ADR-0028 S3b) — no manifest oracle."""

from __future__ import annotations

from typing import Any

from casa.domain.prism_ids import PRISM_VISUAL
from casa.domain.prism_wire import prism_block
from casa.domain.visual_tract import LATTICE_V1_LUM, PREFIX_VIS_LUM
from casa.prisms.memory.f0_stack import decode_f0_lattice, strengthen_graph_edge
from casa.prisms.memory.memory_prisms import append_episode, memory_lattices, persist_content_lattices
from casa.prisms.memory.prism_hot_context import add_hot_edge
from casa.prisms.memory.stack import _place_token
from casa.prisms.shared.codec_grid import Grid
from casa.prisms.shared.lattice_names_v1 import (
    ALPHABET_RU,
    LEXICON_RU,
    SCHEMA_MATH,
    SYLLABLES_RU,
)
from casa.prisms.visual.bootstrap import ensure_prism_visual

DEFAULT_RELATION = "co_occurs"
AGENT_RELATION = "denotes"


def vis_frame_concept_id(frame_id: str) -> str:
    fid = str(frame_id or "").strip()
    if fid.startswith(PREFIX_VIS_LUM):
        return fid
    return f"{PREFIX_VIS_LUM}frame.{fid}"


def _edge_token(src: str, relation: str, dst: str) -> str:
    return f"E:{src}|{relation}|{dst}"


def bridge_exists_on_field(
    lattices: dict[str, dict],
    *,
    src: str,
    relation: str,
    dst: str,
) -> bool:
    tok = _edge_token(src, relation, dst)
    for lid in (LATTICE_V1_LUM, SCHEMA_MATH, ALPHABET_RU, LEXICON_RU, SYLLABLES_RU):
        lat = lattices.get(lid) or {}
        for cell in lat.get("cells") or []:
            if isinstance(cell, list) and tok in cell:
                return True
    return False


def math_concept_votes(lattices: dict[str, dict], math_cid: str, *, min_votes: int = 2) -> int:
    lat = lattices.get(SCHEMA_MATH) or {}
    if not lat.get("cells"):
        return 0
    from casa.prisms.memory.stack import decode_lattice

    dec = decode_lattice(lat, min_votes=1)
    for row in dec.get("concepts") or []:
        if str(row.get("concept_id") or "") == math_cid:
            return int(row.get("votes") or 0)
    tok = f"C:{math_cid}"
    votes = sum(cell.count(tok) for cell in lat.get("cells") or [] if isinstance(cell, list))
    return votes if votes >= min_votes else 0


def _strengthen_on_visual_lum(
    state: dict,
    *,
    src: str,
    relation: str,
    dst: str,
    copies: int,
) -> bool:
    ensure_prism_visual(state)
    block = prism_block(state, PRISM_VISUAL)
    lat = (block.get("lattices") or {}).get(LATTICE_V1_LUM)
    if not lat:
        return False
    g = Grid(
        width=int(lat["width"]),
        height=int(lat["height"]),
        cells=[list(row) for row in lat["cells"]],
    )
    edge = _edge_token(src, relation, dst)
    g = _place_token(g, edge, edge, copies=copies, radius=4)
    for cid in (src, dst):
        if cid.startswith(("vis.", "math.")):
            g = _place_token(g, f"C:{cid}", f"C:{cid}", copies=max(2, copies // 2), radius=3)
    lat["cells"] = g.cells
    persist_content_lattices(state, {LATTICE_V1_LUM: lat})
    return True


def mint_crosslink(
    state: dict,
    *,
    src: str,
    relation: str,
    dst: str,
    copies: int = 5,
    provenance: str = "emergent",
) -> dict[str, str] | None:
    """Mint cross-prism edge; vis↔math, vis↔grapheme, math/math on schema-math."""
    src, relation, dst = src.strip(), relation.strip(), dst.strip()
    if not (src and relation and dst):
        return None
    lats = memory_lattices(state)
    if bridge_exists_on_field(lats, src=src, relation=relation, dst=dst):
        return None
    on_vis = False
    on_math = False
    on_lex = False
    if src.startswith(PREFIX_VIS_LUM) or src.startswith("vis."):
        on_vis = _strengthen_on_visual_lum(state, src=src, relation=relation, dst=dst, copies=copies)
    if src.startswith("math.") or dst.startswith("math."):
        on_math = strengthen_graph_edge(lats, SCHEMA_MATH, src, relation, dst, copies=copies)
    from casa.prisms.memory.lexical_lattice_bootstrap import lattice_for_lex_concept

    for cid in (src, dst):
        lat_id = lattice_for_lex_concept(cid)
        if lat_id:
            on_lex = on_lex or strengthen_graph_edge(lats, lat_id, src, relation, dst, copies=copies)
    if not (on_vis or on_math or on_lex):
        return None
    add_hot_edge(state, src, relation, dst, salience=1.0, provenance=provenance)
    persist_content_lattices(state, lats)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "src": src,
        "relation": relation,
        "dst": dst,
        "edge": _edge_token(src, relation, dst),
        "on_visual": on_vis,
        "on_math": on_math,
        "on_lex": on_lex,
        "provenance": provenance,
    }


def reinforce_vis_math_bridge(
    state: dict,
    *,
    frame_id: str,
    math_cid: str,
    relation: str = DEFAULT_RELATION,
    copies: int = 8,
    provenance: str = "reinforce",
) -> dict[str, str] | None:
    """Add edge copies even when link exists (contrast / tie-break after co-occurrence)."""
    if not str(math_cid).startswith("math."):
        return None
    vis_cid = vis_frame_concept_id(frame_id)
    lats = memory_lattices(state)
    on_vis = _strengthen_on_visual_lum(
        state, src=vis_cid, relation=relation, dst=math_cid, copies=copies
    )
    on_math = strengthen_graph_edge(lats, SCHEMA_MATH, vis_cid, relation, math_cid, copies=copies)
    if not (on_vis or on_math):
        return None
    add_hot_edge(state, vis_cid, relation, math_cid, salience=1.0, provenance=provenance)
    persist_content_lattices(state, lats)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "src": vis_cid,
        "relation": relation,
        "dst": math_cid,
        "edge": _edge_token(vis_cid, relation, math_cid),
        "on_visual": on_vis,
        "on_math": on_math,
        "provenance": provenance,
    }


def mint_vis_math_bridge(
    state: dict,
    *,
    frame_id: str,
    specs: list[tuple[str, str]],
    copies: int = 5,
    provenance: str = "emergent",
) -> list[dict[str, str]]:
    vis_cid = vis_frame_concept_id(frame_id)
    minted: list[dict[str, str]] = []
    for relation, math_cid in specs:
        row = mint_crosslink(
            state,
            src=vis_cid,
            relation=relation,
            dst=math_cid,
            copies=copies,
            provenance=provenance,
        )
        if row:
            minted.append(row)
    return minted


def agent_promote_crosslink(
    state: dict,
    *,
    src: str,
    relation: str,
    dst: str,
    cue: str = "",
    scene: str = "",
    lattice_id: str = LATTICE_V1_LUM,
    copies: int = 5,
) -> dict[str, Any]:
    """Agent decides a cross-prism link → hippo episode + field mint on sleep/now."""
    row = mint_crosslink(
        state,
        src=src,
        relation=relation,
        dst=dst,
        copies=copies,
        provenance="agent_promote",
    )
    ep = append_episode(
        state,
        cue=(cue or f"link:{src}:{dst}")[:120],
        surface_attempt="",
        correct=dst[:120],
        lattice_id=lattice_id,
        concept_id=src if src.startswith(PREFIX_VIS_LUM) else None,
        scene=scene,
        links=[{"src": src, "relation": relation, "dst": dst}],
        structure_tag="self_promote",
        episode_source="wake",
    )
    return {"minted": row, "episode_id": ep.get("id") if ep else None}


def self_promote_vis_math_bridge(
    state: dict,
    *,
    frame_id: str,
    math_cid: str,
    relation: str = AGENT_RELATION,
    copies: int = 5,
    provenance: str = "self_verify",
) -> list[dict[str, str]]:
    if not str(math_cid).startswith("math."):
        return []
    return mint_vis_math_bridge(
        state,
        frame_id=frame_id,
        specs=[(relation, math_cid)],
        copies=copies,
        provenance=provenance,
    )


def _vis_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ep in episodes:
        if str(ep.get("lattice_id") or "") != LATTICE_V1_LUM:
            continue
        cid = str(ep.get("concept_id") or "")
        if cid.startswith(f"{PREFIX_VIS_LUM}frame."):
            out.append(ep)
    return out


def _math_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ep in episodes:
        if str(ep.get("lattice_id") or "") != SCHEMA_MATH:
            continue
        cid = str(ep.get("concept_id") or "")
        if cid.startswith("math."):
            out.append(ep)
    return out


def _agent_link_specs(ep: dict[str, Any]) -> list[tuple[str, str, str]]:
    if str(ep.get("structure_tag") or "") != "self_promote" and str(
        ep.get("correction_kind") or ""
    ) not in ("self_promote", "agent_bridge"):
        return []
    specs: list[tuple[str, str, str]] = []
    for raw in ep.get("links") or []:
        if not isinstance(raw, dict):
            continue
        src = str(raw.get("src") or "")
        dst = str(raw.get("dst") or "")
        rel = str(raw.get("relation") or raw.get("rel") or AGENT_RELATION)
        if src and dst:
            specs.append((src, rel, dst))
    return specs


def _schema_math_ready(lattices: dict[str, dict], episodes: list[dict[str, Any]]) -> bool:
    lat = lattices.get(SCHEMA_MATH) or {}
    if lat.get("cells"):
        return True
    if lat.get("_cells_in_ltm"):
        return True
    return bool(_math_episodes(episodes))


def extract_emergent_vis_math_bridges(
    lattices: dict[str, dict],
    episodes: list[dict[str, Any]],
    state: dict,
    *,
    copies: int = 4,
    min_math_votes: int = 2,
) -> list[dict[str, Any]]:
    """
    Sleep Extract (S3b): no manifest oracle.

    - Agent episodes with structure_tag=self_promote + links
    - Co-occurrence: visual + math episodes in the same sleep batch
    """
    if not _schema_math_ready(lattices, episodes):
        return []
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def emit(src: str, relation: str, dst: str, *, episode_id: str | None, kind: str) -> None:
        key = (src, relation, dst)
        if key in seen:
            return
        seen.add(key)
        row = mint_crosslink(
            state,
            src=src,
            relation=relation,
            dst=dst,
            copies=copies,
            provenance=kind,
        )
        if row:
            out.append(
                {
                    "episode_id": episode_id,
                    "kind": "emergent_crosslink",
                    "extract": row,
                }
            )

    for ep in episodes:
        for src, rel, dst in _agent_link_specs(ep):
            emit(src, rel, dst, episode_id=str(ep.get("id") or ""), kind="agent_self_promote")

    vis_eps = _vis_episodes(episodes)
    math_eps = _math_episodes(episodes)
    for vep in vis_eps:
        vis_cid = str(vep.get("concept_id") or "")
        frame_id = vis_cid[len(f"{PREFIX_VIS_LUM}frame.") :]
        for mep in math_eps:
            math_cid = str(mep.get("concept_id") or "")
            if math_concept_votes(lattices, math_cid, min_votes=min_math_votes) < min_math_votes:
                continue
            emit(
                vis_cid,
                DEFAULT_RELATION,
                math_cid,
                episode_id=str(vep.get("id") or ""),
                kind="sleep_co_occurs",
            )
            if len(seen) > 32:
                break

    return out


def predict_math_for_vis_cue(
    state: dict,
    cue: str,
    *,
    top_k: int = 5,
) -> list[tuple[str, int]]:
    """Rank math.* via emergent E: edges from vis cue."""
    ensure_prism_visual(state)
    lats = memory_lattices(state)
    lum = (prism_block(state, PRISM_VISUAL).get("lattices") or {}).get(LATTICE_V1_LUM) or {}
    if not lum.get("cells"):
        return []
    cue = str(cue or "").strip()
    vis_cid = vis_frame_concept_id(cue.removeprefix("vis:"))
    prefix = f"E:{vis_cid}|"
    scores: dict[str, int] = {}
    for cell in lum.get("cells") or []:
        if not isinstance(cell, list):
            continue
        for tok in cell:
            if not isinstance(tok, str) or not tok.startswith(prefix):
                continue
            parts = tok.split("|", 2)
            if len(parts) == 3 and parts[2].startswith("math."):
                scores[parts[2]] = scores.get(parts[2], 0) + 1
    math_lat = lats.get(SCHEMA_MATH) or {}
    if math_lat.get("cells"):
        dec = decode_f0_lattice(math_lat)
        for es in dec.get("edges") or []:
            if isinstance(es, str) and es.startswith(prefix):
                parts = es.split("|", 2)
                if len(parts) == 3 and parts[2].startswith("math."):
                    scores[parts[2]] = scores.get(parts[2], 0) + 2
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:top_k]
