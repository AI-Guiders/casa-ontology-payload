#!/usr/bin/env python3
"""Emergent goals from surprise — domain-neutral META (ADR-0034 B6)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from casa.domain.emergent_promote import promote_goal_route
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.shared.store_persist import mark_runtime_dirty
from casa.prisms.tick.surprise_policy import normalize_cue


def _primary_surprise_concept(control: ControlExtensions) -> str | None:
    for cid in control.surprise:
        s = str(cid).strip()
        if s.startswith(("lang.", "math.", "skill.", "vis.")):
            return s
    return str(control.surprise[0]).strip() if control.surprise else None


def _revise_goal_id(concept_id: str) -> str:
    tail = concept_id.split(".")[-1][:24]
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", tail) or "surprise"
    return f"goal.revise.{safe}"


def propose_goal_from_surprise(
    store_dir: Path,
    state: dict,
    *,
    wm: WorkingMemory,
    control: ControlExtensions,
    hippo_ep: dict[str, Any] | None,
    cue: str = "",
    min_value: float = 0.25,
) -> dict[str, Any] | None:
    """Proposal only — arbiter applies (ADR-0036)."""
    if wm.goal_id or not control.surprise:
        return None
    if control.value < min_value and not hippo_ep:
        return None

    concept = _primary_surprise_concept(control)
    if not concept:
        return None

    gid = _revise_goal_id(concept)
    norm = normalize_cue(cue or wm.goal or concept)
    match = {
        "surprise_kind": concept.split(".")[0] if "." in concept else "misc",
        "cue_prefix": norm[:32],
    }
    route = promote_goal_route(
        state,
        match=match,
        target_goal=gid,
        gate="emergent:surprise",
    )
    mark_runtime_dirty(state)

    return {
        "goal_id": gid,
        "concept_id": concept,
        "route": route,
        "cue_normalized": norm,
        "kind": "revise_after_surprise",
        "goal": f"revise:{concept}",
        "subgoal": "kolb_revise" if control.value >= 0.4 else "rehearse",
    }


def maybe_goal_from_surprise(
    store_dir: Path,
    state: dict,
    *,
    wm: WorkingMemory,
    control: ControlExtensions,
    hippo_ep: dict[str, Any] | None,
    cue: str = "",
    min_value: float = 0.25,
) -> dict[str, Any] | None:
    rep = propose_goal_from_surprise(
        store_dir,
        state,
        wm=wm,
        control=control,
        hippo_ep=hippo_ep,
        cue=cue,
        min_value=min_value,
    )
    if rep is None:
        return None
    wm.goal_id = str(rep["goal_id"])
    wm.goal = str(rep.get("goal") or "")
    wm.subgoal = str(rep.get("subgoal") or "")
    return rep
