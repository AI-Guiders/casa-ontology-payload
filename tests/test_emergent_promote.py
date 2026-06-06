#!/usr/bin/env python3
"""Emergent promote after probe gate + trial plan."""

from __future__ import annotations

from casa.domain.emergent_promote import (
    fill_trial_plan_if_needed,
    promote_from_probe_report,
    promote_routes_from_probe_report,
    record_probe_gate,
    suggest_trial_plan,
)
from casa.domain.plan_tick import PlanTick
from casa.domain.routing import ROUTE_KIND_CAPABILITY, Router
from casa.prisms.memory.memory_prisms import ensure_prisms


def _gate_streak(state, report, *, streak: int = 2):
    for tick in range(1, streak + 1):
        promote_from_probe_report(state, report, tick=tick)


def test_record_probe_gate_no_routes():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}})
    report = {
        "probe": "literacy-corpus-quiz",
        "total": 10,
        "know": 10,
        "empty": 0,
        "wrong": 0,
    }
    record_probe_gate(state, report, tick=1)
    result = record_probe_gate(state, report, tick=2)
    assert result.passed
    assert not result.promoted
    caps = Router.bind(state).routes(route_kind=ROUTE_KIND_CAPABILITY)
    assert not any(r.target_skill == "skill.read.whole" for r in caps)


def test_promote_corpus_whole_after_full_know():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "von-neumann"}})
    report = {
        "probe": "literacy-corpus-quiz",
        "stage": "stage-06-words-cyrl-corpus",
        "total": 10,
        "know": 10,
        "empty": 0,
        "wrong": 0,
        "ambiguous": 0,
    }
    _gate_streak(state, report)
    result = promote_routes_from_probe_report(state, report, min_mastery_streak=2)
    assert len(result.promoted) >= 1
    caps = Router.bind(state).routes(route_kind=ROUTE_KIND_CAPABILITY)
    assert any(r.target_skill == "skill.read.whole" for r in caps)


def test_promote_skips_duplicate():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}})
    report = {
        "probe": "literacy-corpus-quiz",
        "total": 2,
        "know": 2,
        "empty": 0,
        "wrong": 0,
    }
    _gate_streak(state, report)
    r1 = promote_routes_from_probe_report(state, report, min_mastery_streak=2)
    r2 = promote_routes_from_probe_report(state, report, min_mastery_streak=2)
    assert len(r1.promoted) >= 1
    assert r2.skipped


def test_promote_analytic_r1_gate():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "von-neumann"}})
    report = {
        "probe": "analytic-read-corpus-r1",
        "items": [
            {"verdict": "analytic_know", "r1_novel_bind": True, "r1_novel_via": "novel_compose"},
            {"verdict": "analytic_know"},
        ],
    }
    _gate_streak(state, report)
    result = promote_routes_from_probe_report(state, report, min_mastery_streak=2)
    assert result.promoted
    caps = Router.bind(state).routes(route_kind=ROUTE_KIND_CAPABILITY)
    assert any(r.target_skill == "skill.read.analytic" for r in caps)


def test_trial_plan_without_router():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}})
    rep = {
        "probe": "analytic-read-corpus-r1",
        "items": [{"verdict": "analytic_know"}],
    }
    _gate_streak(state, rep)
    promote_routes_from_probe_report(state, rep, min_mastery_streak=2)
    plan = PlanTick(goal_id="goal.read.phrase")
    filled = fill_trial_plan_if_needed(state, plan)
    assert filled.plan_steps
    assert filled.active_plan_id.startswith("plan.trial.")


def test_suggest_trial_needs_capability_for_phrase():
    assert suggest_trial_plan("goal.read.phrase", ("skill.read.analytic",)) is not None
    assert suggest_trial_plan("goal.read.phrase", ()) is None
