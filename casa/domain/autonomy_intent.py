#!/usr/bin/env python3
"""Autonomous intent seed — subject picks next tract without inbox (north star)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.domain.emergent_promote import capabilities_on_field
from casa.domain.interleaving_queue import maybe_interleave_goal
from casa.domain.progression_ring import maybe_progression_goal
from casa.domain.spacing_policy import maybe_spacing_goal
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.tick.kolb_relink_tick import agent_wants_kolb


def _session_raw(store_dir: Path) -> dict[str, Any]:
    path = store_dir / "agent_session.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def pick_autonomous_goal(
    state: dict,
    store_dir: Path,
    wm: WorkingMemory,
) -> dict[str, Any] | None:
    """Seed WM goal when subject has no explicit intent (priority: practice > spacing > progression > interleave)."""
    if wm.goal_id or wm.plan_steps:
        return None

    weak = state.get("last_weakest_link")
    if isinstance(weak, dict) and weak.get("concept_id"):
        cid = str(weak.get("concept_id") or "")
        return {
            "goal_id": f"goal.practice.{cid.split('.')[-1][:20]}",
            "goal": f"practice:{cid}",
            "source": "deliberate_practice",
            "step_capability": "skill.read.analytic",
            "step_focus": str(weak.get("frame_id") or ""),
        }

    spacing_wm = WorkingMemory(**wm.to_dict())
    spacing = maybe_spacing_goal(state, spacing_wm)
    if spacing:
        return {**spacing, "source": "rehearse"}

    progression = maybe_progression_goal(state, tick=wm.tick)
    if progression:
        return {**progression, "source": "progression"}

    caps = capabilities_on_field(state)
    session = _session_raw(store_dir)
    drive = session.get("self_drive") if isinstance(session.get("self_drive"), dict) else {}
    if drive.get("want_kolb") and not any(c.startswith("skill.read.") for c in caps):
        inter = maybe_interleave_goal(state, tick=wm.tick, wm_goal_id="")
        if inter:
            return {**inter, "source": "interleave"}

    if agent_wants_kolb(store_dir) and any(c.startswith("skill.math.") for c in caps):
        return None  # let Kolb/self_drive handle math

    inter = maybe_interleave_goal(state, tick=wm.tick, wm_goal_id="")
    if inter:
        return {**inter, "source": "interleave"}
    return None


def apply_autonomy_seed(state: dict, store_dir: Path, wm: WorkingMemory) -> dict[str, Any] | None:
    """Write picked goal into WM when empty."""
    picked = pick_autonomous_goal(state, store_dir, wm)
    if not picked:
        return None
    wm.goal_id = str(picked.get("goal_id") or "")
    wm.goal = str(picked.get("goal") or wm.goal_id)
    if picked.get("step_capability"):
        wm.step_capability = str(picked["step_capability"])
    if picked.get("step_focus"):
        wm.step_focus = str(picked["step_focus"])
    state.setdefault("sn", {})["autonomy_seed"] = picked
    return picked
