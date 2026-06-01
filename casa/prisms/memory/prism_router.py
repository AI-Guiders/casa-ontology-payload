#!/usr/bin/env python3
"""Router prism — modality/locale → content prism (ADR-0016). Facade over casa.domain.routing."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any

from casa.domain.routing import RouteContext, RouteTarget, Router
from casa.prisms.shared.prism_state import normalize_prisms

__all__ = ["RouteContext", "RouteTarget", "resolve_route", "add_route", "bootstrap_default_routes"]


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


def resolve_route(state: dict, ctx: RouteContext) -> RouteTarget:
    normalize_prisms(state)
    return Router.bind(state).resolve(ctx)


def route_context_from_state(
    state: dict,
    *,
    modality: str = "",
    segment: str = "",
    locale: str | None = None,
) -> RouteContext:
    from casa.domain.field_state import FieldState

    return Router.context_from_field(FieldState.bind(state), modality=modality, segment=segment, locale=locale)


def _apply_lattice_hint(state: dict, prism_id: str, hint: str | None) -> None:
    if not hint:
        return
    from casa.prisms.memory.memory_prisms import content_prism_lattices
    from casa.prisms.shared.prism_state import prisms

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
    from casa.prisms.shared.prism_state import set_active_prism

    set_active_prism(state, target.prism_id)
    sn = state.setdefault("sn", {})
    sn["route_lattice_hint"] = target.lattice_hint
    sn["route_matched"] = target.matched
    _apply_lattice_hint(state, target.prism_id, target.lattice_hint)


def apply_route_for_modality(state: dict, modality: str, *, segment: str = "") -> RouteTarget:
    ctx = route_context_from_state(state, modality=modality, segment=segment)
    target = resolve_route(state, ctx)
    apply_route_to_sn(state, target)
    return target


def tick_prepare_memory(state: dict, *, cue: str = "", modality: str = "segment") -> dict[str, Any]:
    from casa.prisms.control.thalamus import thalamus_tick_phase
    from casa.prisms.memory.prism_hot_context import merge_hot_context_digest

    thal = thalamus_tick_phase(state, modality=modality, cue=cue)
    target = apply_route_for_modality(state, modality)
    hot = merge_hot_context_digest(state, cue) if cue else merge_hot_context_digest(state, "")
    return {"thalamus": thal, "route": target, "hot": hot}


def bootstrap_default_routes(state: dict, *, locale: str = "ru", force: bool = False) -> list[dict[str, Any]]:
    normalize_prisms(state)
    routes = Router.bind(state).bootstrap_defaults(locale=locale, force=force)
    return [r.to_row() for r in routes]
