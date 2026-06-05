#!/usr/bin/env python3
"""Autonomy: wake decompose, interleave, autonomy seed, self-check."""

from __future__ import annotations

import json
from pathlib import Path

from casa.domain.autonomy_intent import apply_autonomy_seed, pick_autonomous_goal
from casa.domain.emergent_promote import fill_trial_plan_if_needed
from casa.domain.interleaving_queue import maybe_interleave_goal
from casa.domain.plan_tick import PlanTick
from casa.domain.routing import ROUTE_KIND_CAPABILITY, Router
from casa.domain.wake_decompose import apply_wake_decompose, current_word_focus, init_phrase_queue
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.self_check_tick import maybe_self_check_before_cen


def test_wake_decompose_sets_phrase_focus():
    state: dict = {}
    plan = PlanTick(goal_id="goal.read.phrase", plan_steps=["skill.read.analytic"], step_index=0)
    plan = fill_trial_plan_if_needed(state, plan)
    out = apply_wake_decompose(state, plan)
    assert out.step_focus.startswith("phrase-probe-")
    assert current_word_focus(state, goal_id="goal.read.phrase") == out.step_focus


def test_interleave_goal_when_wm_empty():
    state: dict = {"interleave_queue": {"tracts": ["literacy", "math"], "cursor": 0}}
    inter = maybe_interleave_goal(state, tick=1, wm_goal_id="")
    assert inter is not None
    assert inter["goal_id"] == "goal.read.phrase"


def test_autonomy_seed_practice_over_interleave():
    state = {"last_weakest_link": {"concept_id": "syllable.ла", "frame_id": "syllable-ла-sans"}}
    wm = WorkingMemory(tick=1)
    tmp = Path("/tmp/autonomy-seed-test")
    picked = pick_autonomous_goal(state, tmp, wm)
    assert picked is not None
    assert picked["source"] == "deliberate_practice"
    apply_autonomy_seed(state, tmp, wm)
    assert wm.goal_id.startswith("goal.practice.")


def test_self_check_writes_sn():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    wm = WorkingMemory(step_capability="skill.read.analytic", step_focus="word-x-sans")
    mem_prep = {"plan_tick": wm.to_dict(), "routing_chain": None}
    rep = maybe_self_check_before_cen(state, wm=wm, mem_prep=mem_prep)
    assert "metacog" in rep
    assert state["sn"].get("self_check") is not None


def test_goal_arbiter_interleave_candidate():
    from casa.domain.goal_arbiter import collect_plan_candidates

    state: dict = {"interleave_queue": {"tracts": ["literacy"], "cursor": 0}}
    wm = WorkingMemory(tick=3)
    candidates = collect_plan_candidates(state, wm, Path("/tmp/none"))
    assert any(c.source == "interleave" for c in candidates)


def test_fill_trial_plan_with_capability_on_field():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    Router.bind(state).add_emergent_route(
        route_kind=ROUTE_KIND_CAPABILITY,
        match={"modality": "vis", "novel": "true"},
        target_skill="skill.read.analytic",
        gate="test",
    )
    plan = PlanTick(goal_id="goal.read.phrase")
    out = fill_trial_plan_if_needed(state, plan)
    assert out.plan_steps
    assert out.step_focus.startswith("phrase-probe-")
