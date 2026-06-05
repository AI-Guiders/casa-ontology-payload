#!/usr/bin/env python3
"""Router prism — multi-layer match→target (ADR-0016 / ADR-0035). Facade over casa.domain.routing."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from pathlib import Path
from typing import Any

from casa.domain.emergent_promote import fill_trial_plan_if_needed
from casa.domain.plan_tick import PlanTick, merge_chain_into_plan
from casa.domain.routing import (
    ROUTE_KIND_KNOWLEDGE,
    RouteContext,
    RouteTarget,
    Router,
    RoutingChain,
)
from casa.domain.prism_wire import normalize_prisms

__all__ = [
    "RouteContext",
    "RouteTarget",
    "RoutingChain",
    "resolve_route",
    "resolve_route_chain",
    "add_route",
    "add_emergent_route",
    "bootstrap_default_routes",
]


def profile_default_content_prism(state: dict) -> str | None:
    from casa.domain.field_state import FieldState

    return FieldState.bind(state).profile_default_content_prism()


def router_routes(state: dict) -> list[dict[str, Any]]:
    normalize_prisms(state)
    return [r.to_row() for r in Router.bind(state).routes()]


def add_route(
    state: dict,
    match: dict[str, str],
    target_prism: str,
    *,
    lattice_hint: str | None = None,
    priority: int = 0,
) -> dict[str, Any]:
    normalize_prisms(state)
    return Router.bind(state).add_route(
        match, target_prism, lattice_hint=lattice_hint, priority=priority
    ).to_row()


def add_emergent_route(state: dict, **kwargs: Any) -> dict[str, Any]:
    normalize_prisms(state)
    return Router.bind(state).add_emergent_route(**kwargs).to_row()


def resolve_route(state: dict, ctx: RouteContext) -> RouteTarget:
    normalize_prisms(state)
    return Router.bind(state).resolve(ctx)


def resolve_route_chain(
    state: dict,
    ctx: RouteContext,
    *,
    plan: PlanTick | None = None,
) -> RoutingChain:
    normalize_prisms(state)
    pt = plan or PlanTick()
    return Router.bind(state).resolve_chain(
        ctx,
        goal_id=pt.goal_id,
        skill_id=pt.step_capability,
        capabilities_available=pt.capabilities_available(),
    )


def route_context_from_state(
    state: dict,
    *,
    modality: str = "",
    segment: str = "",
    locale: str | None = None,
    route_kind: str = ROUTE_KIND_KNOWLEDGE,
    goal_id: str = "",
    skill_id: str = "",
    surface_class: str = "",
    novel: str = "",
) -> RouteContext:
    from casa.domain.field_state import FieldState

    return Router.context_from_field(
        FieldState.bind(state),
        modality=modality,
        segment=segment,
        locale=locale,
        route_kind=route_kind,  # type: ignore[arg-type]
        goal_id=goal_id,
        skill_id=skill_id,
        surface_class=surface_class,
        novel=novel,
    )


def _apply_lattice_hint(state: dict, prism_id: str, hint: str | None) -> None:
    if not hint:
        return
    from casa.prisms.memory.memory_prisms import content_prism_lattices
    from casa.domain.prism_wire import prisms

    lats = content_prism_lattices(state, prism_id)
    if hint in lats:
        state.setdefault("sn", {})["active_lattice"] = hint
        block = prisms(state).get(prism_id)
        if isinstance(block, dict):
            block["active_lattice"] = hint
        return
    if hint in ("L2_word", "lexicon"):
        for lid in sorted(lats):
            if lid.startswith("L2_") or lid.startswith("lexicon-"):
                state.setdefault("sn", {})["active_lattice"] = lid
                block = prisms(state).get(prism_id)
                if isinstance(block, dict):
                    block["active_lattice"] = lid
                return


def apply_route_to_sn(state: dict, target: RouteTarget) -> None:
    from casa.domain.prism_wire import set_active_prism

    if target.route_kind == ROUTE_KIND_KNOWLEDGE and target.prism_id:
        set_active_prism(state, target.prism_id)
    sn = state.setdefault("sn", {})
    sn["route_kind"] = target.route_kind
    sn["route_lattice_hint"] = target.lattice_hint
    sn["route_matched"] = target.matched
    if target.target_skill:
        sn["route_target_skill"] = target.target_skill
    if target.target_goal:
        sn["route_target_goal"] = target.target_goal
    if target.target_plan:
        sn["route_target_plan"] = target.target_plan
    if target.steps:
        sn["route_plan_steps"] = list(target.steps)
    if target.prism_id:
        _apply_lattice_hint(state, target.prism_id, target.lattice_hint)


def apply_route_chain_to_sn(state: dict, chain: RoutingChain) -> None:
    apply_route_to_sn(state, chain.knowledge)
    sn = state.setdefault("sn", {})
    sn["routing_chain"] = chain.to_dict()


def apply_route_for_modality(state: dict, modality: str, *, segment: str = "") -> RouteTarget:
    ctx = route_context_from_state(state, modality=modality, segment=segment)
    target = resolve_route(state, ctx)
    apply_route_to_sn(state, target)
    return target


def tick_prepare_memory(
    state: dict,
    *,
    cue: str = "",
    modality: str = "segment",
    wm: Any | None = None,
    store_dir: Any | None = None,
) -> dict[str, Any]:
    from casa.prisms.control.thalamus import thalamus_tick_phase
    from casa.prisms.memory.prism_hot_context import merge_hot_context_digest

    from casa.domain.autonomy_intent import apply_autonomy_seed
    from casa.domain.goal_arbiter import arbitrate_plan_intent
    from casa.domain.scaffold_fading import scaffold_plan_hint

    thal = thalamus_tick_phase(state, modality=modality, cue=cue)
    plan = PlanTick.from_wm(wm)
    autonomy_seed: dict | None = None
    if wm is not None and store_dir is not None:
        autonomy_seed = apply_autonomy_seed(state, Path(store_dir), wm)
    arbiter_rep: dict | None = None
    if wm is not None and store_dir is not None:
        arbiter_rep = arbitrate_plan_intent(state, wm, Path(store_dir))
    scaffold_hint = scaffold_plan_hint(state)
    winner = (arbiter_rep or {}).get("winner") or {}
    spacing_rep = winner.get("payload") if winner.get("source") == "rehearse" else None
    progression_rep = winner.get("payload") if winner.get("source") == "progression" else None
    if not plan.goal_id and wm is not None and getattr(wm, "goal", ""):
        plan.goal_id = str(wm.goal).strip()[:120]
    plan.sync_step_from_plan()
    ctx = route_context_from_state(
        state,
        modality=modality,
        goal_id=plan.goal_id,
        skill_id=plan.step_capability,
    )
    chain = resolve_route_chain(state, ctx, plan=plan)
    plan = merge_chain_into_plan(plan, chain)
    plan = fill_trial_plan_if_needed(state, plan)
    if wm is not None:
        plan.apply_to_wm(wm)
    apply_route_chain_to_sn(state, chain)
    hot = merge_hot_context_digest(state, cue) if cue else merge_hot_context_digest(state, "")
    return {
        "thalamus": thal,
        "route": chain.knowledge,
        "routing_chain": chain,
        "plan_tick": plan.to_dict(),
        "hot": hot,
        "spacing_goal": spacing_rep,
        "progression_goal": progression_rep,
        "scaffold_hint": scaffold_hint,
        "goal_arbiter": arbiter_rep,
        "autonomy_seed": autonomy_seed,
    }


def bootstrap_default_routes(state: dict, *, locale: str = "ru", force: bool = False) -> list[dict[str, Any]]:
    normalize_prisms(state)
    routes = Router.bind(state).bootstrap_defaults(locale=locale, force=force)
    return [r.to_row() for r in routes]
