#!/usr/bin/env python3
"""Hot-path capability resolve (ADR-0035 / ADR-0049 dual-route)."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.routing import ROUTE_KIND_CAPABILITY, RouteContext, Router


def _norm_query(query: str) -> str:
    return (query or "").strip().lower()


def _read_intent_cues(query: str) -> str:
    ql = _norm_query(query)
    if any(w in ql for w in ("запят", "пунктуац", "тире", "двоеточ")):
        return "punctuation"
    if any(w in ql for w in ("орфограф", "правописан", "как пишется", "верно ли", "согласно")):
        return "spelling"
    if any(w in ql for w in ("проверь", "исправь")) and "орфограф" in ql:
        return "spelling"
    return ""


def build_capability_context(
    query: str,
    *,
    locale: str = "ru",
    novel: str = "",
    surface_class: str = "",
) -> RouteContext:
    """Query geometry → capability route match (text tract v1)."""
    from casa.prisms.tick.passage import has_passage_context

    ql = _norm_query(query)
    geometry = "passage_context" if has_passage_context(query) else ""
    read_intent = _read_intent_cues(query)
    modality = "text"
    if re.search(r"\.(png|jpg|jpeg|webp)\b", ql):
        modality = "vis"

    return RouteContext(
        route_kind=ROUTE_KIND_CAPABILITY,
        modality=modality,
        locale=locale,
        geometry=geometry,
        read_intent=read_intent,
        surface_class=surface_class,
        novel=novel,
    )


def resolve_capability_skill(
    state: dict,
    query: str,
    *,
    locale: str = "ru",
) -> str | None:
    """Best promoted skill for this query, or None."""
    ctx = build_capability_context(query, locale=locale)
    tgt = Router.bind(state).resolve_layer(ctx)
    if tgt is None or not tgt.target_skill:
        return None
    return str(tgt.target_skill).strip() or None


def apply_capability_to_wm(state: dict, wm: Any, query: str, *, locale: str = "ru") -> str | None:
    """Set WM step_capability when router has a promoted skill."""
    skill = resolve_capability_skill(state, query, locale=locale)
    if skill and hasattr(wm, "step_capability"):
        wm.step_capability = skill
    return skill
