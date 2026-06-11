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

_DIALOGUE_COPLACE = ("ru.dialog.", "lang.word.")
_MATH_COPLACE = ("math.",)
_PROP_COPLACE = ("ru.prop.", "passage.")
_SOCIAL_FOCUS_PREFIXES = _DIALOGUE_COPLACE + ("subject.dialog.",)


def _co_place_pair_allowed(a: str, b: str) -> bool:
    """Scratch edges only within one co-placement family — no math↔lang cliques."""
    groups = (_DIALOGUE_COPLACE, _MATH_COPLACE, _PROP_COPLACE)
    for prefixes in groups:
        if any(a.startswith(p) for p in prefixes) and any(b.startswith(p) for p in prefixes):
            return True
    if a.startswith("agent.world.") and b.startswith("agent.world."):
        return True
    return False


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
    intent: str = "general",
) -> dict[str, Any]:
    if overloaded:
        return {"placed_nodes": 0, "placed_edges": [], "skipped": "overload_freeze"}
    merged: list[str] = []
    for cid in list(focus_concepts) + list(fpn_hints or []):
        if cid and cid not in merged:
            merged.append(cid)
    if intent == "social":
        merged = [c for c in merged if c.startswith(_SOCIAL_FOCUS_PREFIXES)]
    if len(merged) < 2:
        return {"placed_nodes": len(merged), "placed_edges": [], "skipped": "short_focus"}

    topic_slug = infer_topic_slug(merged)
    lid = spawn_wm_lattice(state, tick=tick, topic_slug=topic_slug)
    if not lid:
        return {"placed_nodes": 0, "placed_edges": [], "skipped": "spawn_blocked"}

    placed_edges: list[str] = []
    for i, a in enumerate(merged[:6]):
        for b in merged[i + 1 : 6]:
            if not _co_place_pair_allowed(a, b):
                continue
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


def social_wm_block_eligible(block: dict[str, Any], query: str) -> bool:
    """Partner social turn may use WM only on explicit callback / token overlap."""
    if block.get("source") != "wm_prism":
        return False
    slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
    fc = str(slots.get("from") or "")
    tc = str(slots.get("to") or "")
    if not fc or not tc or not _co_place_pair_allowed(fc, tc):
        return False
    edge = {"from_concept": fc, "to_concept": tc}
    if partner_callback_hit(query, edge):
        return True
    qt = tokenize(query)
    for concept in (fc, tc):
        tail = concept.rsplit(".", 1)[-1].lower()
        if tail and tail in qt:
            return True
    return False


def wm_blocks_for_bind(
    state: dict, query: str, *, k: int = 3, intent: str = "general"
) -> list[dict[str, Any]]:
    qt = tokenize(query)
    ranked: list[tuple[float, str, dict[str, Any], str, float]] = []
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
            if intent == "social" and boost <= 0.0:
                continue
            if not _co_place_pair_allowed(fc, tc):
                continue
            ranked.append((sigma + boost, eid, edge, lid, boost))
    ranked.sort(key=lambda row: row[0], reverse=True)
    blocks: list[dict[str, Any]] = []
    for score, eid, edge, lid, _boost in ranked[:k]:
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
