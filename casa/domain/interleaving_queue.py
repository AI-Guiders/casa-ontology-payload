#!/usr/bin/env python3
"""Interleaving on wake — mixed tract queue (ADR-0034 C7)."""

from __future__ import annotations

from typing import Any

# tract_id → default autonomous goal when no explicit WM goal
_TRACT_GOALS: tuple[tuple[str, str, str], ...] = (
    ("literacy", "goal.read.phrase", "phrase:pilot"),
    ("math", "goal.learn.math", "math:schema"),
    ("meta", "goal.rehearse.meta", "meta:closed_class"),
)


def _queue_state(state: dict) -> dict[str, Any]:
    raw = state.setdefault("interleave_queue", {})
    if not isinstance(raw, dict):
        raw = {}
        state["interleave_queue"] = raw
    if "tracts" not in raw:
        raw["tracts"] = [t[0] for t in _TRACT_GOALS]
    if "cursor" not in raw:
        raw["cursor"] = 0
    return raw


def rotate_tract(state: dict, *, tick: int) -> str:
    q = _queue_state(state)
    tracts = [str(t) for t in (q.get("tracts") or []) if t]
    if not tracts:
        return "literacy"
    cursor = int(q.get("cursor") or 0)
    if tick > 0 and tick % 3 == 0:
        cursor = (cursor + 1) % len(tracts)
        q["cursor"] = cursor
        state["interleave_queue"] = q
    return tracts[cursor % len(tracts)]


def maybe_interleave_goal(state: dict, *, tick: int, wm_goal_id: str = "") -> dict[str, Any] | None:
    """Plan candidate when WM has no goal — mixed literacy/math/meta."""
    if wm_goal_id:
        return None
    tract = rotate_tract(state, tick=tick)
    for tid, goal_id, label in _TRACT_GOALS:
        if tid == tract:
            return {
                "goal_id": goal_id,
                "goal": label,
                "tract": tract,
                "kind": "interleave",
            }
    return None
