#!/usr/bin/env python3
"""Cognitive load governor — defer low-priority goals when WM overloaded (ADR-0036)."""

from __future__ import annotations

from typing import Any

from casa.domain.hypothesis_queue import open_hypothesis_count
from casa.domain.prism_wire import prism_hippo
from casa.prisms.control.fpn_state import WorkingMemory

DEFAULT_LOAD_THRESHOLD = 4
HIGH_PRIORITY_MIN = 80


def assess_cognitive_load(
    state: dict,
    wm: WorkingMemory | None,
) -> dict[str, Any]:
    wm = wm or WorkingMemory()
    hippo_pending = sum(
        1 for e in prism_hippo(state).get("episodes") or [] if not e.get("consolidated")
    )
    plan_depth = len(wm.plan_steps)
    step_active = 1 if wm.step_capability else 0
    hypotheses = open_hypothesis_count(state)
    competing = 1 if wm.goal_id else 0

    load = hypotheses + plan_depth + min(hippo_pending, 3) + step_active + competing
    overloaded = load >= DEFAULT_LOAD_THRESHOLD

    rep = {
        "load": load,
        "threshold": DEFAULT_LOAD_THRESHOLD,
        "overloaded": overloaded,
        "components": {
            "open_hypotheses": hypotheses,
            "plan_steps": plan_depth,
            "hippo_pending": hippo_pending,
            "step_active": step_active,
            "has_goal": bool(competing),
        },
        "policy": "high_priority_only" if overloaded else "normal",
    }
    state.setdefault("sn", {})["cognitive_load"] = rep
    return rep


def allows_candidate(priority: int, load_rep: dict[str, Any]) -> bool:
    if not load_rep.get("overloaded"):
        return True
    return priority >= HIGH_PRIORITY_MIN
