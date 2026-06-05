#!/usr/bin/env python3
"""Agent conscious life on tick: knowledge seek + skill promote (ADR-0034 / ADR-0035)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.emergent_promote import capabilities_on_field
from casa.domain.plan_tick import PlanTick, promote_applicability_route, promote_capability_route
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.tick.kolb_relink_tick import agent_wants_kolb
from casa.prisms.tick.predict_tick import predict_tick
from casa.prisms.visual.vis_frames import (
    FrameKind,
    is_read_frame,
    parse_frame_ref,
    vis_cue_from_frame_id,
)


_SKILL_MATCH: dict[str, dict[str, str]] = {
    "skill.read.whole": {"modality": "vis", "surface_class": "word", "trained_frame": "true"},
    "skill.read.analytic": {"modality": "vis", "surface_class": "word", "novel": "true"},
    "skill.read.grapheme": {"modality": "vis", "surface_class": "grapheme", "locale": "ru"},
    "skill.read.syllable": {"modality": "vis", "surface_class": "syllable", "locale": "ru"},
    "skill.read.phrase": {"modality": "vis", "surface_class": "phrase", "locale": "ru"},
    "skill.lang.closed_class": {"modality": "vis", "surface_class": "meta", "locale": "ru"},
    "skill.compose.slots": {"modality": "vis", "surface_class": "phrase", "locale": "ru"},
    "skill.verify.lex": {"modality": "vis", "surface_class": "word", "locale": "ru"},
    "skill.verify.phrase": {"modality": "vis", "surface_class": "phrase", "locale": "ru"},
}


def _agent_id(state: dict) -> str:
    store = state.get("store") if isinstance(state.get("store"), dict) else {}
    return str(store.get("store_id") or store.get("agent_id") or "agent")


def _plan_from_mem_prep(mem_prep: dict[str, Any]) -> PlanTick:
    raw = mem_prep.get("plan_tick") if isinstance(mem_prep.get("plan_tick"), dict) else {}
    return PlanTick(
        goal_id=str(raw.get("goal_id") or ""),
        active_plan_id=str(raw.get("active_plan_id") or ""),
        plan_steps=list(raw.get("plan_steps") or []),
        step_index=int(raw.get("step_index") or 0),
        step_capability=str(raw.get("step_capability") or ""),
        step_focus=str(raw.get("step_focus") or ""),
    )


def _infer_seek_modality(plan: PlanTick, cue: str, mem_prep: dict[str, Any]) -> str:
    focus = (plan.step_focus or "").strip()
    if parse_frame_ref(cue) or parse_frame_ref(focus):
        return "vis"
    cap = plan.step_capability
    if cap.startswith(("skill.read.", "skill.compose.", "skill.verify.", "skill.lang.", "skill.vis.")):
        return "vis"
    chain = mem_prep.get("routing_chain")
    prism = ""
    if chain is not None:
        know = getattr(chain, "knowledge", None)
        prism = str(getattr(know, "prism_id", "") or "")
    if prism == "prism_math":
        return "schema"
    if prism == "prism_visual":
        return "vis"
    return "t9"


def _seek_cue(plan: PlanTick, cue: str) -> str:
    focus = (plan.step_focus or "").strip()
    ref = parse_frame_ref(focus)
    if ref is not None and ref.kind != FrameKind.UNKNOWN:
        return ref.vis_cue
    if cue.strip():
        return cue.strip()
    if plan.goal_id:
        return plan.goal_id
    return "macro_tick"


def agent_active_intent(wm: WorkingMemory, store_dir: Path) -> bool:
    """Agent drives this tick (goal, plan, or explicit want_kolb)."""
    return bool(
        wm.goal_id
        or wm.goal.strip()
        or wm.plan_steps
        or wm.active_plan_id
        or agent_wants_kolb(store_dir)
    )


def seek_agent_knowledge(
    state: dict,
    *,
    wm: WorkingMemory,
    mem_prep: dict[str, Any],
    cue: str = "",
    bundle: dict | None = None,
) -> dict[str, Any]:
    """Conscious knowledge probe: router + predict on field (not lab oracle)."""
    plan = _plan_from_mem_prep(mem_prep)
    modality = _infer_seek_modality(plan, cue, mem_prep)
    seek_cue = _seek_cue(plan, cue)
    tick = predict_tick(state, seek_cue, modality=modality, bundle=bundle, top_k=8)
    caps = capabilities_on_field(state)
    chain = mem_prep.get("routing_chain")
    out: dict[str, Any] = {
        "cue": seek_cue,
        "modality": modality,
        "goal_id": plan.goal_id,
        "step_capability": plan.step_capability,
        "step_index": plan.step_index,
        "capabilities_on_field": list(caps),
        "predict_verdict": tick.get("verdict"),
        "hypothesis": (tick.get("predict") or {}).get("hypothesis"),
        "route_prism": mem_prep.get("route").prism_id if mem_prep.get("route") else "",
    }
    if chain is not None:
        out["routing_chain"] = chain.to_dict()
    sn = state.setdefault("sn", {})
    sn["agent_knowledge_seek"] = out
    return out


def _step_key(plan: PlanTick) -> str:
    return f"{plan.goal_id}:{plan.step_index}:{plan.step_capability}"


def _verified_steps(state: dict) -> set[str]:
    raw = state.get("sn", {}).get("skill_steps_verified") or []
    return {str(x) for x in raw if x}


def _mark_step_verified(state: dict, key: str) -> None:
    sn = state.setdefault("sn", {})
    verified = [str(x) for x in (sn.get("skill_steps_verified") or []) if x]
    if key not in verified:
        verified.append(key)
    sn["skill_steps_verified"] = verified[-64:]


def _verify_plan_step(
    state: dict,
    *,
    plan: PlanTick,
    cue: str,
    bundle: dict | None,
    knowledge: dict[str, Any],
    mem_prep: dict[str, Any],
) -> bool:
    """Agent self-check for current plan step before skill promote."""
    cap = plan.step_capability
    if not cap:
        return False

    if knowledge.get("predict_verdict") == "pass":
        hyp = knowledge.get("hypothesis")
        if cap.startswith("skill.verify.") and hyp:
            return True
        if cap.startswith("skill.read.") and hyp:
            return True

    focus = plan.step_focus or cue
    ref = parse_frame_ref(focus)
    frame_id = ref.frame_id if ref is not None else focus
    if cap == "skill.read.analytic" and is_read_frame(focus):
        from casa.prisms.visual.analytic_read import verify_analytic_read_frame

        return verify_analytic_read_frame(state, frame_id)

    if cap in ("skill.read.whole", "skill.verify.lex") and ref is not None and ref.kind in (
        FrameKind.WORD,
        FrameKind.SYLLABLE,
        FrameKind.PHRASE_PROBE,
    ):
        from casa.prisms.visual.analytic_read import leaders_at_max
        from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

        preds = predict_lex_for_vis_cue(state, frame_id, top_k=5)
        top, leaders = leaders_at_max(preds)
        return bool(leaders) and top >= 2

    tick = predict_tick(
        state,
        _seek_cue(plan, cue),
        modality=_infer_seek_modality(plan, cue, mem_prep),
        bundle=bundle,
    )
    return tick.get("verdict") in ("pass", "provisional")


def maybe_promote_skill_on_verify(
    state: dict,
    *,
    wm: WorkingMemory,
    mem_prep: dict[str, Any],
    knowledge: dict[str, Any],
    cue: str = "",
    gate: str | None = None,
    store_dir: Path | None = None,
) -> dict[str, Any] | None:
    """After self-verify — agent promotes capability / applicability routes."""
    plan = _plan_from_mem_prep(mem_prep)
    if not plan.step_capability or not plan.goal_id:
        return None

    key = _step_key(plan)
    if key in _verified_steps(state):
        return {"skipped": True, "reason": "step_already_promoted", "step_key": key}

    if not _verify_plan_step(
        state, plan=plan, cue=cue, bundle=None, knowledge=knowledge, mem_prep=mem_prep
    ):
        return {"skipped": True, "reason": "step_verify_failed", "step_key": key}

    from casa.domain.mastery_gate import (
        mastery_ready_for_skill,
        record_gate_attempt,
        skill_gate_id,
    )

    skill = plan.step_capability
    gid = gate or skill_gate_id(skill)
    record_gate_attempt(state, gid, passed=True, tick=wm.tick, store_dir=store_dir)
    if not mastery_ready_for_skill(state, skill, min_streak=2):
        return {
            "skipped": True,
            "reason": "mastery_pending",
            "step_key": key,
            "gate": gid,
        }

    aid = _agent_id(state)
    promoted: list[dict[str, Any]] = []
    match = dict(_SKILL_MATCH.get(plan.step_capability) or {"modality": "vis", "locale": "ru"})
    row = promote_capability_route(
        state,
        match=match,
        target_skill=plan.step_capability,
        gate=gid,
        agent_id=aid,
    )
    promoted.append(row)
    _mark_step_verified(state, key)

    phrase_advance: dict[str, Any] | None = None
    gid_goal = str(plan.goal_id or "").strip()
    if plan.step_capability == "skill.read.analytic" and gid_goal.startswith("goal.read.phrase"):
        from casa.domain.wake_decompose import advance_word_queue, current_word_focus

        phrase_advance = advance_word_queue(state, passed=True)
        next_focus = current_word_focus(state, goal_id=gid_goal)
        if next_focus:
            wm.step_focus = next_focus

    applicability_row: dict[str, Any] | None = None
    if plan.plan_steps:
        verified = _verified_steps(state)
        all_done = all(
            f"{plan.goal_id}:{i}:{step}" in verified
            for i, step in enumerate(plan.plan_steps)
            if step.startswith("skill.")
        )
        if all_done:
            plan_id = plan.active_plan_id or f"plan.emergent_{plan.goal_id.replace('.', '_')}"
            applicability_row = promote_applicability_route(
                state,
                match={"goal": plan.goal_id, "locale": "ru"},
                target_plan=plan_id,
                steps=[s for s in plan.plan_steps if s.startswith("skill.")],
                gate=gid,
                agent_id=aid,
            )
            promoted.append(applicability_row)

    wm_sync = PlanTick.from_wm(wm)
    if wm_sync.plan_steps and wm_sync.advance_after_verify():
        wm_sync.apply_to_wm(wm)

    return {
        "gate": gid,
        "step_key": key,
        "promoted": promoted,
        "applicability": applicability_row,
        "capabilities_after": list(capabilities_on_field(state)),
        "plan_advanced": wm.step_index,
        "phrase_queue": phrase_advance,
    }


def maybe_agent_self_drive_tick(
    store_dir: Path,
    state: dict,
    *,
    wm: WorkingMemory,
    control: ControlExtensions,
    mem_prep: dict[str, Any],
    cue: str = "",
    bundle: dict | None = None,
    min_drive_value: float = 0.25,
) -> dict[str, Any] | None:
    """Life hook: agent seeks knowledge and promotes skills under its own intent."""
    if not agent_active_intent(wm, store_dir):
        return None
    if control.value < min_drive_value and not agent_wants_kolb(store_dir) and not wm.goal_id:
        return None

    knowledge = seek_agent_knowledge(state, wm=wm, mem_prep=mem_prep, cue=cue, bundle=bundle)
    skill = maybe_promote_skill_on_verify(
        state,
        wm=wm,
        mem_prep=mem_prep,
        knowledge=knowledge,
        cue=cue,
        store_dir=store_dir,
    )
    return {
        "agent_controlled": True,
        "knowledge_seek": knowledge,
        "skill_promote": skill,
        "want_kolb": agent_wants_kolb(store_dir),
    }
