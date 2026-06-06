#!/usr/bin/env python3
"""Phrase macro-tick self-drive integration."""

from __future__ import annotations

from unittest.mock import patch

from casa.domain.emergent_promote import promote_from_probe_report, promote_routes_from_probe_report
from casa.domain.plan_tick import PlanTick
from casa.domain.wake_decompose import current_word_focus, init_phrase_queue
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.agent_self_drive_tick import (
    maybe_promote_skill_on_verify,
    prepare_phrase_agent_tick,
)


def _bootstrap_routes(state: dict) -> None:
    for report in (
        {"probe": "analytic-read-corpus-r1", "items": [{"verdict": "analytic_know"}]},
        {"probe": "phrase-compose-pilot", "phrase_know": True, "verdict": "phrase_know"},
    ):
        promote_from_probe_report(state, report, tick=1)
        promote_from_probe_report(state, report, tick=2)
        promote_routes_from_probe_report(state, report, min_mastery_streak=2)


def test_prepare_phrase_agent_tick_sets_word_focus():
    state = ensure_prisms(
        {"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}}
    )
    _bootstrap_routes(state)
    goal = "goal.read.phrase#lang.event.transitive.wash.v0"
    wm = WorkingMemory(goal_id=goal)
    mem_prep: dict = {"plan_tick": {}, "routing_chain": None}
    plan = prepare_phrase_agent_tick(state, wm, mem_prep)
    assert plan.plan_steps
    assert wm.step_focus.startswith("phrase-probe-")


def test_phrase_word_queue_advances_on_analytic_promote():
    state = ensure_prisms(
        {"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}}
    )
    _bootstrap_routes(state)
    goal = "goal.read.phrase#lang.event.transitive.wash.v0"
    wm = WorkingMemory(
        goal_id=goal,
        active_plan_id="plan.trial.phrase_compose",
        plan_steps=["skill.read.analytic", "skill.compose.slots", "skill.verify.phrase"],
        step_index=0,
        step_capability="skill.read.analytic",
    )
    init_phrase_queue(state, goal)
    first = current_word_focus(state, goal_id=goal)
    mem_prep = {"plan_tick": PlanTick.from_wm(wm).to_dict(), "routing_chain": None}

    with patch(
        "casa.prisms.visual.analytic_read.verify_analytic_read_frame",
        return_value=True,
    ):
        from casa.domain.mastery_gate import record_gate_attempt, skill_gate_id

        gid = skill_gate_id("skill.read.analytic")
        record_gate_attempt(state, gid, passed=True, tick=1)
        record_gate_attempt(state, gid, passed=True, tick=2)
        wm.step_focus = first
        mem_prep["plan_tick"] = PlanTick.from_wm(wm).to_dict()
        rep = maybe_promote_skill_on_verify(
            state,
            wm=wm,
            mem_prep=mem_prep,
            knowledge={"predict_verdict": "pass"},
        )

    assert rep is not None
    assert rep.get("phrase_queue", {}).get("advanced") is True
    assert current_word_focus(state, goal_id=goal) != first
