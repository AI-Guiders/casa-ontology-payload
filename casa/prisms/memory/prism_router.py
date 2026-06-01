#!/usr/bin/env python3
"""Router prism — modality/locale → content prism (ADR-0016)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from dataclasses import dataclass
from typing import Any

from casa.prisms.shared.prism_state import PRISM_MEMORY, PRISM_ROUTER, PRISM_VISUAL, normalize_prisms, prism_router
from casa.prisms.memory.prism_spawn import validate_content_prism_id


@dataclass(frozen=True, slots=True)
class RouteContext:
    modality: str = ""
    locale: str = ""
    segment: str = ""
    tier: str = ""
    store_id: str = ""


@dataclass(frozen=True, slots=True)
class RouteTarget:
    prism_id: str
    lattice_hint: str | None = None
    route_index: int | None = None
    matched: dict[str, str] | None = None


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def profile_default_content_prism(state: dict) -> str | None:
    """Store/profile default before router block default (ADR-0016)."""
    for key in ("store", "profile"):
        block = state.get(key)
        if not isinstance(block, dict):
            continue
        raw = block.get("default_content_prism")
        if raw:
            return validate_content_prism_id(str(raw))
    return None


def router_routes(state: dict) -> list[dict[str, Any]]:
    normalize_prisms(state)
    return list(prism_router(state).get("routes") or [])


def add_route(
    state: dict,
    match: dict[str, str],
    target_prism: str,
    *,
    lattice_hint: str | None = None,
    priority: int = 0,
) -> dict[str, Any]:
    normalize_prisms(state)
    block = prism_router(state)
    pid = validate_content_prism_id(target_prism)
    row = {
        "match": {k: _norm(v) for k, v in match.items() if v},
        "target_prism": pid,
        "lattice_hint": lattice_hint,
        "priority": int(priority),
    }
    routes = block.setdefault("routes", [])
    routes.append(row)
    routes.sort(key=lambda r: int(r.get("priority") or 0), reverse=True)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return row


def _match_score(route_match: dict[str, str], ctx: RouteContext) -> int:
    ctx_map = {
        "modality": _norm(ctx.modality),
        "locale": _norm(ctx.locale),
        "segment": _norm(ctx.segment),
        "tier": _norm(ctx.tier),
        "store_id": _norm(ctx.store_id),
    }
    if not route_match:
        return 0
    score = 0
    for key, want in route_match.items():
        got = ctx_map.get(key, "")
        if not want:
            continue
        if got != want:
            return -1
        score += 10
    return score


def resolve_route(state: dict, ctx: RouteContext) -> RouteTarget:
    """Pick content prism for this tick; falls back to router default or prism_memory."""
    normalize_prisms(state)
    block = prism_router(state)
    best: RouteTarget | None = None
    best_score = -1
    for i, row in enumerate(block.get("routes") or []):
        m = row.get("match") or {}
        sc = _match_score(m, ctx)
        if sc > best_score:
            best_score = sc
            best = RouteTarget(
                prism_id=str(row.get("target_prism") or PRISM_MEMORY),
                lattice_hint=row.get("lattice_hint"),
                route_index=i,
                matched=dict(m),
            )
    if best is not None and best_score >= 0:
        return best
    profile_default = profile_default_content_prism(state)
    if profile_default:
        return RouteTarget(
            prism_id=profile_default,
            lattice_hint=None,
            route_index=None,
            matched={"source": "profile"},
        )
    default = str(block.get("default_content_prism") or PRISM_MEMORY)
    return RouteTarget(prism_id=default, lattice_hint=None, route_index=None, matched=None)


def route_context_from_state(
    state: dict,
    *,
    modality: str = "",
    segment: str = "",
    locale: str | None = None,
) -> RouteContext:
    store = state.get("store") if isinstance(state.get("store"), dict) else {}
    loc = str(store.get("locale") or "ru") if locale is None else locale
    return RouteContext(
        modality=_norm(modality),
        locale=_norm(loc),
        segment=_norm(segment),
        tier=_norm(str(store.get("tier") or "")),
        store_id=_norm(str(store.get("store_id") or "")),
    )


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
    """Resolve and apply route for predict/tick (ADR-0016)."""
    ctx = route_context_from_state(state, modality=modality, segment=segment)
    target = resolve_route(state, ctx)
    apply_route_to_sn(state, target)
    return target


def tick_prepare_memory(state: dict, *, cue: str = "", modality: str = "segment") -> dict[str, Any]:
    """Route → hot digest (tick order before predict)."""
    from casa.prisms.memory.prism_hot_context import merge_hot_context_digest

    target = apply_route_for_modality(state, modality)
    hot = merge_hot_context_digest(state, cue) if cue else merge_hot_context_digest(state, "")
    return {"route": target, "hot": hot}


def bootstrap_default_routes(state: dict, *, locale: str = "ru", force: bool = False) -> list[dict[str, Any]]:
    """Idempotent lab defaults for bilingual / math (structural init — no field_version bump)."""
    normalize_prisms(state)
    block = prism_router(state)
    if block.get("routes") and not force:
        return list(block.get("routes") or [])
    rows = [
        {
            "match": {"modality": "schema"},
            "target_prism": PRISM_MEMORY,
            "lattice_hint": "schema-math",
            "priority": 100,
        },
        {
            "match": {"modality": "vis"},
            "target_prism": PRISM_VISUAL,
            "lattice_hint": "V1_object",
            "priority": 95,
        },
        {
            "match": {"modality": "image"},
            "target_prism": PRISM_VISUAL,
            "lattice_hint": "V1_object",
            "priority": 95,
        },
        {
            "match": {"modality": "t9", "locale": _norm(locale)},
            "target_prism": PRISM_MEMORY,
            "lattice_hint": "L2_word",
            "priority": 50,
        },
    ]
    block["routes"] = rows
    return rows
