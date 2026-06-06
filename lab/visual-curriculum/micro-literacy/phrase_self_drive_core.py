"""Shared phrase self-drive loop (analytic → compose → macro tick)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from casa.domain.mastery_gate import record_gate_attempt, skill_gate_id
from casa.domain.plan_tick import PlanTick
from casa.domain.wake_decompose import (
    advance_word_queue,
    current_word_focus,
    init_phrase_queue,
    phrase_compose_entry_for_goal,
    phrase_event_id_from_goal,
)
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.tick.agent_self_drive_tick import (
    maybe_agent_self_drive_tick,
    maybe_promote_skill_on_verify,
    prepare_phrase_agent_tick,
)
from casa.prisms.visual.phrase_compose import check_agreement, check_modifier_agreement


def run_phrase_self_drive_event(
    store_dir,
    state: dict,
    *,
    goal: str,
    record_agreement: bool = True,
) -> dict[str, Any]:
    from casa.domain.emergent_promote import promote_from_probe_report, promote_routes_from_probe_report

    for report in (
        {"probe": "analytic-read-corpus-r1", "items": [{"verdict": "analytic_know"}]},
        {"probe": "phrase-compose-pilot", "phrase_know": True, "verdict": "phrase_know"},
    ):
        promote_from_probe_report(state, report, tick=1)
        promote_from_probe_report(state, report, tick=2)
        promote_routes_from_probe_report(state, report, min_mastery_streak=2)

    wm = WorkingMemory(goal_id=goal)
    mem_prep: dict = {"plan_tick": {}, "routing_chain": None}
    prepare_phrase_agent_tick(state, wm, mem_prep)
    event_id = phrase_event_id_from_goal(goal)
    entry = phrase_compose_entry_for_goal(goal)
    init_phrase_queue(state, goal)
    words_done: list[str] = []
    analytic_gid = skill_gate_id("skill.read.analytic")
    dec0 = state.get("wake_decompose") or {}
    word_count = len(dec0.get("words") or [])
    max_iters = max(word_count * 2, 8)
    agreement_ok = False
    modifier_ok = False
    mod_spec = entry.get("possessive_agreement") or entry.get("numeral_agreement")

    with patch(
        "casa.prisms.visual.analytic_read.verify_analytic_read_frame",
        return_value=True,
    ):
        for _ in range(max_iters):
            focus = current_word_focus(state, goal_id=goal)
            if not focus:
                break
            wm.step_capability = "skill.read.analytic"
            wm.step_index = len(words_done)
            wm.step_focus = focus
            mem_prep["plan_tick"] = PlanTick.from_wm(wm).to_dict()
            record_gate_attempt(state, analytic_gid, passed=True, tick=wm.tick)
            record_gate_attempt(state, analytic_gid, passed=True, tick=wm.tick + 1)
            rep = maybe_promote_skill_on_verify(
                state,
                wm=wm,
                mem_prep=mem_prep,
                knowledge={"predict_verdict": "pass", "hypothesis": event_id},
            )
            if rep and not rep.get("phrase_queue", {}).get("advanced"):
                advance_word_queue(state, passed=True)
            words_done.append(focus)
            wm.tick += 1
            if len(words_done) >= word_count:
                break
        else:
            raise RuntimeError(f"phrase analytic loop exceeded {max_iters} iterations")

        wm.step_capability = "skill.compose.slots"
        wm.step_index = 1
        mem_prep["plan_tick"] = PlanTick.from_wm(wm).to_dict()
        compose_gid = skill_gate_id("skill.compose.slots")
        record_gate_attempt(state, compose_gid, passed=True, tick=wm.tick)
        record_gate_attempt(state, compose_gid, passed=True, tick=wm.tick + 1)
        maybe_promote_skill_on_verify(
            state,
            wm=wm,
            mem_prep=mem_prep,
            knowledge={"predict_verdict": "pass", "hypothesis": event_id},
        )

        slots = {
            str(w.get("role") or ""): {"surface": str(w.get("surface") or "")}
            for w in entry.get("words") or []
            if isinstance(w, dict) and w.get("role")
        }

        if record_agreement and entry.get("agreement"):
            agr = check_agreement(slots, list(entry.get("agreement") or []))
            agreement_ok = bool(agr.get("ok"))
            if agreement_ok:
                agree_gid = skill_gate_id("skill.agree.subjectVerb")
                record_gate_attempt(state, agree_gid, passed=True, tick=wm.tick)
                record_gate_attempt(state, agree_gid, passed=True, tick=wm.tick + 1)
                maybe_promote_skill_on_verify(
                    state,
                    wm=wm,
                    mem_prep=mem_prep,
                    knowledge={"predict_verdict": "pass", "hypothesis": event_id},
                )

        if record_agreement and mod_spec:
            mod = check_modifier_agreement(slots, entry)
            modifier_ok = bool(mod.get("ok"))
            if modifier_ok:
                mod_gid = skill_gate_id("skill.agree.modifierHead")
                record_gate_attempt(state, mod_gid, passed=True, tick=wm.tick)
                record_gate_attempt(state, mod_gid, passed=True, tick=wm.tick + 1)
                maybe_promote_skill_on_verify(
                    state,
                    wm=wm,
                    mem_prep=mem_prep,
                    knowledge={"predict_verdict": "pass", "hypothesis": event_id},
                )

        control = ControlExtensions(
            predicted=(),
            surprise=(),
            prediction_error=0.0,
            dan_mask=(),
            sparse_ratio=0.0,
            masked_digest=(),
            value=0.5,
        )
        macro = maybe_agent_self_drive_tick(
            store_dir,
            state,
            wm=wm,
            control=control,
            mem_prep=mem_prep,
        )

    wake_complete = len(words_done) == word_count
    return {
        "goal": goal,
        "event_id": event_id,
        "words_analytic": words_done,
        "word_count": word_count,
        "macro_tick": macro is not None,
        "wake_complete": wake_complete,
        "agreement_ok": agreement_ok,
        "has_agreement_spec": bool(entry.get("agreement")),
        "modifier_ok": modifier_ok,
        "has_modifier_spec": bool(mod_spec),
    }
