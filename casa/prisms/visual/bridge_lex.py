#!/usr/bin/env python3
"""Emergent vis↔lexical bridges (grapheme, syllable, whole word)."""

from __future__ import annotations

from typing import Any

from casa.domain.prism_ids import PRISM_VISUAL
from casa.domain.prism_wire import prism_block
from casa.domain.visual_tract import LATTICE_V1_LUM, PREFIX_VIS_LUM
from casa.prisms.memory.f0_stack import decode_f0_lattice
from casa.prisms.memory.memory_prisms import memory_lattices
from casa.prisms.memory.lexical_lattice_bootstrap import lattice_for_lex_concept
from casa.prisms.shared.lattice_names_v1 import (
    ALPHABET_EN,
    ALPHABET_RU,
    LEXICON_EN,
    LEXICON_RU,
    SYLLABLES_EN,
    SYLLABLES_RU,
)
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id, lex_concept_id_variants
from casa.prisms.memory.f0_stack import strengthen_graph_edge
from casa.prisms.memory.memory_prisms import persist_content_lattices
from casa.prisms.memory.prism_hot_context import add_hot_edge
from casa.prisms.visual.bridge_math import (
    DEFAULT_RELATION,
    _edge_token,
    _strengthen_on_visual_lum,
    bridge_exists_on_field,
    frame_id_from_vis_cue,
    mint_crosslink,
    vis_frame_concept_id,
)

_LEX_DST_PREFIXES = ("grapheme.", "lang.word.", "lang.meta.", "syllable.")


def lex_concept_votes(lattices: dict[str, dict], lex_cid: str, *, min_votes: int = 2) -> int:
    lat_id = lattice_for_lex_concept(lex_cid)
    if not lat_id:
        return 0
    lat = lattices.get(lat_id) or {}
    if not lat.get("cells"):
        return 0
    from casa.prisms.memory.stack import decode_lattice

    variants = lex_concept_id_variants(lex_cid)
    dec = decode_lattice(lat, min_votes=1)
    best = 0
    for row in dec.get("concepts") or []:
        if str(row.get("concept_id") or "") in variants:
            best = max(best, int(row.get("votes") or 0))
    for vid in variants:
        tok = f"C:{vid}"
        votes = sum(cell.count(tok) for cell in lat.get("cells") or [] if isinstance(cell, list))
        best = max(best, votes)
    return best if best >= min_votes else 0


def _lex_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lat_ok = {
        ALPHABET_RU,
        ALPHABET_EN,
        LEXICON_RU,
        LEXICON_EN,
        SYLLABLES_RU,
        SYLLABLES_EN,
    }
    out: list[dict[str, Any]] = []
    for ep in episodes:
        if str(ep.get("lattice_id") or "") not in lat_ok:
            continue
        cid = str(ep.get("concept_id") or "")
        if cid.startswith(_LEX_DST_PREFIXES):
            out.append(ep)
    return out


def _vis_lex_episode_pair(vep: dict[str, Any], lep: dict[str, Any]) -> bool:
    """Co-occur only when same scene or vis cue matches lex concept slug."""
    vs = str(vep.get("scene") or "").strip()
    ls = str(lep.get("scene") or "").strip()
    if vs and ls and vs == ls:
        return True
    cue = str(vep.get("cue") or "")
    lex_cid = str(lep.get("concept_id") or "").lower()
    if not cue.startswith("vis:") or not lex_cid:
        return False
    frame_id = cue[4:].lower()
    skip = frozenset({"word", "sans", "phrase", "probe", "syllable", "frame", "vis"})
    for token in frame_id.replace("phrase-probe-", "").replace("-sans", "").split("-"):
        if token in skip or len(token) < 2:
            continue
        if token in lex_cid:
            return True
    return False


def _lexical_ready(lattices: dict[str, dict], episodes: list[dict[str, Any]]) -> bool:
    for lat_id in (ALPHABET_RU, LEXICON_RU, SYLLABLES_RU, ALPHABET_EN, LEXICON_EN, SYLLABLES_EN):
        lat = lattices.get(lat_id) or {}
        if lat.get("cells") or lat.get("_cells_in_ltm"):
            return True
    return bool(_lex_episodes(episodes))


def extract_emergent_vis_lex_bridges(
    lattices: dict[str, dict],
    episodes: list[dict[str, Any]],
    state: dict,
    *,
    copies: int = 4,
    min_lex_votes: int = 2,
) -> list[dict[str, Any]]:
    if not _lexical_ready(lattices, episodes):
        return []
    from casa.prisms.visual.bridge_math import _agent_link_specs

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
                    "kind": "emergent_crosslink_lex",
                    "extract": row,
                }
            )

    for ep in episodes:
        for src, rel, dst in _agent_link_specs(ep):
            if dst.startswith(_LEX_DST_PREFIXES):
                emit(src, rel, dst, episode_id=str(ep.get("id") or ""), kind="agent_self_promote")

    vis_eps = [
        ep
        for ep in episodes
        if str(ep.get("lattice_id") or "") == LATTICE_V1_LUM
        and str(ep.get("concept_id") or "").startswith(f"{PREFIX_VIS_LUM}frame.")
    ]
    lex_eps = _lex_episodes(episodes)
    for vep in vis_eps:
        vis_cid = str(vep.get("concept_id") or "")
        for lep in lex_eps:
            if not _vis_lex_episode_pair(vep, lep):
                continue
            lex_cid = str(lep.get("concept_id") or "")
            if lex_concept_votes(lattices, lex_cid, min_votes=min_lex_votes) < min_lex_votes:
                continue
            emit(
                vis_cid,
                DEFAULT_RELATION,
                lex_cid,
                episode_id=str(vep.get("id") or ""),
                kind="sleep_co_occurs_lex",
            )
            if len(seen) > 128:
                break

    return out


def reinforce_vis_lex_bridge(
    state: dict,
    *,
    frame_id: str,
    lex_cid: str,
    relation: str = DEFAULT_RELATION,
    copies: int = 8,
    provenance: str = "reinforce",
) -> dict[str, str] | None:
    """Add vis↔lex edge copies even when link exists (lab tie-break)."""
    lex_cid = canonical_lex_concept_id(str(lex_cid).strip())
    if not lex_cid.startswith(_LEX_DST_PREFIXES):
        return None
    vis_cid = vis_frame_concept_id(frame_id)
    lats = memory_lattices(state)
    on_vis = _strengthen_on_visual_lum(
        state, src=vis_cid, relation=relation, dst=lex_cid, copies=copies
    )
    lat_id = lattice_for_lex_concept(lex_cid)
    on_lex = False
    if lat_id:
        on_lex = strengthen_graph_edge(lats, lat_id, vis_cid, relation, lex_cid, copies=copies)
    if not (on_vis or on_lex):
        return None
    add_hot_edge(state, vis_cid, relation, lex_cid, salience=1.0, provenance=provenance)
    persist_content_lattices(state, lats)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "src": vis_cid,
        "relation": relation,
        "dst": lex_cid,
        "edge": _edge_token(vis_cid, relation, lex_cid),
        "on_visual": on_vis,
        "on_lex": on_lex,
        "provenance": provenance,
    }


def predict_lex_for_vis_cue(
    state: dict,
    cue: str,
    *,
    top_k: int = 5,
) -> list[tuple[str, int]]:
    ensure_prism_visual(state)
    lats = memory_lattices(state)
    lum = (prism_block(state, PRISM_VISUAL).get("lattices") or {}).get(LATTICE_V1_LUM) or {}
    if not lum.get("cells"):
        return []
    vis_cid = vis_frame_concept_id(frame_id_from_vis_cue(cue))
    prefix = f"E:{vis_cid}|"
    scores: dict[str, int] = {}

    def bump(dst: str, n: int) -> None:
        if dst.startswith(_LEX_DST_PREFIXES):
            canon = canonical_lex_concept_id(dst)
            scores[canon] = scores.get(canon, 0) + n

    for cell in lum.get("cells") or []:
        if not isinstance(cell, list):
            continue
        for tok in cell:
            if not isinstance(tok, str) or not tok.startswith(prefix):
                continue
            parts = tok.split("|", 2)
            if len(parts) == 3:
                bump(parts[2], 1)
    for lat_id in (ALPHABET_RU, LEXICON_RU, SYLLABLES_RU, ALPHABET_EN, LEXICON_EN, SYLLABLES_EN):
        lat = lats.get(lat_id) or {}
        if not lat.get("cells"):
            continue
        dec = decode_f0_lattice(lat)
        for es in dec.get("edges") or []:
            if isinstance(es, str) and es.startswith(prefix):
                parts = es.split("|", 2)
                if len(parts) == 3:
                    bump(parts[2], 2)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:top_k]
