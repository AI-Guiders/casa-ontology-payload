#!/usr/bin/env python3
"""Spiral learning progressions — L0→L4 ring per concept family (ADR-0030)."""

from __future__ import annotations

from typing import Any

from casa.domain.knowledge_tracing import due_for_retrieval, p_known, trace_row

# ring_id → next goal template
_LITERACY_RINGS: tuple[tuple[str, str, str], ...] = (
    ("syllable.", "L0_syllable", "goal.read.syllable"),
    ("lang.word.", "L1_word", "goal.read.word"),
    ("lang.meta.", "L2_meta", "goal.lang.meta"),
    ("lang.event.", "L3_event", "goal.read.phrase"),
    ("goal.write.", "L4_j0", "goal.write.j0"),
)


def _rings_for(concept_id: str) -> tuple[str, str] | None:
    cid = str(concept_id or "")
    for prefix, ring, goal in _LITERACY_RINGS:
        if cid.startswith(prefix):
            return ring, goal
    return None


def _progression(state: dict) -> dict[str, str]:
    raw = state.setdefault("progression_ring", {})
    return raw if isinstance(raw, dict) else {}


def current_ring(state: dict, concept_id: str) -> str | None:
    return _progression(state).get(str(concept_id or "").strip())


def set_ring(state: dict, concept_id: str, ring_id: str) -> None:
    cid = str(concept_id or "").strip()
    if cid:
        prog = _progression(state)
        prog[cid] = ring_id
        state["progression_ring"] = prog


def maybe_progression_goal(
    state: dict,
    *,
    tick: int,
    mastery_threshold: float = 0.75,
) -> dict[str, Any] | None:
    """When p_known high — suggest next ring goal (spiral)."""
    best: tuple[float, str, str, str] | None = None
    for cid, row in (state.get("knowledge_trace") or {}).items():
        if not isinstance(row, dict) or str(cid).startswith("gate:"):
            continue
        prob = float(row.get("p_known") or p_known(row))
        if prob < mastery_threshold:
            continue
        if not due_for_retrieval(state, cid, tick=tick):
            continue
        mapped = _rings_for(cid)
        if mapped is None:
            continue
        ring, goal = mapped
        if best is None or prob > best[0]:
            best = (prob, cid, ring, goal)

    if best is None:
        return None
    prob, cid, ring, goal = best
    set_ring(state, cid, ring)
    return {
        "kind": "progression_ring",
        "concept_id": cid,
        "ring": ring,
        "goal_id": goal,
        "p_known": prob,
    }


def apply_progression_goal(wm: Any, proposal: dict[str, Any] | None) -> None:
    if not proposal or wm is None:
        return
    gid = str(proposal.get("goal_id") or "").strip()
    if gid and not getattr(wm, "goal_id", ""):
        wm.goal_id = gid
        wm.goal = f"spiral:{proposal.get('concept_id')}"
