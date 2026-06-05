#!/usr/bin/env python3
"""ADR-0035: route_kind, routing chain, emergent promote, plan tick."""

from __future__ import annotations

from casa.domain.plan_tick import PlanTick, promote_applicability_route, promote_capability_route
from casa.domain.routing import (
    ROUTE_KIND_APPLICABILITY,
    ROUTE_KIND_CAPABILITY,
    ROUTE_KIND_KNOWLEDGE,
    RouteContext,
    Router,
)
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_router import resolve_route, resolve_route_chain, tick_prepare_memory


def test_knowledge_routes_ignore_other_kinds():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    router = Router.bind(state)
    router.bootstrap_defaults(locale="ru")
    router.add_emergent_route(
        route_kind=ROUTE_KIND_CAPABILITY,
        match={"modality": "vis", "novel": "true"},
        target_skill="skill.read.analytic",
        gate="probe_test",
    )
    target = resolve_route(state, RouteContext(modality="t9", locale="ru"))
    assert target.route_kind == ROUTE_KIND_KNOWLEDGE
    assert target.prism_id in ("prism_lang_ru", "prism_memory")
    assert (target.matched or {}).get("modality") == "t9" or (target.matched or {}).get("logical_prism") == "prism_lang_ru"


def test_emergent_capability_resolve():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    promote_capability_route(
        state,
        match={"modality": "vis", "novel": "true"},
        target_skill="skill.read.analytic",
        gate="probe_analytic_read_corpus",
        agent_id="von-neumann",
    )
    router = Router.bind(state)
    layer = router.resolve_layer(
        RouteContext(
            route_kind=ROUTE_KIND_CAPABILITY,
            modality="vis",
            novel="true",
            skill_id="skill.read.analytic",
        )
    )
    assert layer is not None
    assert layer.target_skill == "skill.read.analytic"
    assert (layer.matched or {}).get("modality") == "vis"


def test_emergent_applicability_chain():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    Router.bind(state).bootstrap_defaults(locale="ru")
    promote_capability_route(
        state,
        match={"modality": "vis", "novel": "true"},
        target_skill="skill.read.analytic",
        gate="probe_analytic",
    )
    promote_applicability_route(
        state,
        match={"goal": "goal.read.phrase", "locale": "ru"},
        target_plan="plan.phrase_compose_emergent_v1",
        steps=["skill.read.analytic", "skill.compose.slots", "skill.verify.phrase"],
        gate="probe_phrase_compose_pilot",
        agent_id="von-neumann",
    )
    plan = PlanTick(
        goal_id="goal.read.phrase",
        plan_steps=["skill.read.analytic", "skill.compose.slots"],
        step_index=0,
    )
    plan.sync_step_from_plan()
    chain = resolve_route_chain(
        state,
        RouteContext(modality="vis", locale="ru", novel="true"),
        plan=plan,
    )
    assert chain.applicability is not None
    assert chain.applicability.target_plan == "plan.phrase_compose_emergent_v1"
    assert chain.capability is not None
    assert chain.capability.target_skill == "skill.read.analytic"
    assert chain.knowledge.prism_id == "prism_visual"


def test_tick_prepare_memory_plan_tick_in_wm():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    Router.bind(state).bootstrap_defaults()
    wm = WorkingMemory(
        goal_id="goal.read.phrase",
        plan_steps=["skill.read.analytic"],
        step_index=0,
    )
    prep = tick_prepare_memory(state, cue="мама", modality="vis", wm=wm)
    assert prep["plan_tick"]["goal_id"] == "goal.read.phrase"
    assert prep["plan_tick"]["step_capability"] == "skill.read.analytic"
    assert prep["routing_chain"] is not None
    assert state["sn"].get("routing_chain") is not None


def test_plan_tick_advance():
    plan = PlanTick(
        plan_steps=["skill.read.analytic", "skill.compose.slots"],
        step_index=0,
    )
    plan.sync_step_from_plan()
    assert plan.step_capability == "skill.read.analytic"
    assert plan.advance_after_verify()
    assert plan.step_index == 1
    assert plan.step_capability == "skill.compose.slots"
