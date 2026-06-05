#!/usr/bin/env python3
"""Goal arbiter — single winning intent per phase (ADR-0036)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casa.domain.deliberate_practice import apply_deliberate_practice
from casa.domain.interleaving_queue import maybe_interleave_goal
from casa.domain.intent_checkpoint import apply_checkpoint_to_wm, checkpoint_restore_candidate
from casa.domain.load_governor import allows_candidate, assess_cognitive_load
from casa.domain.progression_ring import apply_progression_goal, maybe_progression_goal
from casa.domain.spacing_policy import maybe_spacing_goal
from casa.domain.subject_agency import (
    EXPLICIT_PROPOSAL_PRIORITY,
    evaluate_external_proposal,
    disposition_to_priority,
    record_disposition,
)
from casa.prisms.control.fpn_state import WorkingMemory


def collect_retro_intent_candidates(
    store_dir: Path,
) -> list[IntentCandidate]:
    """Turn retro Try items into plan-phase candidates."""
    from casa.domain.agent_journal import last_retrospective

    retro = last_retrospective(store_dir)
    if not isinstance(retro, dict):
        return []
    candidates: list[IntentCandidate] = []
    for item in retro.get("try") or []:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "")
        gid = str(item.get("goal_id") or "")
        if not gid:
            continue
        priority = 55
        if action == "practice":
            priority = 68
        elif action == "rehearse":
            priority = 62
        elif action == "change_approach":
            priority = 66
        elif action == "continue":
            priority = 52
        candidates.append(
            IntentCandidate(
                source="retro",
                priority=priority,
                goal_id=gid,
                goal=str(item.get("goal") or gid),
                step_capability=str(item.get("step_capability") or ""),
                step_focus=str(item.get("step_focus") or ""),
                subgoal=f"retro_{action}",
                payload=item,
            )
        )
    return candidates


@dataclass(frozen=True, slots=True)
class IntentCandidate:
    source: str
    priority: int
    goal_id: str = ""
    goal: str = ""
    step_capability: str = ""
    step_focus: str = ""
    subgoal: str = ""
    payload: dict[str, Any] | None = None


def _winner(candidates: list[IntentCandidate], load_rep: dict[str, Any]) -> IntentCandidate | None:
    viable = [c for c in candidates if allows_candidate(c.priority, load_rep)]
    if not viable:
        return None
    viable.sort(key=lambda c: (-c.priority, c.source))
    return viable[0]


def _apply_candidate(wm: WorkingMemory, cand: IntentCandidate) -> dict[str, Any]:
    if cand.goal_id:
        wm.goal_id = cand.goal_id
    if cand.goal:
        wm.goal = cand.goal
    if cand.step_capability:
        wm.step_capability = cand.step_capability
    if cand.step_focus:
        wm.step_focus = cand.step_focus
    if cand.subgoal:
        wm.subgoal = cand.subgoal
    return {
        "source": cand.source,
        "priority": cand.priority,
        "goal_id": wm.goal_id,
        "goal": wm.goal,
        "step_focus": wm.step_focus,
        "payload": cand.payload,
    }


def collect_plan_candidates(
    state: dict,
    wm: WorkingMemory,
    store_dir: Path,
) -> list[IntentCandidate]:
    candidates: list[IntentCandidate] = []

    if wm.goal_id:
        candidates.append(
            IntentCandidate(
                source="explicit",
                priority=EXPLICIT_PROPOSAL_PRIORITY,
                goal_id=wm.goal_id,
                goal=wm.goal,
                step_capability=wm.step_capability,
                step_focus=wm.step_focus,
            )
        )

    ck = checkpoint_restore_candidate(store_dir, wm)
    if ck:
        candidates.append(
            IntentCandidate(
                source="checkpoint",
                priority=90,
                goal_id=str(ck.get("goal_id") or ""),
                goal=str(ck.get("goal") or ""),
                step_capability=str(ck.get("step_capability") or ""),
                step_focus=str(ck.get("step_focus") or ""),
                subgoal="checkpoint_restore",
                payload=ck,
            )
        )

    weak = state.get("last_weakest_link")
    if isinstance(weak, dict) and weak.get("concept_id"):
        candidates.append(
            IntentCandidate(
                source="deliberate_practice",
                priority=80,
                goal_id=f"goal.practice.{weak.get('concept_id', '').split('.')[-1][:20]}",
                goal=f"practice:{weak.get('concept_id')}",
                step_capability="skill.read.analytic",
                step_focus=str(weak.get("frame_id") or ""),
                subgoal="deliberate_practice",
                payload=weak,
            )
        )

    prog = maybe_progression_goal(state, tick=wm.tick)
    if prog:
        candidates.append(
            IntentCandidate(
                source="progression",
                priority=50,
                goal_id=str(prog.get("goal_id") or ""),
                goal=f"spiral:{prog.get('concept_id')}",
                payload=prog,
            )
        )

    spacing_wm = WorkingMemory(**wm.to_dict())
    spacing = maybe_spacing_goal(state, spacing_wm)
    if spacing:
        candidates.append(
            IntentCandidate(
                source="rehearse",
                priority=40,
                goal_id=str(spacing.get("goal_id") or ""),
                goal=str(spacing_wm.goal or ""),
                payload=spacing,
            )
        )

    if not wm.goal_id:
        inter = maybe_interleave_goal(state, tick=wm.tick, wm_goal_id="")
        if inter:
            candidates.append(
                IntentCandidate(
                    source="interleave",
                    priority=45,
                    goal_id=str(inter.get("goal_id") or ""),
                    goal=str(inter.get("goal") or ""),
                    subgoal=str(inter.get("tract") or ""),
                    payload=inter,
                )
            )

    candidates.extend(collect_retro_intent_candidates(store_dir))

    return candidates


def _apply_subject_agency(
    state: dict,
    wm: WorkingMemory,
    candidates: list[IntentCandidate],
    load_rep: dict[str, Any],
) -> tuple[list[IntentCandidate], dict[str, Any] | None]:
    adjusted: list[IntentCandidate] = []
    disposition_payload: dict[str, Any] | None = None

    for cand in candidates:
        if cand.source != "explicit":
            adjusted.append(cand)
            continue
        disp = evaluate_external_proposal(state, wm, load_rep=load_rep)
        disposition_payload = record_disposition(state, disp)
        priority = disposition_to_priority(disp)
        if priority is None:
            continue
        adjusted.append(
            IntentCandidate(
                source=cand.source,
                priority=priority,
                goal_id=cand.goal_id,
                goal=cand.goal,
                step_capability=cand.step_capability,
                step_focus=cand.step_focus,
                subgoal=cand.subgoal,
                payload=cand.payload,
            )
        )

    return adjusted, disposition_payload


def arbitrate_plan_intent(
    state: dict,
    wm: WorkingMemory,
    store_dir: Path,
) -> dict[str, Any]:
    load_rep = assess_cognitive_load(state, wm)
    raw_candidates = collect_plan_candidates(state, wm, store_dir)
    candidates, subject_disposition = _apply_subject_agency(state, wm, raw_candidates, load_rep)

    winner = _winner(candidates, load_rep)
    if winner is None:
        return {
            "phase": "plan",
            "load": load_rep,
            "winner": None,
            "candidates": len(candidates),
            "subject_disposition": subject_disposition,
        }

    if winner.source == "checkpoint" and winner.payload:
        apply_checkpoint_to_wm(wm, winner.payload)
    elif winner.source == "deliberate_practice" and winner.payload:
        apply_deliberate_practice(wm, winner.payload)
    elif winner.source == "progression" and winner.payload:
        apply_progression_goal(wm, winner.payload)
    elif winner.source == "retro" and winner.payload:
        _apply_candidate(wm, winner)
    else:
        _apply_candidate(wm, winner)

    applied = {
        "source": winner.source,
        "priority": winner.priority,
        "goal_id": wm.goal_id,
        "goal": wm.goal,
        "step_focus": wm.step_focus,
        "payload": winner.payload,
    }
    return {
        "phase": "plan",
        "load": load_rep,
        "winner": applied,
        "candidates": len(candidates),
        "subject_disposition": subject_disposition,
    }


def collect_check_candidates(
    *,
    goal_emergent: dict[str, Any] | None,
    deliberate: dict[str, Any] | None,
    wm: WorkingMemory,
) -> list[IntentCandidate]:
    candidates: list[IntentCandidate] = []
    if deliberate and deliberate.get("applied"):
        candidates.append(
            IntentCandidate(
                source="deliberate_practice",
                priority=80,
                goal_id=str(deliberate.get("goal_id") or wm.goal_id),
                goal=wm.goal,
                step_focus=str(deliberate.get("step_focus") or ""),
                subgoal="deliberate_practice",
                payload=deliberate,
            )
        )
    if goal_emergent:
        candidates.append(
            IntentCandidate(
                source="revise",
                priority=70,
                goal_id=str(goal_emergent.get("goal_id") or ""),
                goal=f"revise:{goal_emergent.get('concept_id')}",
                subgoal="kolb_revise",
                payload=goal_emergent,
            )
        )
    if wm.goal_id:
        candidates.append(
            IntentCandidate(
                source="explicit",
                priority=100,
                goal_id=wm.goal_id,
                goal=wm.goal,
            )
        )
    return candidates


def arbitrate_check_intent(
    state: dict,
    wm: WorkingMemory,
    *,
    goal_emergent: dict[str, Any] | None,
    deliberate: dict[str, Any] | None,
) -> dict[str, Any]:
    load_rep = assess_cognitive_load(state, wm)
    candidates = collect_check_candidates(
        goal_emergent=goal_emergent,
        deliberate=deliberate,
        wm=wm,
    )
    winner = _winner(candidates, load_rep)
    if winner is None:
        return {"phase": "check", "load": load_rep, "winner": None}

    if winner.source == "revise" and winner.payload:
        wm.goal_id = str(winner.payload.get("goal_id") or wm.goal_id)
        wm.goal = f"revise:{winner.payload.get('concept_id')}"
        wm.subgoal = "kolb_revise"
    elif winner.source == "deliberate_practice":
        pass  # already applied in pdca_check
    else:
        _apply_candidate(wm, winner)

    return {
        "phase": "check",
        "load": load_rep,
        "winner": {"source": winner.source, "priority": winner.priority, "goal_id": wm.goal_id},
        "candidates": len(candidates),
    }
