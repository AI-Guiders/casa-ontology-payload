"""Working Memory Prism — bind-time focus and retrieval blocks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from casa.domain.dialogue_turn import recent_dialogue

from .graph import place_wm_edge
from .lattice import infer_topic_slug, spawn_wm_lattice, wm_root
from .scoring import partner_callback_hit
from .model import tokenize


def dialogue_focus_concepts(store_dir: Path, *, limit: int = 6) -> list[str]:
    focus: list[str] = []
    for turn in recent_dialogue(store_dir, limit=12):
        for skill in re.findall(r"skill\.[\w.\-]+", turn.text):
            if skill not in focus:
                focus.append(skill)
        prov = turn.provenance if isinstance(turn.provenance, dict) else {}
        for cid in prov.get("prop_ids") or []:
            s = str(cid)
            if s and s not in focus:
                focus.append(s)
        for cid in prov.get("concept_hints") or []:
            s = str(cid)
            if s and s not in focus:
                focus.append(s)
        for cid in prov.get("wm_nodes") or []:
            s = str(cid)
            if s and s not in focus:
                focus.append(s)
        if len(focus) >= limit:
            break
    return focus[:limit]


def fpn_co_place_hints(wm: Any) -> list[str]:
    """FPN WorkingMemory last_concepts → WM node placement hints."""
    hints: list[str] = []
    for cid in getattr(wm, "last_concepts", []) or []:
        s = str(cid).strip()
        if s and s not in hints:
            hints.append(s)
    goal = str(getattr(wm, "goal", "") or "")
    for token in re.findall(r"[\w.\-]+", goal):
        if "." in token and token not in hints:
            hints.append(token)
    return hints[:8]


def wm_bind_focus_concepts(
    state: dict,
    focus_concepts: list[str],
    *,
    tick: int,
    overloaded: bool = False,
    surprise_before: int | None = None,
    surprise_after: int | None = None,
    fpn_hints: list[str] | None = None,
) -> dict[str, Any]:
    if overloaded:
        return {"placed_nodes": 0, "placed_edges": [], "skipped": "overload_freeze"}
    merged: list[str] = []
    for cid in list(focus_concepts) + list(fpn_hints or []):
        if cid and cid not in merged:
            merged.append(cid)
    if len(merged) < 2:
        return {"placed_nodes": len(merged), "placed_edges": [], "skipped": "short_focus"}

    topic_slug = infer_topic_slug(merged)
    lid = spawn_wm_lattice(state, tick=tick, topic_slug=topic_slug)
    if not lid:
        return {"placed_nodes": 0, "placed_edges": [], "skipped": "spawn_blocked"}

    placed_edges: list[str] = []
    for i, a in enumerate(merged[:6]):
        for b in merged[i + 1 : 6]:
            row = place_wm_edge(
                state,
                a,
                b,
                tick=tick,
                lattice_id=lid,
                surprise_before=surprise_before,
                surprise_after=surprise_after,
            )
            if row:
                placed_edges.append(str(row["edge_id"]))
    return {
        "lattice_id": lid,
        "placed_nodes": len(merged[:6]),
        "placed_edges": placed_edges,
        "focus": merged[:6],
        "topic_slug": topic_slug,
    }


def wm_blocks_for_bind(state: dict, query: str, *, k: int = 3) -> list[dict[str, Any]]:
    qt = tokenize(query)
    ranked: list[tuple[float, str, dict[str, Any], str]] = []
    for lid, meta in wm_root(state).items():
        for eid, edge in (meta.get("edges") or {}).items():
            sigma = float(edge.get("score") or 0.0)
            fc = str(edge.get("from_concept") or "")
            tc = str(edge.get("to_concept") or "")
            boost = 0.0
            for concept in (fc, tc):
                tail = concept.rsplit(".", 1)[-1].lower()
                if tail and tail in qt:
                    boost += 0.12
            if partner_callback_hit(query, edge):
                boost += 0.18
            ranked.append((sigma + boost, eid, edge, lid))
    ranked.sort(key=lambda row: row[0], reverse=True)
    blocks: list[dict[str, Any]] = []
    for score, eid, edge, lid in ranked[:k]:
        fc = str(edge.get("from_concept") or "")
        tc = str(edge.get("to_concept") or "")
        tier = str(edge.get("tier") or "scratch")
        blocks.append(
            {
                "concept_id": eid,
                "text": f"WM-связь [{tier}] σ={edge.get('score')}: {fc} ↔ {tc}.",
                "section": "wm_edge",
                "doc_path": "wm_prism",
                "score": int(round(float(score) * 40)),
                "source": "wm_prism",
                "slots": {
                    "from": fc,
                    "to": tc,
                    "sigma": edge.get("score"),
                    "tier": tier,
                    "lattice_id": lid,
                },
            }
        )
    return blocks
