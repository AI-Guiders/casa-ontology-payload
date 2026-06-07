#!/usr/bin/env python3
"""Cognitive load governor — defer low-priority goals when WM overloaded (ADR-0036)."""

from __future__ import annotations

from typing import Any

from casa.domain.hypothesis_queue import open_hypothesis_count
from casa.domain.episode_bind import counts_toward_load
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
        1 for e in prism_hippo(state).get("episodes") or [] if counts_toward_load(e)
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
        "semantic": {
            "hippo_queue": "episodic.pending",
            "policy": "high_priority_only" if overloaded else "normal",
        },
        "policy": "high_priority_only" if overloaded else "normal",
    }
    state.setdefault("sn", {})["cognitive_load"] = rep
    return rep


def allows_candidate(priority: int, load_rep: dict[str, Any]) -> bool:
    if not load_rep.get("overloaded"):
        return True
    return priority >= HIGH_PRIORITY_MIN


def cognitive_load_from_state(state: dict) -> dict[str, Any]:
    """Latest load snapshot from SN (set during tick_prepare_memory)."""
    raw = (state.get("sn") or {}).get("cognitive_load")
    return raw if isinstance(raw, dict) else {}


def should_force_sleep_on_overload(state: dict) -> bool:
    """Overload → sleep even when sleep_every / sleep_on_value would not fire."""
    load_rep = cognitive_load_from_state(state)
    if not load_rep.get("overloaded"):
        return False
    pending = int((load_rep.get("components") or {}).get("hippo_pending") or 0)
    return pending > 0


def retire_stuck_surprise_episodes(state: dict, *, overloaded: bool) -> dict[str, Any]:
    """Retire hippo episodes that cannot merge when WM is overloaded.

    Episodes without ``concept_id`` never pass ``run_sleep`` strengthen — they
    keep ``hippo_pending`` high and trigger perpetual ``cognitive_overload``.
    """
    if not overloaded:
        return {"retired": 0}

    hippo = prism_hippo(state)
    episodes = list(hippo.get("episodes") or [])
    retired: list[str] = []
    for ep in episodes:
        if ep.get("consolidated"):
            continue
        if ep.get("pending") or ep.get("kind") in ("question", "hint"):
            continue
        if str(ep.get("bind_class") or "") == "open_probe":
            continue
        if ep.get("concept_id"):
            continue
        min_rec = max(1, int(ep.get("min_recurrence") or 1))
        if int(ep.get("recurrence_seen") or 0) < min_rec:
            continue
        ep["consolidated"] = True
        ep["overload_retired"] = True
        retired.append(str(ep.get("id") or ""))

    if retired:
        hippo["episodes"] = episodes
        cons = state.setdefault("consolidation", {})
        cons["last_overload_retire"] = {"count": len(retired), "episode_ids": retired[:12]}
    return {"retired": len(retired), "episode_ids": retired[:12]}
